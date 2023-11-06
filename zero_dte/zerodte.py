from toolkit.regative import Regative
from time import sleep
from rich import print
from prettytable import PrettyTable
from constants import snse
from porfolio_manager import PortfolioManager
from random import randint
from toolkit.digits import Digits
from rich.live import Live
from rich.table import Table


pm = PortfolioManager()


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


def _reset_trailing(**kwargs):
    kwargs["trailing"]["reset_high"] = 0
    kwargs["trailing"]["decline"] = 0
    return kwargs


def is_pyramid_cond(**kwargs):
    kwargs = update_metrics(**kwargs)
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


def update_metrics(**kwargs):
    positions = kwargs.get("positions", [])
    for pos in positions:
        # TODO
        if pos["qty"] < 0:
            pos["ltp"] = simultp(pos["ltp"], 25)
        elif pos["qty"] > 0:
            pos["ltp"] = simultp(pos["ltp"], 1)
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
    if kwargs.get("trailing", "EMPTY") == "EMPTY":
        kwargs["trailing"] = dict(trailing=False, reset_high=0, perc_decline=0)

    if kwargs["perc"]["curr_pfolio"] >= 0.5 and kwargs["perc"]["decline"] >= 1:
        trailing_stop = True
    else:
        trailing_stop = False

    is_trailing = kwargs["trailing"]["trailing"]
    if trailing_stop and not is_trailing:
        kwargs["trailing"]["trailing"] = True
        kwargs = _reset_trailing(**kwargs)
        kwargs["last"] = "trailing mode ON"
    elif not trailing_stop and is_trailing:
        kwargs["trailing"]["trailing"] = False
        kwargs = _reset_trailing(**kwargs)
        kwargs["last"] = "trailing mode OFF"

    if trailing_stop:
        kwargs["trailing"]["reset_high"] = max(
            curr_pfolio, kwargs["trailing"]["reset_high"]
        )
        kwargs["trailing"]["perc_decline"] = (
            kwargs["trailing"]["reset_high"] - curr_pfolio
        )

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
    sleep(3)
    return kwargs


# TODO should only return true or false
def is_trailing_cond(**kwargs):
    kwargs["fn"] = is_buy_to_cover

    def _exit_by_trail(**kwargs):
        """
        buy 20% of the positions sell value value
        starting from the high-est ltp
        """
        if kwargs["trailing"]["perc_decline"] > 0.1:
            kwargs["last"] = "exit by trail"

            reduction_amount = 0.2 * kwargs["portfolio"]["value"]
            reduction_qty = int(reduction_amount / snse["LOT_SIZE"]) * snse["LOT_SIZE"]
            print(f"{reduction_qty=} for {reduction_amount}")

            positions = kwargs["positions"]
            buy_pos = [pos for pos in positions if pos["qty"] > 0]
            _prettify(buy_pos)
            sell_pos = [pos for pos in positions if pos["qty"] < 0]
            _prettify(sell_pos)
            zero_pos = [pos for pos in positions if pos["qty"] == 0]

            buy_pm = PortfolioManager(buy_pos)
            sell_pm = PortfolioManager(sell_pos)
            for cover_result in sell_pm.adjust_positions(reduction_qty):
                print(f"cover result: {cover_result}")
                endswith = "CE" if cover_result["symbol"].endswith("CE") else "PE"
                for sell_result in buy_pm.adjust_positions(
                    -1 * cover_result["reduction_qty"], endswith=endswith
                ):
                    print("sell_result: ", sell_result)

            kwargs["positions"] = buy_pm.portfolio + sell_pm.portfolio
            # delete all key value with key["reduction_qty"]
            for pos in kwargs["positions"]:
                pos.pop("reduction_qty")
                # pm.replace_position(pos)
            pm.portfolio = kwargs["positions"] + zero_pos
            kwargs = _reset_trailing(**kwargs)
        return kwargs

    # set values
    if kwargs["trailing"]["trailing"]:
        kwargs = _exit_by_trail(**kwargs)
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
        for buy_order in pm.adjust_positions(total_qty, endswith="CE"):
            adjusted_qty = buy_order.pop("adjusted_qty")
            print(f"to be adjusted {buy_order}")
            for sell_order in pm.adjust_positions(-1 * adjusted_qty, endswith="CE"):
                print(f"adjusted {sell_order}")
        kwargs["adjust"]["adjust"] = True
        kwargs["last"] = "adjust mode ON"
    return kwargs


kwargs = {"last": "Happy Trading"}
kwargs = _calculate_allowable_quantity(**kwargs)
kwargs = _pyramid(**kwargs)
# we dont have fn key till now, so add it
kwargs["fn"] = is_pyramid_cond
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = prettier(**kwargs)
    next_func = kwargs.pop("fn")
    kwargs = next_func(**kwargs)
