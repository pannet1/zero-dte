from toolkit.regative import Regative
from time import sleep
from rich import print
from prettytable import PrettyTable
from constants import snse, logging
from porfolio_manager import PortfolioManager
from random import randint
from toolkit.digits import Digits
from rich.live import Live
from rich.table import Table
import math


pm = PortfolioManager()
slp = 0.05


def simultp(ltp, speed, tick=0.05):
    new_ltp = round(ltp + (randint(-1 * speed, speed) * tick), 2)
    if new_ltp <= 0:
        new_ltp = tick
    return new_ltp


# TODO to be removed
def _prettify(lst):
    if isinstance(lst, dict):
        lst = [lst]
    table = PrettyTable()
    table.field_names = lst[0].keys()
    for dct in lst:
        table.add_row(dct.values())
    print(table)


def richest(**kwargs):
    def generate_table(dct) -> Table:
        table = Table()
        for key in dct:
            table.add_column(key)
        row_values = tuple()
        for key, value in dct.items():
            if isinstance(value, (int, float)) and value > 0:
                color = "[green]"
            elif isinstance(value, (int, float)):
                color = "[red]"
            else:
                color = "[blue]"
            colored = f"{color}{value}"
            row_values += (colored,)
        table.add_row(*row_values)
        print(table)

    for k, v in kwargs.items():
        if isinstance(v, dict):
            with Live(generate_table(v), refresh_per_second=1):
                pass
    return kwargs


def prettier(**kwargs) -> dict:
    for k, v in kwargs.items():
        table = PrettyTable()
        if isinstance(v, dict):
            table.field_names = v.keys()
            table.add_row(v.values())
            print(table)
        elif isinstance(v, list):
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
    kwargs["last"] = "pyramid complete"
    pm.add_position(
        {
            "symbol": snse["SYMBOL"] + str(randint(1, 5)) + "CE",
            "qty": -1 * kwargs["lotsize"],
            "ltp": snse["SEL_PREMIUM"],
            "entry": snse["SEL_PREMIUM"],
            "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
            "m2m": 0,
            "rpl": 0,
        }
    )
    pm.add_position(
        {
            "symbol": snse["SYMBOL"] + str(randint(16, 20)) + "CE",
            "qty": kwargs["lotsize"],
            "ltp": snse["BUY_PREMIUM"],
            "entry": snse["BUY_PREMIUM"],
            "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
            "m2m": 0,
            "rpl": 0,
        }
    )
    pm.add_position(
        {
            "symbol": snse["SYMBOL"] + str(randint(1, 5)) + "PE",
            "qty": -1 * kwargs["lotsize"],
            "ltp": snse["SEL_PREMIUM"],
            "entry": snse["SEL_PREMIUM"],
            "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
            "m2m": 0,
            "rpl": 0,
        }
    )
    pm.add_position(
        {
            "symbol": snse["SYMBOL"] + str(randint(16, 20)) + "PE",
            "qty": kwargs["lotsize"],
            "ltp": snse["BUY_PREMIUM"],
            "entry": snse["BUY_PREMIUM"],
            "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
            "m2m": 0,
            "rpl": 0,
        }
    )
    kwargs["positions"] = pm.portfolio
    return kwargs


def reset_trailing(**kwargs):
    kwargs["trailing"]["reset_high"] = -100
    kwargs["trailing"]["perc_decline"] = -100
    return kwargs


def _update_metrics(**kwargs):
    positions = kwargs["positions"]
    for pos in positions:
        # TODO
        if pos["qty"] < 0:
            pos["ltp"] = simultp(pos["ltp"], snse["SEL_PREMIUM"])
        elif pos["qty"] > 0:
            pos["ltp"] = simultp(pos["ltp"], snse["SEL_PREMIUM"] / 2)
        pos["value"] = int(pos["qty"] * pos["ltp"])
        pos["m2m"] = int((pos["ltp"] - pos["entry"]) * pos["qty"])
    positions.sort(key=lambda x: x["value"], reverse=False)

    # portfolio
    sell_value = sum(pos["value"] for pos in positions if pos["qty"] < 0)
    m2m = sum(pos["m2m"] for pos in positions)
    rpl = sum(pos["rpl"] for pos in positions)
    pnl = m2m + rpl
    if kwargs.get("portfolio", False):
        lowest = min(pnl, kwargs["portfolio"]["lowest"])
        highest = max(pnl, kwargs["portfolio"]["highest"])
    else:
        lowest = pnl
        highest = pnl

    kwargs["portfolio"] = dict(
        portfolio="portfolio",
        lowest=lowest,
        highest=highest,
        value=sell_value,
        m2m=m2m,
        rpl=rpl,
    )

    # quantity
    sell = abs(sum(pos["qty"] for pos in positions if pos["qty"] < 0))
    buy = sum(pos["qty"] for pos in positions if pos["qty"] > 0)
    closed = sum(pos["qty"] for pos in positions if pos["qty"] == 0)
    kwargs["quantity"] = dict(
        quantity="quantity", sell=sell, buy=buy, closed=closed, total=buy - sell
    )

    # percentages
    max_pfolio = Digits.calc_perc(highest, snse["PFOLIO"])
    curr_pfolio = Digits.calc_perc(pnl, snse["PFOLIO"])
    decline = round(max_pfolio - curr_pfolio, 2)
    kwargs["perc"] = dict(
        perc="perc",
        max_pfolio=max_pfolio,
        curr_pfolio=curr_pfolio,
        decline=decline,
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
            kwargs["trailing"]["trailing"] == -1
            and kwargs["trailing"]["perc_decline"] >= 1
        ):
            kwargs["trailing"]["trailing"] = 0
            logging.debug(
                f"trailing :{max_pfolio=}>0.5 and "
                + f"decline{kwargs['trailing']['perc_decline']} >= 1 "
            )
            kwargs = reset_trailing(**kwargs)

    # adjustment
    call_value = sum(
        pos["value"]
        for pos in positions
        if pos["symbol"].endswith("CE") and pos["qty"] < 0
    )
    put_value = sum(
        pos["value"]
        for pos in positions
        if pos["symbol"].endswith("PE") and pos["qty"] < 0
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
        ratio=round(ratio, 2),
        amount=round(ratio * snse["ADJUST_PERC"] / 100, 2),
    )

    kwargs["pnl"] = pnl
    sleep(slp)
    return kwargs


def is_pyramid_cond(**kwargs):
    kwargs = _update_metrics(**kwargs)
    kwargs = _calculate_allowable_quantity(**kwargs)
    kwargs["fn"] = is_trailing_cond

    if kwargs["lotsize"] > 0 and (
        kwargs["last"] != "attempt to pyramid" or kwargs["last"] != "pyramid complete"
    ):
        increase = kwargs["portfolio"]["highest"] - kwargs["portfolio"]["lowest"]
        if kwargs["pnl"] > kwargs["quantity"]["sell"] * 2:
            kwargs["last"] = "attempt to pyramid"
            kwargs = _pyramid(**kwargs)
        elif increase > kwargs["quantity"]["sell"] * 5 and kwargs["pnl"] < 0:
            kwargs["last"] = "attempt to pyramid"
            kwargs = _pyramid(**kwargs)

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
            kwargs["last"] = "exit by trail"
            logging.debug(f' {kwargs["trailing"]["perc_decline"]} > 0.1 ')
            value_to_reduce = int(-0.2 * kwargs["portfolio"]["value"] / 2)
            logging.debug(
                f'{value_to_reduce=}= -0.2 X value {kwargs["portfolio"]["value"]} / 2'
            )
            print(f"INITIAL VALUE TO REDUCE: {value_to_reduce}")
            print("======== AFTER TRAIL ========")
            pm.portfolio = kwargs["positions"]
            call_value_to_reduce = pm.trailing_full(
                value_to_reduce, endswith="CE", lotsize=50
            )
            print("call values to reduce:", call_value_to_reduce)
            put_value_to_reduce = pm.trailing_full(
                value_to_reduce, endswith="PE", lotsize=50
            )
            print("put values to reduce:", put_value_to_reduce)
            quotes = {
                snse["SYMBOL"] + "6" + "CE": simultp(16, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "7" + "CE": simultp(17, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "8" + "CE": simultp(18, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "9" + "CE": simultp(19, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "10" + "CE": simultp(20, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "6" + "PE": simultp(16, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "7" + "PE": simultp(17, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "8" + "PE": simultp(18, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "9" + "PE": simultp(19, snse["SEL_PREMIUM"]),
                snse["SYMBOL"] + "10" + "PE": simultp(20, snse["SEL_PREMIUM"]),
            }
            if call_value_to_reduce < 0:
                symbol_name = pm.find_closest_premium(
                    quotes, snse["SEL_PREMIUM"], endswith="CE"
                )
                lots = math.ceil(
                    call_value_to_reduce / quotes[symbol_name] / snse["LOT_SIZE"]
                )
                print(f"sell {lots}fresh call {symbol_name} @ {quotes[symbol_name]}")
                pm.add_position(
                    {
                        "symbol": symbol_name,
                        "qty": lots * snse["LOT_SIZE"],
                        "ltp": quotes[symbol_name],
                        "entry": quotes[symbol_name],
                        "value": quotes[symbol_name] * snse["LOT_SIZE"],
                        "m2m": 0,
                        "rpl": 0,
                    }
                )
            if put_value_to_reduce < 0:
                symbol_name = pm.find_closest_premium(
                    quotes, snse["SEL_PREMIUM"], endswith="PE"
                )
                lots = math.ceil(
                    put_value_to_reduce / quotes[symbol_name] / snse["LOT_SIZE"]
                )
                print(f"sell {lots}fresh put {symbol_name} @ {quotes[symbol_name]}")
                pm.add_position(
                    {
                        "symbol": symbol_name,
                        "qty": lots * snse["LOT_SIZE"],
                        "ltp": quotes[symbol_name],
                        "entry": quotes[symbol_name],
                        "value": quotes[symbol_name] * snse["LOT_SIZE"],
                        "m2m": 0,
                        "rpl": 0,
                    }
                )
            pm.portfolio = [
                {k: v for k, v in pos.items() if k != "reduced_qty"}
                for pos in pm.portfolio
            ]
            kwargs["positions"] = pm.portfolio
            _prettify(kwargs["positions"])
            kwargs["trailing"]["trailing"] += 1
            sleep(10)
            # TODO
        return kwargs

    # set values
    # kwargs["fn"] = is_buy_to_cover
    kwargs["fn"] = is_pyramid_cond
    if kwargs["trailing"]["trailing"] <= 4:
        kwargs = _exit_by_trail(**kwargs)
    elif kwargs["trailing"]["trailing"] == 5:
        print("close all positions")
        kwargs.pop("fn")

    return kwargs


def is_buy_to_cover(**kwargs):
    kwargs["fn"] = is_pyramid_cond
    is_call_in_pos = any(
        pos["symbol"].endswith("CE")
        and pos["qty"] < 0
        and pos["ltp"] > snse["MAX_SOLD_LTP"]
        for pos in kwargs["positions"]
    )
    if kwargs["adjust"]["ratio"] > snse["DIFF_THRESHOLD"] and is_call_in_pos:
        quantity = kwargs["adjust"]["amount"] / snse["ADJUST_BUY_PREMIUM"]
        total_qty = int(quantity / snse["LOT_SIZE"]) * snse["LOT_SIZE"]
        for buy_order in pm.adjust_quantity(total_qty, endswith="CE"):
            adjusted_qty = buy_order.pop("adjusted_qty")
            print(f"{adjusted_qty} to be adjusted {buy_order}")
            for sell_order in pm.adjust_quantity(-1 * adjusted_qty, endswith="CE"):
                print(f"adjusted {sell_order}")
        kwargs["adjust"]["adjust"] = True
        kwargs["last"] = "adjust mode ON"
    return kwargs


kwargs = {
    "last": "Happy Trading",
    "trailing": {"trailing": -1},
}
kwargs = reset_trailing(**kwargs)
kwargs = _calculate_allowable_quantity(**kwargs)
kwargs = _pyramid(**kwargs)
# we dont have fn key till now, so add it
kwargs["fn"] = is_pyramid_cond
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = prettier(**kwargs)
    next_func = kwargs.pop("fn")
    kwargs = next_func(**kwargs)
