from constants import base, logging, common, cnfg, data, fils
from omspy_brokers.finvasia import Finvasia
from wserver import Wserver
from portfolio_manager import PortfolioManager
from paper import Paper
from symbols import Symbols, dct_sym
from utilities.printutils import prettier
from utilities.digits import Digits
from utilities.utils import adjust_ltp, round_val_to_qty
from adjustment import adjust_highest_ltp, reduce_value, is_above_highest_ltp, close_profiting_position
import pendulum as pdlm
from time import sleep
import re
import os
import json
import sys
from typing import Dict


def log_rotate():
    files = fils.get_files_with_extn("json", data)
    files = [file.split(".")[0] for file in files]
    files = [file for file in files
             if file.isdigit()]
    for file in files:
        pathfile = data + str(file) + ".json"
        if fils.is_file_not_2day(pathfile):
            fils.del_file(pathfile)
    pathfile = data + "orders.json"
    if fils.is_file_not_2day(pathfile):
        fils.nuke_file(pathfile)


def _log_and_show(text, kwargs):
    """
    logs and shows value on screen
    returns kwargs
    """
    logging.info(text)
    fname = _now()
    kwargs["portfolio"]["last"] = fname + ": " + text
    return kwargs


def _append_to_json(data, filename):
    if not os.path.exists(filename):
        with open(filename, 'w') as file:
            # If the file doesn't exist, create it with the initial data
            json.dump(data, file, ensure_ascii=False, indent=4)
    else:
        # Write the updated data back to the file
        with open(filename, 'a+') as file:
            json.dump(data, file, ensure_ascii=False, indent=4, default=str)


def _now() -> str:
    now = pdlm.now()
    fname = str(now.format('H')).zfill(2) + \
        str(now.format('m')).zfill(2) + \
        str(now.format('s')).zfill(2)
    return fname


def _save_file(kwargs):
    fname = _now()
    fils.save_file(kwargs, data + fname)


def _reset_trail(**kwargs):
    kwargs["trailing"]["reset_high"] = -100
    kwargs["trailing"]["perc_decline"] = -100
    return kwargs


def _hl_cls(brkr, quantity: Dict) -> Dict:
    hi = quantity.get("hi", 0)
    lo = quantity.get("lo", 0)
    keys = ["h", "l", "lp"]
    if isinstance(brkr, Finvasia):
        sleep(slp)
        resp = brkr.finvasia.get_quotes(
            dct_sym[SYMBOL]["exch"], dct_sym[SYMBOL]["token"])
        # check if keys exists in the json resp
        if resp and all(key in resp for key in keys):
            hi = int(float(resp["h"]))
            lo = int(float(resp["l"]))
        quantity["is_new"] = 1 if hi > quantity.get(
            "hi", hi) else quantity["is_new"]
        quantity["is_new"] = -1 \
            if lo < quantity.get("lo", lo) else quantity["is_new"]
        quantity['cl'] = int(float(resp["lp"]))
    else:
        quantity["hi"] = PAPER_ATM + 50
        quantity["lo"] = PAPER_ATM - 50
        quantity["cl"] = PAPER_ATM
        quantity["is_new"] = 1 if hi > quantity.get(
            "hi", hi) else quantity["is_new"]
        quantity["is_new"] = -1 \
            if lo < quantity.get("lo", lo) else quantity["is_new"]
        quantity["atm"] = PAPER_ATM
    quantity["atm"] = obj_sym.get_atm(quantity["cl"])
    return quantity


def _order_place(**args):
    if args["quantity"] > 0:
        if common["buff_perc"] == 0:
            args["order_type"] = "MKT"
        else:
            args["order_type"] = "LMT"
            dir = 1 if args["side"] == "B" else -1
            last_price = kwargs["quotes"][args["symbol"]]
            args["price"] = adjust_ltp(
                last_price, dir * common["buff_perc"], 0.05)
        args["exchange"] = base['EXCHANGE']
        args["disclosed_quantity"] = args["quantity"]
        brkr.order_place(**args)
        file_to_append = data + "orders.json"
        _append_to_json(args, file_to_append)
    else:
        tag = args.get("tag", "unknown")
        logging.error(
            f"Q0 while: {tag} {kwargs['portfolio']['lotsize']}")


def _positions(**kwargs):
    sleep(slp)
    positions = [{}]
    positions = brkr.positions
    keys = [
        "symbol",
        "quantity",
        "last_price",
        "urmtom",
        "rpnl",
    ]
    if any(positions):
        # filter by dict keys
        positions = [{key: dct[key] for key in keys} for dct in positions]
        # remove positions that does not begin with symbol name
        positions = [pos for pos in positions if pos["symbol"].startswith(
            kwargs["quantity"]["quantity"])]
        # calc value
        for pos in positions:
            straddle = kwargs["quantity"].get('straddle', pos["last_price"])
            ltp = min(pos["last_price"], straddle)
            pos["value"] = int(pos["quantity"] * ltp)
    kwargs["positions"] = pm.update(positions)
    return kwargs


def _allowed_lot(**kwargs):
    kwargs["portfolio"]["lotsize"] = 0
    sold_quantities = kwargs["quantity"].get("sell", 0)
    entry_quantity = base["ENTRY_PERC"] / 100 * base["MAX_QTY"]
    entry_lot = int(entry_quantity / base["LOT_SIZE"])
    simul_qty = (entry_lot * 2 * base["LOT_SIZE"]) + sold_quantities
    if entry_lot > 0 and (simul_qty <= base['MAX_QTY']):
        kwargs['portfolio']['lotsize'] = entry_lot
    return kwargs


def _pyramid(**kwargs):
    # sell call
    symbol = obj_sym.find_closest_premium(
        kwargs["quotes"], base["SEL_PREMIUM"], contains="C"
    )
    args = {
        "symbol": symbol,
        "quantity": kwargs["portfolio"]["lotsize"] * base['LOT_SIZE'],
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
    return kwargs


def _update_metrics(**kwargs):
    kwargs["quotes"].update(wserver.ltp)
    quantity = kwargs["quantity"]
    try:
        quantity = _hl_cls(brkr, quantity)
    except Exception as e:
        logging.debug(f"{e} unable to get atm price")
    quantity["straddle"] = obj_sym.calc_straddle_value(
        quantity["atm"], kwargs["quotes"])
    kwargs = _positions(**kwargs)
    kwargs = _allowed_lot(**kwargs)

    # portfolio
    sell_value = 0
    for pos in kwargs["positions"]:
        if pos["quantity"] < 0:
            sell_value += pos["value"]
    urmtom = sum(pos["urmtom"] for pos in kwargs["positions"])
    rpnl = sum(pos["rpnl"] for pos in kwargs["positions"])
    pnl = urmtom + rpnl
    lowest = min(pnl, kwargs["portfolio"].get("lowest", pnl))
    highest = max(pnl, kwargs["portfolio"].get("highest", pnl))
    kwargs["portfolio"].update(
        {
            "lowest": lowest,
            "highest": highest,
            "value": sell_value,
            "urmtom": urmtom,
            "rpnl": rpnl,
            "PNL": pnl
        })

    # quantity
    sell = 0
    for pos in kwargs["positions"]:
        if pos['quantity'] < 0:
            sell += abs(pos['quantity'])
    buy = sum(pos["quantity"]
              for pos in kwargs["positions"] if pos["quantity"] > 0)
    kwargs["quantity"].update({"sell": sell, "buy": buy, "total": buy - sell})

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
            kwargs = _log_and_show(text, kwargs)
            kwargs = _reset_trail(**kwargs)

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
    kwargs["adjust"].update({
        "call_value": call_value,
        "put_value": put_value,
        "diff": diff,
        "ratio": round(ratio, 5),
        "amount": abs(int(diff * base["ADJUST_PERC"] / 100)),
    })
    _save_file(kwargs)
    return kwargs


def is_pyramid_cond(**kwargs):
    kwargs = _update_metrics(**kwargs)
    kwargs["portfolio"]["fn"] = is_trailing_cond
    if (
        kwargs["portfolio"]["lotsize"] > 0
        and kwargs["portfolio"]["is_pyramid"]
    ):
        increase = kwargs["portfolio"]["PNL"] - kwargs["portfolio"]["lowest"]
        if kwargs["portfolio"]["PNL"] > \
                (kwargs["quantity"]["sell"] * base["PYRAMID_PLUS"]):
            kwargs = _pyramid(**kwargs)
            kwargs = _log_and_show("pyramid plus", kwargs)
            kwargs = _update_metrics(**kwargs)
        elif (
            increase > (kwargs["quantity"]["sell"] *
                        base["PYRAMID_MINUS"]) and
                kwargs["portfolio"]["PNL"] < 0
        ):
            kwargs = _pyramid(**kwargs)
            kwargs = _log_and_show("pyramid minus", kwargs)
            kwargs = _update_metrics(**kwargs)
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
            amount = int(-0.2 * kwargs["portfolio"]["value"] / 2)
            tag = "trailing"
            lst_options = ['P', 'C']

            for ce_or_pe in lst_options:
                reduced_value, lst_of_ords = reduce_value(
                    kwargs["positions"],
                    amount, ce_or_pe, tag
                )
                for ord in lst_of_ords:
                    _order_place(**ord)
                if reduced_value < 0:
                    kwargs["trailing"][ce_or_pe] += abs(reduced_value)
                    kwargs = find_symbol_and_sell(kwargs, ce_or_pe, tag)
            kwargs["trailing"]["trailing"] += 1
            kwargs = _log_and_show(f"{tag} for {amount=}", kwargs)
            kwargs = _update_metrics(**kwargs)
        return kwargs

    # set values
    kwargs["portfolio"]["fn"] = toggle_pyramid
    if 0 < kwargs["trailing"]["trailing"] <= 4:
        kwargs = _exit_by_trail(**kwargs)
    elif kwargs["trailing"]["trailing"] == 5:
        if kwargs["trailing"]["perc_decline"] >= 1.5:
            kwargs = _log_and_show("trailing EXIT", kwargs)
            for pos in pm.close_positions():
                if any(pos):
                    pos.update({"tag": "EXIT_BY_TRAIL"})
                    _order_place(**pos)
            kwargs = _update_metrics(**kwargs)
            kwargs = prettier(**kwargs)
            kwargs['portfolio'].pop("fn")
    return kwargs


def toggle_pyramid(**kwargs):
    kwargs["portfolio"]["fn"] = close_profit_position
    is_pyramid = kwargs["portfolio"]["is_pyramid"]
    if kwargs["perc"]["decline"] > 2.5 and is_pyramid:
        is_pyramid = False
        kwargs = _log_and_show("pyramid disabled", kwargs)
    elif kwargs["perc"]["improve"] > 2.5 and not is_pyramid:
        is_pyramid = True
        kwargs = _log_and_show("pyramid enabled", kwargs)
    return kwargs


def close_profit_position(**kwargs):
    kwargs["portfolio"]["fn"] = is_portfolio_stop
    tag = "close_profit_position"
    value_for_this, pos = close_profiting_position(
        kwargs["positions"], kwargs["trailing"]["profit_val"], tag)
    if any(pos):
        _order_place(**pos)
        # find option to cover
        kwargs = _log_and_show(
            f"{tag} covering {pos['symbol']} {pos['quantity']}",
            kwargs)
        ce_or_pe = obj_sym.find_option_type(pos["symbol"])
        if ce_or_pe and value_for_this > 0:
            symbol = obj_sym.find_closest_premium(kwargs['quotes'],
                                                  base["ADJUST_SEL_PREMIUM"],
                                                  ce_or_pe)
            symbol = obj_sym.find_symbol_in_moneyness(symbol,
                                                      ce_or_pe,
                                                      price_type="ITM")
            quantity = round_val_to_qty(
                value_for_this,
                kwargs["quotes"][symbol],
                base['LOT_SIZE']
            )
            quantity = max(quantity, base['LOT_SIZE'])
            args = dict(
                symbol=symbol,
                quantity=quantity,
                side="S",
                tag=tag
            )
            _order_place(**args)
            kwargs = _log_and_show(
                f"{tag}: {value_for_this} in new {symbol} {quantity}",
                kwargs)
        kwargs = _update_metrics(**kwargs)
    return kwargs


def is_portfolio_stop(**kwargs):
    kwargs["portfolio"]["fn"] = adjust
    if kwargs["perc"]["curr_pfolio"] < base["PFOLIO_SL_PERC"]:
        for entry in pm.close_positions():
            entry.update({"tag": "portfolio stop"})
            _order_place(**entry)
        kwargs = _log_and_show("portfolio stop hit", kwargs)
        kwargs = _update_metrics(**kwargs)
        kwargs = prettier(**kwargs)
        kwargs['portfolio'].pop("fn")
    return kwargs


def find_symbol_and_sell(kwargs, ce_or_pe, tag: str, price_type=None):
    value_deficit = kwargs["trailing"][ce_or_pe]
    if value_deficit > 0:
        symbol = obj_sym.find_closest_premium(kwargs['quotes'],
                                              base["ADJUST_SEL_PREMIUM"],
                                              ce_or_pe)
        if price_type:
            symbol = obj_sym.find_symbol_in_moneyness(symbol,
                                                      ce_or_pe,
                                                      price_type)
        quantity = round_val_to_qty(
            value_deficit,
            kwargs["quotes"][symbol],
            base['LOT_SIZE']
        )
        if quantity > 0:
            args = dict(
                symbol=symbol,
                quantity=quantity,
                side="S",
                tag=tag
            )
            _order_place(**args)
            value_deficit -= int(args["quantity"] * kwargs["quotes"][symbol])
            kwargs["trailing"][ce_or_pe] = value_deficit
    return kwargs


def adjust(**kwargs):
    kwargs["portfolio"]["fn"] = is_pyramid_cond
    ce_or_pe = None

    if kwargs["adjust"]["ratio"] >= base["UP_THRESH"] * 1:
        ce_or_pe = "C"
    elif kwargs["adjust"]["ratio"] <= base["DN_THRESH"] * -1:
        ce_or_pe = "P"

    if ce_or_pe:
        # level 1
        amount = kwargs["adjust"]["amount"]
        if is_above_highest_ltp(kwargs["positions"], contains=ce_or_pe):
            kwargs["adjust"]["adjust"] = 1
            tag = "adjust_highest_ltp"
            reduced_value, ord = adjust_highest_ltp(
                kwargs["positions"],
                amount, ce_or_pe, tag)
            if any(ord):
                _order_place(**ord)
                log = f"adjust {ord['quantity']} {ord['symbol']}" \
                    f"{tag} {reduced_value=}"
                kwargs = _log_and_show(log, kwargs)
        # level 2
        elif kwargs["perc"]["decline"] > 0.25:
            kwargs["adjust"]["adjust"] = 2
            tag = "adjust_decline_perc"
            reduced_value, lst_of_ords = reduce_value(
                kwargs["positions"],
                amount, ce_or_pe, tag)
            for ord in lst_of_ords:
                _order_place(**ord)
            if reduced_value < 0:
                kwargs["trailing"][ce_or_pe] += abs(reduced_value)
            kwargs = find_symbol_and_sell(kwargs,
                                          ce_or_pe, tag, price_type="OTM"
                                          )
            kwargs = _log_and_show(f"{ce_or_pe} {tag}", kwargs)
        # level 3
        elif kwargs["perc"]["curr_pfolio"] < -0.05:
            kwargs["adjust"]["adjust"] = 3
            tag = "adjust_neg_pfolio"
            reduced_value, lst_of_ords = reduce_value(
                kwargs["positions"],
                amount, ce_or_pe, tag
            )
            for ord in lst_of_ords:
                _order_place(**ord)
            if reduced_value < 0:
                kwargs["trailing"][ce_or_pe] += abs(reduced_value)
            kwargs = find_symbol_and_sell(kwargs,
                                          ce_or_pe, tag, price_type="OTM"
                                          )
            kwargs = _log_and_show(f"{ce_or_pe} {tag}", kwargs)
        # level 4
        elif kwargs["quantity"]["sell"] >= base["ADJUST_MAX_QTY"]:
            kwargs["adjust"]["adjust"] = 4
            tag = "adjust_max_qty"
            _, lst_of_ords = reduce_value(
                kwargs["positions"],
                amount, ce_or_pe, tag
            )
            for ord in lst_of_ords:
                _order_place(**ord)
            txt = f"{ce_or_pe} {kwargs['quantity']['sell']} >=" + \
                f"adjust_max_qty {base['ADJUST_MAX_QTY']}"
            kwargs = _log_and_show(txt, kwargs)
        # level 5
        else:
            ce_or_pe = "P" if ce_or_pe == "C" else "C"
            kwargs["adjust"]["adjust"] = 5
            tag = "adjust_fresh_sell"
            symbol = obj_sym.find_closest_premium(kwargs['quotes'],
                                                  base["ADJUST_SEL_PREMIUM"],
                                                  ce_or_pe)
            symbol = obj_sym.find_symbol_in_moneyness(symbol,
                                                      ce_or_pe,
                                                      "OTM")
            quantity = round_val_to_qty(
                amount,
                kwargs["quotes"][symbol],
                base['LOT_SIZE']
            )
            quantity = max(quantity, base["LOT_SIZE"])
            args = dict(
                symbol=symbol,
                quantity=quantity,
                side="S",
                tag=tag
            )
            _order_place(**args)

            kwargs = _log_and_show(
                f"{tag} {ce_or_pe} for {amount}",
                kwargs)
    return kwargs


def get_brkr_and_wserver():
    if common["live"]:
        brkr = Finvasia(**cnfg)
        if not brkr.authenticate():
            logging.error("Failed to authenticate")
            sys.exit(0)
        else:
            kwargs["quantity"] = _hl_cls(brkr, kwargs["quantity"])
            atm = obj_sym.get_atm(kwargs["quantity"]["cl"])
            dct_tokens = obj_sym.get_tokens(atm)
            lst_tokens = list(dct_tokens.keys())
            wserver = Wserver(brkr, lst_tokens, dct_tokens)
    else:
        dct_tokens = obj_sym.get_tokens(PAPER_ATM)
        lst_tokens = list(dct_tokens.keys())
        brkr = Paper(lst_tokens, dct_tokens)
        wserver = brkr
    return brkr, wserver


slp = 1
PAPER_ATM = 47100
SYMBOL = common["base"]
profit_val = base["ENTRY_PERC"] * 2 / 100 * base["MAX_QTY"] * base["LOT_SIZE"]
kwargs = {
    "quotes": {},
    "trailing": {"trailing": 0, "C": 0, "P": 0, "profit_val": profit_val},
    "perc": {"perc": "perc"},
    "adjust": {"adjust": 0, "max_qty": base['ADJUST_MAX_QTY']},
    "positions": [],
    "quantity": {"quantity": SYMBOL, "is_new": 0},
    "portfolio": {"is_pyramid": True,  "last": "Happy Trading"}
}

log_rotate()
obj_sym = Symbols(base['EXCHANGE'], SYMBOL, base["EXPIRY"])
obj_sym.get_exchange_token_map_finvasia()
pm = PortfolioManager()
brkr, wserver = get_brkr_and_wserver()
while not any(kwargs['quotes']):
    print("waiting for quote \n")
    kwargs['quotes'] = wserver.ltp
    print(kwargs['quotes'])
    sleep(slp)


kwargs = _reset_trail(**kwargs)
kwargs = _allowed_lot(**kwargs)
kwargs = _pyramid(**kwargs)
kwargs["portfolio"]["fn"] = is_pyramid_cond
while kwargs['portfolio'].get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = prettier(**kwargs)
    next_func = kwargs["portfolio"].pop("fn")
    kwargs = next_func(**kwargs)
