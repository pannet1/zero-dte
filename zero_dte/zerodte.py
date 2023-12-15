from constants import base, logging, common, cnfg, data, fils
from porfolio_manager import PortfolioManager
from print import prettier
from toolkit.digits import Digits
from toolkit.round_to_paise import adjust_ltp
from symbols import Symbols, dct_sym
import pendulum as pdlm
from time import sleep
from rich import print
import math
import re
import os
import json


def append_to_json_file(data, filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            # If the file doesn't exist, create it with the initial data
            json.dump(data, file, ensure_ascii=False, indent=4)
    else:
        # Write the updated data back to the file
        with open(filename, 'a+') as file:
            json.dump(data, file, ensure_ascii=False, indent=4, default=str)


def last_print(text, kwargs):
    logging.debug(text)
    kwargs["last"] = text
    return kwargs


def _order_place(**args):
    if common["buff_perc"] == 0:
        args["order_type"] = "MKT"
    else:
        args["order_type"] = "LMT"
        dir = 1 if args["side"] == "B" else -1
        last_price = kwargs["quotes"][args["symbol"]]
        args["price"] = adjust_ltp(last_price, dir * common["buff_perc"], 0.05)
    args["exchange"] = base['EXCHANGE']
    args["disclosed_quantity"] = args["quantity"]
    print(f"order place{args}")
    order_no = brkr.order_place(**args)
    file_to_append = data + "orders.json"
    append_to_json_file(args, file_to_append)
    print(f"{order_no=}")


def _positions(**kwargs):
    positions = brkr.positions
    if any(positions):
        keys = [
            "symbol",
            "quantity",
            "last_price",
            "urmtom",
            "rpnl",
        ]
        # filter by dict keys
        positions = [{key: dct[key] for key in keys} for dct in positions]
        # calc value
        for pos in positions:
            pos["value"] = int(pos["quantity"] * pos["last_price"])
        kwargs["positions"] = pm.update(positions, "last_price")
    return kwargs


def _calculate_allowable_quantity(**kwargs):
    kwargs["lotsize"] = 0
    sold_quantities = kwargs["quantity"].get("sell", 0)
    entry_quantity = base["ENTRY_PERC"] / 100 * base["MAX_QTY"]
    print(f"{entry_quantity=}  {base['ENTRY_PERC']} / 100 * {base['MAX_QTY']}")
    entry_lot = int(entry_quantity / base["LOT_SIZE"])
    simul_qty = (entry_lot * 2 * base["LOT_SIZE"]) + sold_quantities
    print(f"{entry_lot=}{simul_qty=}")
    if entry_lot > 0 and simul_qty <= base['MAX_QTY']:
        kwargs['lotsize'] = entry_lot
    print(f"final lot size: {kwargs['lotsize']}")
    return kwargs


def _pyramid(**kwargs):
    # sell call
    symbol = obj_sym.find_closest_premium(
        kwargs["quotes"], base["SEL_PREMIUM"], contains="C"
    )
    args = {
        "symbol": symbol,
        "quantity": kwargs["lotsize"] * base['LOT_SIZE'],
        "side": "S",
        "tag": "pyramid",
    }
    _order_place(**args)
    # buy call
    symbol = obj_sym.find_closest_premium(
        kwargs["quotes"], base["BUY_PREMIUM"], contains="C"
    )
    args.update({
        "symbol": symbol,
        "side": "B",
    })
    _order_place(**args)
    # sell put
    symbol = obj_sym.find_closest_premium(
        kwargs["quotes"], base["SEL_PREMIUM"], contains="P"
    )
    args.update({
        "symbol": symbol,
        "side": "S",
    })
    _order_place(**args)

    # buy put
    symbol = obj_sym.find_closest_premium(
        kwargs["quotes"], base["BUY_PREMIUM"], contains="P"
    )
    args.update({
        "symbol": symbol,
        "side": "B",
    })
    _order_place(**args)

    kwargs["positions"] = _positions
    return kwargs


def reset_trailing(**kwargs):
    kwargs["trailing"]["reset_high"] = -100
    kwargs["trailing"]["perc_decline"] = -100
    return kwargs


def _update_metrics(**kwargs):

    # portfolio
    sell_value = 0
    for pos in kwargs["positions"]:
        if pos["quantity"] < 0:
            sell_value += pos["value"]

    urmtom = sum(pos["urmtom"] for pos in kwargs["positions"])
    rpnl = sum(pos["rpnl"] for pos in kwargs["positions"])
    pnl = urmtom + rpnl

    if kwargs.get("portfolio", False):
        lowest = min(pnl, kwargs["portfolio"]["lowest"])
        highest = max(pnl, kwargs["portfolio"]["highest"])
    else:
        lowest = pnl
        highest = pnl

    kwargs["portfolio"] = dict(
        portfolio=True,
        lowest=lowest,
        highest=highest,
        value=sell_value,
        urmtom=urmtom,
        rpnl=rpnl,
    )

    # quantity
    sell = 0
    for pos in kwargs["positions"]:
        if pos['quantity'] < 0:
            sell += abs(pos['quantity'])
    buy = sum(pos["quantity"]
              for pos in kwargs["positions"] if pos["quantity"] > 0)
    kwargs["quantity"] = dict(
        quantity="quantity", sell=sell, buy=buy, total=buy - sell
    )

    # percentages
    max_pfolio = Digits.calc_perc(highest, base["PFOLIO"])
    curr_pfolio = Digits.calc_perc(pnl, base["PFOLIO"])
    decline = round(max_pfolio - curr_pfolio, 2)
    min_pfolio = Digits.calc_perc(lowest, base["PFOLIO"])
    improve = round(curr_pfolio - min_pfolio, 2)
    kwargs["perc"] = dict(
        perc="perc",
        max_pfolio=max_pfolio,
        curr_pfolio=curr_pfolio,
        decline=decline,
        min_pfolio=min_pfolio,
        improve=improve,
    )

    # trailing
    if kwargs["perc"]["max_pfolio"] >= 0.5:
        kwargs["trailing"]["reset_high"] = max(
            curr_pfolio, kwargs["trailing"]["reset_high"]
        )
        kwargs["trailing"]["perc_decline"] = (
            kwargs["trailing"]["reset_high"] - curr_pfolio
        )

        if (
            kwargs["trailing"]["trailing"] == 0
            and kwargs["trailing"]["perc_decline"] >= 1
        ):
            kwargs["trailing"]["trailing"] = 1
            text = f"trailing :{max_pfolio=}>0.5 and decline{kwargs['trailing']['perc_decline']} >= 1 "
            kwargs = last_print(text, kwargs)
            kwargs = reset_trailing(**kwargs)

    # adjustment
    call_value = sum(
        pos["value"]
        for pos in kwargs["positions"]
        if re.search(re.escape(base["EXPIRY"] + "C"), pos["symbol"])
        and pos["quantity"] < 0
    )
    put_value = sum(
        pos["value"]
        for pos in kwargs["positions"]
        if re.search(re.escape(base["EXPIRY"] + "P"), pos["symbol"])
        and pos["quantity"] < 0
    )
    diff = call_value - put_value
    ratio = 0 if sell_value == 0 else diff / sell_value
    adjust_mode = False
    if kwargs.get("adjust", False):
        adjust_mode = kwargs["adjust"]["adjust"]
    kwargs["adjust"] = dict(
        adjust=adjust_mode,
        call_value=call_value,
        put_value=put_value,
        diff=diff,
        ratio=round(ratio, 5),
        amount=abs(int(diff * base["ADJUST_PERC"] / 100)),
    )
    kwargs["pnl"] = pnl

    now = pdlm.now()
    fname = str(now.format('H')).zfill(2) + \
        str(now.format('m')).zfill(2) + \
        str(now.format('s')).zfill(2)
    fils.save_file(kwargs, data + fname)
    return kwargs


def is_pyramid_cond(**kwargs):
    sleep(slp)
    kwargs["quotes"].update(wserver.ltp)
    kwargs = _positions(**kwargs)
    kwargs = _update_metrics(**kwargs)
    kwargs = _calculate_allowable_quantity(**kwargs)
    kwargs["fn"] = is_trailing_cond
    if (
        kwargs["lotsize"] > 0
        # and kwargs["last"] != "pyramid plus" or kwargs["last"] != "pyramid minus"
        and kwargs["portfolio"]["portfolio"]
    ):
        print("xxxxxxxxxx {kwargs['lotsize']}")
        increase = kwargs["pnl"] - kwargs["portfolio"]["lowest"]
        if (kwargs["pnl"] > kwargs["quantity"]["sell"] * base["PYRAMID_PLUS"]):
            kwargs = _pyramid(**kwargs)
            kwargs = last_print("pyramid plus", kwargs)
        elif (
            increase > (kwargs["quantity"]["sell"] *
                        base["PYRAMID_MINUS"]) and kwargs["pnl"] < 0
        ):
            kwargs = _pyramid(**kwargs)
            kwargs = last_print("pyramid minus", kwargs)
    return kwargs


def is_trailing_cond(**kwargs):
    def _exit_by_trail(**kwargs):
        """
        buy 20% of the positions sell value value
        starting from the high-est ltp
        """
        if kwargs["trailing"]["perc_decline"] > 1 + (
            kwargs["trailing"]["trailing"] * 0.1
        ):
            kwargs = last_print(
                f' {kwargs["trailing"]["perc_decline"]} > 0.1 ', kwargs)
            value_to_reduce = int(-0.2 * kwargs["portfolio"]["value"] / 2)
            kwargs = last_print(
                f'{value_to_reduce=}= -0.2 X value {kwargs["portfolio"]["value"]} / 2',
                kwargs,
            )
            call_value_to_reduce, lst_of_ords = pm.reduce_value(
                value_to_reduce, contains="C"
            )
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "call_trail_stop"})
                    _order_place(**ord)
            kwargs = last_print(
                f"call values to reduce: {call_value_to_reduce}", kwargs
            )
            if call_value_to_reduce < 0:
                symbol = obj_sym.find_closest_premium(
                    kwargs["quotes"], base["SEL_PREMIUM"], contains="C"
                )
                lots = math.ceil(
                    call_value_to_reduce /
                    kwargs["quotes"][symbol] / base["LOT_SIZE"]
                )
                kwargs = last_print(f"sell {lots=}fresh call {symbol}", kwargs)
                args = {
                    "symbol": symbol,
                    "quantity": lots * kwargs["lotsize"],
                    "side": "S",
                    "tag": "trail",
                }
                _order_place(**args)
            # TODO
            put_value_to_reduce, lst_of_ords = pm.reduce_value(
                value_to_reduce, contains="P"
            )
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "put_trail_stop"})
                    _order_place(**ord)
            kwargs = last_print(
                f"put values to reduce: { put_value_to_reduce}", kwargs)
            if put_value_to_reduce < 0:
                symbol = obj_sym.find_closest_premium(
                    kwargs["quotes"], base["SEL_PREMIUM"], contains="P"
                )
                lots = math.ceil(
                    put_value_to_reduce /
                    kwargs["quotes"][symbol] / base["LOT_SIZE"]
                )
                logging.debug(f"sell {lots=} fresh put {symbol}")
                args = {
                    "symbol": symbol,
                    "quantity": lots * base["LOT_SIZE"],
                    "side": "S",
                    "tag": "trail",
                }
                _order_place(**args)
            kwargs = _positions(**kwargs)
            kwargs = last_print(
                f'trailed level: {kwargs["trailing"]["trailing"]}', kwargs
            )
            kwargs["trailing"]["trailing"] += 1
            # TODO
        return kwargs

    # set values
    kwargs["fn"] = adjust
    if 0 < kwargs["trailing"]["trailing"] <= 4:
        kwargs = _exit_by_trail(**kwargs)
    elif kwargs["trailing"]["trailing"] == 5:
        if kwargs["trailing"]["perc_decline"] >= 1.5:
            kwargs = last_print("trailing EXIT", kwargs)
            for pos in pm.close_positions():
                if any(pos):
                    pos.update({"tag": "EXIT_BY_TRAIL"})
                    _order_place(**pos)
            # TODO
            kwargs.pop('fn')
    return kwargs


def adjust(**kwargs):
    def reduced_value_order(reduced_value, tag=""):
        symbol = obj_sym.find_closest_premium(
            kwargs['quotes'], base['ADJUST_SEL_PREMIUM'], ce_or_pe)
        ltp = kwargs['quotes'][symbol]
        calculated = math.ceil(reduced_value / ltp / base['LOT_SIZE'])
        sell_qty = 1 if calculated == 0 else calculated
        args = {}
        args.update({
            "symbol": symbol,
            "quantity": sell_qty * base['LOT_SIZE'],
            "side": "S",
            "tag": tag
        })
        _order_place(**args)

    kwargs["fn"] = profit
    kwargs = _positions(**kwargs)
    ce_or_pe = None

    if kwargs["adjust"]["ratio"] >= base["DIFF_THRESHOLD"] * 1:
        ce_or_pe = "C"
    elif kwargs["adjust"]["ratio"] <= base["DIFF_THRESHOLD"] * -1:
        ce_or_pe = "P"

    if ce_or_pe:
        # level 1
        if pm.is_above_highest_ltp(contains=ce_or_pe):
            kwargs = last_print(f"{ce_or_pe} adjust_highest", kwargs)
            kwargs["adjust"]["adjust"] = 1
            reduced_value, buy_entry = pm.adjust_highest_ltp(
                kwargs["adjust"]["amount"], ce_or_pe)
            reduced_value = kwargs["adjust"]["amount"] - \
                reduced_value  # expected neg reduced_value
            args = {
                "symbol": buy_entry["symbol"],
                "quantity": buy_entry["quantity"],
                "side": "B",
                "tag": "adjust_highest_ltp",
            }
            _order_place(**args)
            # reduced_value_order(reduced_value, "adjust_highest_ltp")
            kwargs['fn'] = is_pyramid_cond
        # level 2
        elif kwargs["perc"]["decline"] > 0.25:
            kwargs = last_print(f"{ce_or_pe} adjust_detoriation", kwargs)
            kwargs["adjust"]["adjust"] = 2
            reduced_value, lst_of_ords = pm.reduce_value(
                kwargs["adjust"]["amount"], contains=ce_or_pe)
            reduced_value = kwargs["adjust"]["amount"] - \
                reduced_value  # expected neg reduced_value
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "calculated"})
                    _order_place(**ord)
            # reduced_value_order(reduced_value, "adjust_detoriation")
            kwargs['fn'] = is_pyramid_cond
        elif kwargs["pnl"] < 0:
            kwargs = last_print(f"{ce_or_pe} adjust_negative_pnl", kwargs)
            kwargs["adjust"]["adjust"] = 3
            reduced_value, lst_of_ords = pm.reduce_value(
                kwargs["adjust"]["amount"], contains=ce_or_pe
            )
            reduced_value = kwargs["adjust"]["amount"] - \
                reduced_value  # expected neg reduced_value
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "adjust_negative_pnl"})
                    _order_place(**ord)
            # reduced_value_order(reduced_value, "adjust_negative_pnl")
            kwargs['fn'] = is_pyramid_cond
        elif kwargs["quantity"]["sell"] >= base["MAX_QTY"]:
            kwargs["adjust"]["adjust"] = 4
            kwargs = last_print(f"{ce_or_pe} adjust_max_qty", kwargs)
            reduced_value, lst_of_ords = pm.reduce_value(
                kwargs["adjust"]["amount"], contains=ce_or_pe
            )
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "adjust_max_qty"})
                    _order_place(**ord)
            # reduced_value_order(reduced_value, "adjust_max_qty")
            kwargs['fn'] = is_pyramid_cond
        else:
            kwargs["adjust"]["adjust"] = 5
            symbol = obj_sym.find_closest_premium(
                kwargs['quotes'], base['ADJUST_BUY_PREMIUM'], ce_or_pe)
            ltp = kwargs['quotes'][symbol]
            calculated = math.ceil(
                kwargs["adjust"]["amount"] / ltp / base['LOT_SIZE'])
            buy_qty = 1 if calculated == 0 else calculated
            logging.debug(
                f"{kwargs['adjust']['amount']} val to reduce by {buy_qty}")
            args = {}
            args.update({
                "symbol": symbol,
                "quantity": buy_qty * base['LOT_SIZE'],
                "side": "B",
                "tag": "adjust_fresh_buy"
            })
            _order_place(**args)
            kwargs['fn'] = is_pyramid_cond
    return kwargs


def profit(**kwargs):
    kwargs["fn"] = close_profit_position
    if kwargs["perc"]["decline"] > 2.5:
        kwargs["portfolio"]["portfolio"] = False
        kwargs = last_print("portfolio decline: pyrmid disabled", kwargs)
    elif kwargs["perc"]["improve"] > 2.5:
        kwargs["portfolio"]["portfolio"] = True
        kwargs = last_print("portfolio improve: pyrmid enabled", kwargs)
    return kwargs


def close_profit_position(**kwargs):
    kwargs["fn"] = is_portfolio_stop
    ce_qty = pm.close_profiting_position("C")
    # TODO
    if ce_qty < 0:
        kwargs = last_print("take C new positions", kwargs)
    pe_qty = pm.close_profiting_position("P")
    if pe_qty < 0:
        kwargs = last_print("take P new positions", kwargs)
    return kwargs


def is_portfolio_stop(**kwargs):
    kwargs["fn"] = is_pyramid_cond
    if kwargs["perc"]["curr_pfolio"] < base["PFOLIO_SL_PERC"]:
        for entry in pm.close_positions():
            entry.update({"tag": "porfolio stop"})
            _order_place(**entry)
        kwargs = last_print("portfolio stop hit", kwargs)
        kwargs.pop("fn")
    return kwargs


"""
    begin
"""
kwargs = {
    "last": "Happy Trading",
    "trailing": {"trailing": 0},
    "quotes": {},
    "quantity": {},
}
slp = 4
pm = PortfolioManager([], base)
SYMBOL = common["base"]
obj_sym = Symbols(base['EXCHANGE'], SYMBOL, base["EXPIRY"])
obj_sym.get_exchange_token_map_finvasia()
times = pdlm.parse("15:30", fmt="HH:mm").time()

if common["live"]:
    from omspy_brokers.finvasia import Finvasia
    from wserver import Wserver

    brkr = Finvasia(**cnfg)
    if not brkr.authenticate():
        logging.error("Failed to authenticate")
        SystemExit(1)
    else:
        print("success")

    resp = brkr.finvasia.get_quotes(
        dct_sym[SYMBOL]["exch"], dct_sym[SYMBOL]["token"])
    if resp and resp.get("lp", False):
        lp = int(float(resp["lp"]))
        atm = obj_sym.get_atm(lp)
        print(f"{atm=}")
        dct_tokens = obj_sym.get_tokens(atm)
        lst_tokens = list(dct_tokens.keys())
        wserver = Wserver(brkr, lst_tokens, dct_tokens)
        while not any(kwargs['quotes']):
            print("waiting for quote \n")
            kwargs['quotes'] = wserver.ltp
            sleep(1)
    else:
        print("exiting system")
        SystemExit(1)

else:
    from paper import Paper
    atm = 47100
    dct_tokens = obj_sym.get_tokens(atm)
    lst_tokens = list(dct_tokens.keys())
    brkr = Paper(lst_tokens, dct_tokens)
    wserver = brkr
    kwargs['quotes'] = wserver.ltp

# init trailing variables
kwargs = reset_trailing(**kwargs)
# init lot size
kwargs = _calculate_allowable_quantity(**kwargs)
# place the first entry
kwargs = _positions(**kwargs)
# if not any(kwargs['positions']):
kwargs = _pyramid(**kwargs)
#
kwargs["fn"] = is_pyramid_cond
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = prettier(**kwargs)
    next_func = kwargs.pop("fn")
    kwargs = next_func(**kwargs)
