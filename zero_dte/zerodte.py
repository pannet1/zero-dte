from constants import base, logging, common, cnfg
from porfolio_manager import PortfolioManager
from print import prettier
from toolkit.digits import Digits
from toolkit.round_to_paise import adjust_ltp
from symbols import Symbols, dct_sym
from utils import calc_m2m
from time import sleep
from rich import print
import math
import re
import pendulum as pdlm

def last_print(text, kwargs):
    logging.debug(text)
    kwargs["last"] = text
    return kwargs


def _order_place(**args):
    print(kwargs)
    if common["buff_perc"] == 0:
        args["order_type"] = "MKT"
    else:
        args["order_type"]="LMT"
        dir = 1 if args["side"] == "B" else -1 
        last_price = kwargs["quotes"][args["symbol"]]
        args["price"]= adjust_ltp(last_price, dir * common["buff_perc"], 0.05)
    args["exchange"] = base['EXCHANGE']
    args["disclosed_quantity"]=args["quantity"]
    print(f"order place{args}")
    order_no = brkr.order_place(**args)
    print(f"{order_no=}")

def _positions(**kwargs):
    kwargs['positions']= brkr.positions
    keys = [
        "symbol",
        "quantity",
        "last_price",
        "urmtom",
        "rpnl",
    ]
    for pos in kwargs["positions"]:
        pos_copy = {key: pos[key] for key in keys if key in pos}
        # Update the original position dictionary
        pos.clear()
        pos.update(pos_copy)
        pos["value"] = int(pos["quantity"] * pos["last_price"])
    kwargs["positions"] = pm.update(kwargs['positions'], "last_price")
    return kwargs

def _calculate_allowable_quantity(**kwargs):
    kwargs["lotsize"] = 0
    if (
        kwargs.get("quantity", "EMPTY") == "EMPTY"
        or kwargs["quantity"]["sell"] < base["MAX_QTY"]
    ):
        rough_total = base["ENTRY_PERC"] / 100 * base["MAX_QTY"]
        print(f"lotsize: {rough_total}")
        kwargs['lotsize'] = int(rough_total / base["LOT_SIZE"]) * base["LOT_SIZE"]
        print(kwargs["lotsize"])
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
    args.update ({
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
    kwargs = _positions(**kwargs)

    # portfolio
    sell_value = sum(pos["value"] for pos in kwargs["positions"] if pos["quantity"] < 0)
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
    sell = abs(
        sum(pos["quantity"] for pos in kwargs["positions"] if pos["quantity"] < 0)
    )
    buy = sum(pos["quantity"] for pos in kwargs["positions"] if pos["quantity"] > 0)
    closed = sum(pos["quantity"] for pos in kwargs["positions"] if pos["quantity"] == 0)
    kwargs["quantity"] = dict(
        quantity="quantity", sell=sell, buy=buy, closed=closed, total=buy - sell
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
    sleep(2)
    return kwargs


def is_pyramid_cond(**kwargs):
    kwargs["quotes"].update(wserver.ltp)
    kwargs = _update_metrics(**kwargs)
    kwargs = _calculate_allowable_quantity(**kwargs)
    kwargs["fn"] = is_trailing_cond

    if (
        kwargs["lotsize"] > 0
        # and kwargs["last"] != "pyramid complete"
        and kwargs["portfolio"]["portfolio"]
    ):
        increase = kwargs["portfolio"]["urmtom"] - kwargs["portfolio"]["lowest"]
        if (kwargs["pnl"] > kwargs["quantity"]["sell"] * base["PYRAMID_PLUS"]
        ):
            kwargs = _pyramid(**kwargs)
            kwargs = last_print("pyramid complete", kwargs)
        elif (
            increase > (kwargs["quantity"]["sell"] * base["PYRAMID_MINUS"]) and kwargs["pnl"] < 0
            ):
            kwargs = _pyramid(**kwargs)
            kwargs = last_print("pyramid complete", kwargs)

    return kwargs


# TODO should only return true or false
def is_trailing_cond(**kwargs):
    def _exit_by_trail(**kwargs):
        """
        buy 20% of the positions sell value value
        starting from the high-est ltp
        """
        if kwargs["trailing"]["perc_decline"] > 1 + (
            kwargs["trailing"]["trailing"] * 0.1
        ):
            kwargs = last_print(f' {kwargs["trailing"]["perc_decline"]} > 0.1 ', kwargs)
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
                    call_value_to_reduce / kwargs["quotes"][symbol] / base["LOT_SIZE"]
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
                    print(ord)
                    _order_place(**ord)
            kwargs = last_print(f"put values to reduce: { put_value_to_reduce}", kwargs)
            if put_value_to_reduce < 0:
                symbol = obj_sym.find_closest_premium(
                    kwargs["quotes"], base["SEL_PREMIUM"], contains="P"
                )
                lots = math.ceil(
                    put_value_to_reduce / kwargs["quotes"][symbol] / base["LOT_SIZE"]
                )
                logging.debug(f"sell {lots=} fresh put {symbol}")
                args = {
                    "symbol": symbol,
                    "quantity": lots * kwargs["lotsize"],
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
            # kwargs.pop('fn')
    return kwargs


def adjust(**kwargs):
    kwargs["fn"] = profit
    kwargs = _positions(**kwargs)
    ce_or_pe = None

    if kwargs["adjust"]["ratio"] >= base["DIFF_THRESHOLD"] * 5:
        sleep(slp)
        ce_or_pe = "C"
    elif kwargs["adjust"]["ratio"] <= base["DIFF_THRESHOLD"] * -2:
        sleep(slp)
        ce_or_pe = "P"

    if ce_or_pe:
        kwargs["adjust"]["adjust"] = False
        if pm.is_above_highest_ltp(contains=ce_or_pe):
            kwargs = last_print(f"{ce_or_pe} adjust_highest", kwargs)
            kwargs["adjust"]["adjust"] = 1
            kwargs["fn"] = is_pyramid_cond
            buy_entry = pm.adjust_highest_ltp(kwargs["adjust"]["amount"], ce_or_pe)
            args = {
                "symbol": buy_entry["symbol"],
                "quantity": buy_entry["quantity"],
                "side": "B",
                "tag": "adjust_highest_ltp",
            }
            _order_place(**args)
            # TODO should fresh calls be sold
            return kwargs
        if kwargs["perc"]["decline"] > 0.25:
            kwargs["adjust"]["adjust"] = 2
            kwargs = last_print(f"{ce_or_pe} adjust_detoriation", kwargs)
            reduced_value, lst_of_ords = pm.reduce_value(
                kwargs["adjust"]["amount"], contains=ce_or_pe
            )
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "adjust_detoriation"})
                    _order_place(**ord)
            # TODO
            print(f"{reduced_value=}")
            kwargs["fn"] = is_pyramid_cond
            return kwargs
        if kwargs["portfolio"]["urmtom"] < 0:
            kwargs["adjust"]["adjust"] = 3
            kwargs = last_print(f"{ce_or_pe} adjust_negative_pnl", kwargs)
            reduced_value, lst_of_ords = pm.reduce_value(
                kwargs["adjust"]["amount"], contains=ce_or_pe
            )
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "adjust_detoriation"})
                    _order_place(**ord)
            print(f"{reduced_value=}")
            kwargs["fn"] = is_pyramid_cond
            return kwargs
        if kwargs["quantity"]["sell"] >= base["MAX_QTY"]:
            kwargs["adjust"]["adjust"] = 4
            kwargs = last_print(f"{ce_or_pe} adjust_max_qty", kwargs)
            reduced_value, lst_of_ords = pm.reduce_value(
                kwargs["adjust"]["amount"], contains=ce_or_pe
            )
            for ord in lst_of_ords:
                if any(ord):
                    ord.update({"tag": "adjust_detoriation"})
                    _order_place(**ord)
            print(f"{reduced_value=}")
            kwargs["fn"] = is_pyramid_cond
            return kwargs
        if kwargs["adjust"]["adjust"] == 4:
            ce_or_pe = "P" if ce_or_pe == "C" else "C"
            # TODO sell fresh
            pm.reduce_value(kwargs["adjust"]["amount"] * -1, contains=ce_or_pe)
    kwargs["positions"] = pm.update()
    return kwargs


def profit(**kwargs):
    kwargs["fn"] = close_profit_position
    if kwargs["perc"]["decline"] > 2.5:
        kwargs["portfolio"]["portfolio"] = False
    elif kwargs["perc"]["improve"] > 2.5:
        kwargs["portfolio"]["portfolio"] = True
    return kwargs


def close_profit_position(**kwargs):
    kwargs["fn"] = is_portfolio_stop
    ce_qty = pm.close_profiting_position("C")
    if ce_qty < 0:
        print("take C new positions")
    pe_qty = pm.close_profiting_position("P")
    if pe_qty < 0:
        print("take P new position")
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
    BEGIN 
"""
kwargs = {
    "last": "Happy Trading",
    "trailing": {"trailing": 0},
}
slp = 5
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

    resp = brkr.finvasia.get_quotes(dct_sym[SYMBOL]["exch"], dct_sym[SYMBOL]["token"])
    if resp and resp.get("lp", False):
        lp = int(float(resp["lp"]))
        atm = obj_sym.get_atm(lp)
        print(f"{atm=}")
        dct_tokens = obj_sym.get_tokens(atm)
        lst_tokens = list(dct_tokens.keys())
        wserver = Wserver(brkr, lst_tokens, dct_tokens)
        kwargs['quotes'] = {}
        while not any(kwargs['quotes']):
            print("waiting for quote \n")
            kwargs['quotes'] = wserver.ltp
            sleep(1)
        print(kwargs['quotes'])
    else:
        SystemExit(1)

else:
    from paper import Paper

    dct_tokens = obj_sym.get_tokens(12600)
    lst_tokens = list(dct_tokens.keys())
    brkr = Paper(lst_tokens, dct_tokens)
    wserver = brkr

# init trailing variables
kwargs = reset_trailing(**kwargs)
# init lot size
kwargs = _calculate_allowable_quantity(**kwargs)
# place the first entry
kwargs = _positions(**kwargs)
if not any(kwargs['positions']):
    kwargs = _pyramid(**kwargs)
#
kwargs["fn"] = is_pyramid_cond
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = prettier(**kwargs)
    next_func = kwargs.pop("fn")
    kwargs = next_func(**kwargs)
