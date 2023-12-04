from numpy import who
from toolkit.regative import Regative
from symbols import Symbols
from time import sleep
from rich import print
from prettytable import PrettyTable
from constants import snse, logging, common, cnfg
from porfolio_manager import PortfolioManager
from toolkit.digits import Digits
import math
import re

slp = 1
pm = PortfolioManager([], snse)
symbols = Symbols("NFO", snse["SYMBOL"], snse["EXPIRY"])

if common["live"]:
    from omspy_brokers.finvasia import Finvasia

    brkr = Finvasia(**cnfg)
    if not brkr.authenticate():
        logging.error("Failed to authenticate")
        SystemExit(1)

    resp = brkr.finvasia.get_quotes("NSE", "1201")
    print(resp)
else:
    from paper import Paper

    dct_tokens = symbols.get_tokens(20250)
    lst_tokens = list(dct_tokens.keys())
    brkr = Paper(lst_tokens)
    wserver = brkr


def last_print(text, kwargs):
    logging.debug(text)
    kwargs["last"] = text
    return kwargs


# TODO to be removed
def _prettify(lst):
    if isinstance(lst, dict):
        lst = [lst]
    table = PrettyTable()
    table.field_names = lst[0].keys()
    for dct in lst:
        table.add_row(dct.values())
    print(table)


def prettier(**kwargs) -> dict:
    for k, v in kwargs.items():
        table = PrettyTable()
        if isinstance(v, dict):
            if v == "quotes":
                continue
            table.field_names = v.keys()
            table.add_row(v.values())
            print(table)
        elif isinstance(v, list) and any(v):
            table.field_names = v[0].keys()
            for item in v:
                table.add_row(item.values())
            print(table)
        else:
            print(k, ":", Regative(v))
    print(25 * "=", " END OF REPORT ", 25 * "=", "\n")
    return kwargs


def _calculate_allowable_quantity(**kwargs):
    kwargs["lotsize"] = 0
    if (
        kwargs.get("quantity", "EMPTY") == "EMPTY"
        or kwargs["quantity"]["sell"] < snse["MAX_QTY"]
    ):
        rough_total = snse["ENTRY_PERC"] / 100 * snse["MAX_QTY"]
        kwargs["lotsize"] = int(rough_total / snse["LOT_SIZE"]) * snse["LOT_SIZE"]
    return kwargs


def _pyramid(**kwargs):
    symbol = pm.find_closest_premium(
        kwargs["quotes"], snse["SEL_PREMIUM"], contains="C"
    )
    brkr.order_place(
        {
            "symbol": symbol,
            "qty": kwargs["lotsize"],
            "side": "S",
            "prc": kwargs["quotes"][symbol],
            "tag": "pyramid",
        }
    )
    symbol = pm.find_closest_premium(
        kwargs["quotes"], snse["BUY_PREMIUM"], contains="C"
    )
    brkr.order_place(
        {
            "symbol": symbol,
            "qty": kwargs["lotsize"],
            "side": "B",
            "prc": kwargs["quotes"][symbol],
            "tag": "pyramid",
        }
    )
    symbol = pm.find_closest_premium(
        kwargs["quotes"], snse["SEL_PREMIUM"], contains="P"
    )
    brkr.order_place(
        {
            "symbol": symbol,
            "qty": kwargs["lotsize"],
            "side": "S",
            "prc": kwargs["quotes"][symbol],
            "tag": "pyramid",
        }
    )
    symbol = pm.find_closest_premium(
        kwargs["quotes"], snse["BUY_PREMIUM"], contains="P"
    )
    brkr.order_place(
        {
            "symbol": symbol,
            "qty": kwargs["lotsize"],
            "side": "B",
            "prc": kwargs["quotes"][symbol],
            "tag": "pyramid",
        }
    )
    pm.update(brkr.positions, sort_key="qty")
    return kwargs


def reset_trailing(**kwargs):
    kwargs["trailing"]["reset_high"] = -100
    kwargs["trailing"]["perc_decline"] = -100
    return kwargs


def _update_metrics(**kwargs):
    def _calc_m2m(pos):
        if pos["qty"] > 0:
            return (pos["ltp"] - pos["quantity_buy"]) * pos["price_buy"]
        else:
            return (pos["quantity_buy"] - pos["ltp"]) * pos["price_buy"]

    kwargs["positions"] = pm.portfolio
    for pos in kwargs["positions"]:
        pos["ltp"] = kwargs["quotes"][pos["symbol"]]
        pos["value"] = int(pos["qty"] * pos["ltp"])
        pos["m2m"] = _calc_m2m(pos) if pos["qty"] != 0 else 0
        # TODO
        pos["rpl"] = pos["value"] - (pos["sold"] - pos["bought"])
    # positions.sort(key=lambda x: x["value"], reverse=False)

    # portfolio
    sell_value = sum(pos["value"] for pos in kwargs["positions"] if pos["qty"] < 0)
    m2m = sum(pos["m2m"] for pos in kwargs["positions"])
    rpl = sum(pos["rpl"] for pos in kwargs["positions"])
    pnl = m2m + rpl
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
        m2m=m2m,
        rpl=rpl,
    )

    # quantity
    sell = abs(sum(pos["qty"] for pos in kwargs["positions"] if pos["qty"] < 0))
    buy = sum(pos["qty"] for pos in kwargs["positions"] if pos["qty"] > 0)
    closed = sum(pos["qty"] for pos in kwargs["positions"] if pos["qty"] == 0)
    kwargs["quantity"] = dict(
        quantity="quantity", sell=sell, buy=buy, closed=closed, total=buy - sell
    )

    # percentages
    max_pfolio = Digits.calc_perc(highest, snse["PFOLIO"])
    curr_pfolio = Digits.calc_perc(pnl, snse["PFOLIO"])
    decline = round(max_pfolio - curr_pfolio, 2)
    min_pfolio = Digits.calc_perc(lowest, snse["PFOLIO"])
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
        if re.search(re.escape(snse["EXPIRY"] + "C"), pos["symbol"]) and pos["qty"] < 0
    )
    put_value = sum(
        pos["value"]
        for pos in kwargs["positions"]
        if re.search(re.escape(snse["EXPIRY"] + "P"), pos["symbol"]) and pos["qty"] < 0
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
        amount=abs(int(diff * snse["ADJUST_PERC"] / 100)),
    )

    kwargs["pnl"] = pnl
    sleep(0.5)
    return kwargs


def is_pyramid_cond(**kwargs):
    quotes = wserver.ltp
    kwargs["quotes"] = {dct_tokens[key]: value for key, value in quotes.items()}
    kwargs = _update_metrics(**kwargs)
    kwargs = _calculate_allowable_quantity(**kwargs)
    kwargs["fn"] = is_trailing_cond

    if (
        kwargs["lotsize"] > 0
        and (
            kwargs["last"] != "attempt to pyramid"
            or kwargs["last"] != "pyramid complete"
        )
        and kwargs["portfolio"]["portfolio"]
    ):
        increase = kwargs["portfolio"]["highest"] - kwargs["portfolio"]["lowest"]
        if (
            (kwargs["pnl"] > kwargs["quantity"]["sell"] * 2)
            or (increase > kwargs["quantity"]["sell"] * 5)
        ) and kwargs["pnl"] < 0.5:
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
            print(f"INITIAL VALUE TO REDUCE: {value_to_reduce}")
            print("======== AFTER TRAIL ========")
            pm.portfolio = kwargs["positions"]
            call_value_to_reduce = pm.reduce_value(value_to_reduce, contains="CE")
            print("call values to reduce:", call_value_to_reduce)
            put_value_to_reduce = pm.reduce_value(value_to_reduce, contains="PE")
            print("put values to reduce:", put_value_to_reduce)
            if call_value_to_reduce < 0:
                symbol = pm.find_closest_premium(
                    kwargs["quotes"], snse["SEL_PREMIUM"], contains="C"
                )
                lots = math.ceil(
                    call_value_to_reduce / quotes[symbol] / snse["LOT_SIZE"]
                )
                print(f"sell {lots=}fresh call {symbol}")
                brkr.order_place(
                    {
                        "symbol": symbol,
                        "qty": lots * kwargs["lotsize"],
                        "side": "S",
                        "prc": kwargs["quotes"][symbol],
                        "tag": "trail",
                    }
                )
            if put_value_to_reduce < 0:
                symbol = pm.find_closest_premium(
                    kwargs["quotes"], snse["SEL_PREMIUM"], contains="P"
                )
                lots = math.ceil(
                    put_value_to_reduce / quotes[symbol] / snse["LOT_SIZE"]
                )
                print(f"sell {lots=} fresh put {symbol}")
                brkr.order_place(
                    {
                        "symbol": symbol,
                        "qty": lots * kwargs["lotsize"],
                        "side": "S",
                        "prc": kwargs["quotes"][symbol],
                        "tag": "trail",
                    }
                )
            kwargs["positions"] = pm.update()
            _prettify(kwargs["positions"])
            kwargs["last"] = f'trailed level: {kwargs["trailing"]["trailing"]}'
            kwargs["trailing"]["trailing"] += 1
            # TODO
        return kwargs

    # set values
    kwargs["fn"] = adjust
    if 0 < kwargs["trailing"]["trailing"] <= 4:
        kwargs = _exit_by_trail(**kwargs)
    elif kwargs["trailing"]["trailing"] == 5:
        if kwargs["trailing"]["perc_decline"] >= 1.5:
            for pos in pm.close_positions():
                print("order place", pos)
    return kwargs


def adjust(**kwargs):
    kwargs["fn"] = profit
    pm.update(kwargs["positions"], "ltp")
    ce_or_pe = None

    if kwargs["adjust"]["ratio"] >= snse["DIFF_THRESHOLD"] * 5:
        sleep(slp)
        ce_or_pe = "CE"
    elif kwargs["adjust"]["ratio"] <= snse["DIFF_THRESHOLD"] * -2:
        sleep(slp)
        ce_or_pe = "PE"

    if ce_or_pe:
        kwargs["adjust"]["adjust"] = False
        if pm.is_above_highest_ltp(contains=ce_or_pe):
            kwargs = last_print(f"{ce_or_pe} adjust_highest", kwargs)
            buy_entry = pm.adjust_highest_ltp(kwargs["adjust"]["amount"], ce_or_pe)
            print(f"{buy_entry=}")
            kwargs["adjust"]["adjust"] = True
        if kwargs["perc"]["decline"] > 0.25:
            kwargs = last_print(f"{ce_or_pe} adjust_detoriation", kwargs)
            pm.reduce_value(kwargs["adjust"]["amount"], contains=ce_or_pe)
            kwargs["adjust"]["adjust"] = True
        if kwargs["portfolio"]["m2m"] < 0:
            kwargs = last_print(f"{ce_or_pe} adjust_negative_pnl", kwargs)
            pm.reduce_value(kwargs["adjust"]["amount"], contains=ce_or_pe)
            kwargs["adjust"]["adjust"] = True
        if kwargs["quantity"]["sell"] >= snse["MAX_QTY"]:
            kwargs = last_print(f"{ce_or_pe} adjust_max_qty", kwargs)
            pm.reduce_value(kwargs["adjust"]["amount"], contains=ce_or_pe)
            kwargs["adjust"]["adjust"] = True
        if not kwargs["adjust"]["adjust"]:
            ce_or_pe = "PE" if ce_or_pe == "CE" else "CE"
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
    ce_qty = pm.close_profiting_position("CE")
    if ce_qty < 0:
        print("take CE new positions")
    pe_qty = pm.close_profiting_position("PE")
    if pe_qty < 0:
        print("take PE new position")
    return kwargs


def is_portfolio_stop(**kwargs):
    kwargs["fn"] = is_pyramid_cond
    if kwargs["perc"]["curr_pfolio"] < snse["PFOLIO_SL_PERC"]:
        for pos in pm.close_positions():
            print("order place", pos)
        kwargs = last_print("portfolio stop hit", kwargs)
        kwargs.pop("fn")
    return kwargs


kwargs = {
    "last": "Happy Trading",
    "trailing": {"trailing": 0},
}
kwargs = reset_trailing(**kwargs)
kwargs = _calculate_allowable_quantity(**kwargs)
quotes = wserver.ltp
kwargs["quotes"] = {dct_tokens[key]: value for key, value in quotes.items()}
kwargs = _pyramid(**kwargs)
kwargs["fn"] = is_pyramid_cond
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = prettier(**kwargs)
    next_func = kwargs.pop("fn")
    kwargs = next_func(**kwargs)
