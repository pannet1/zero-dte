from toolkit.digits import Digits
from time import sleep
from rich import print
from prettytable import PrettyTable
from constants import snse
from random import randint


def random_func(start, end):
    # return a random number
    return randint(start, end)


def _update_metrics(**kwargs):
    positions = kwargs["positions"]
    for pos in positions:
        # TODO
        if pos["qty"] < 0:
            pos["ltp"] = random_func(1, 100)
        pos["value"] = abs(pos["qty"] * pos["ltp"])
        pos["m2m"] = (pos["ltp"] - pos["entry"]) * pos["qty"]

    kwargs["m2m"] = sum(pos["m2m"] for pos in positions)
    kwargs["total_sell_positions"] = sum(
        pos["qty"] for pos in positions if pos["qty"] < 0
    )
    kwargs["total_buy_positions"] = sum(
        pos["qty"] for pos in positions if pos["qty"] > 0
    )
    kwargs["total_positions"] = (
        kwargs["total_sell_positions"] + kwargs["total_buy_positions"]
    )
    kwargs["lowest"] = min(kwargs["m2m"], kwargs.get("lowest", kwargs["m2m"]))
    kwargs["highest"] = max(kwargs["m2m"], kwargs.get("highest", kwargs["m2m"]))
    kwargs["profit_on_pfolio"] = Digits.calc_perc(kwargs["m2m"], snse["PFOLIO"])
    kwargs["decline_perc"] = Digits.calc_perc(
        (kwargs["highest"] - kwargs["m2m"]), kwargs["highest"]
    )
    if kwargs.get("trailing", False):
        kwargs["trailing"]["highest"] = max(
            kwargs["m2m"], kwargs["trailing"]["highest"]
        )
        kwargs["trailing"]["decline_perc"] = Digits.calc_perc(
            (kwargs["trailing"]["highest"] - kwargs["m2m"]),
            kwargs["trailing"]["highest"],
        )
    return kwargs


def portfolio_conditions(**kwargs):
    increase = kwargs["highest"] - kwargs["lowest"]
    if kwargs["m2m"] > kwargs["total_positions"] * 2:
        kwargs["fn"] = enter_options_with_hedge
        kwargs["txt"] = "entry positive portfolio"
    elif (increase > kwargs["total_positions"] * 5) and kwargs["m2m"] < 0:
        kwargs["fn"] = enter_options_with_hedge
        kwargs["txt"] = "entry negative portfolio"
    else:
        kwargs["txt"] = "portfolio condtions"
        kwargs["fn"] = set_trailing_mode
    return kwargs


def set_trailing_mode(**kwargs):
    if kwargs["profit_on_pfolio"] >= 0.5 and kwargs["decline_perc"] >= 1:
        trailing_stop = True
    else:
        trailing_stop = False

    is_trailing = kwargs.get("trailing", False)
    if trailing_stop and not is_trailing:
        kwargs["trailing"] = {"highest": 0, "decline_perc": 0}
        kwargs["txt"] = "trailing mode ON"
    elif not trailing_stop and is_trailing:
        kwargs.pop("trailing")
        kwargs["txt"] = "trailing mode OFF"

    if trailing_stop:
        _exit_by_trail(**kwargs)
    else:
        kwargs["fn"] = portfolio_conditions
    return kwargs


def _exit_by_trail(**kwargs):
    """
    buy 20% of the positions value
    starting from the highest ltp
    """


def enter_options_with_hedge(**kwargs):
    is_positions = kwargs.get("positions", False)
    if is_positions:
        new_list = [
            {
                "symbol": "CE",
                "qty": -1 * snse["LOT_SIZE"],
                "ltp": snse["SEL_PREMIUM"],
                "entry": snse["SEL_PREMIUM"],
                "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
            {
                "symbol": "CE",
                "qty": snse["LOT_SIZE"],
                "ltp": snse["BUY_PREMIUM"],
                "entry": snse["BUY_PREMIUM"],
                "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
            {
                "symbol": "PE",
                "qty": -1 * snse["LOT_SIZE"],
                "ltp": snse["SEL_PREMIUM"],
                "entry": snse["SEL_PREMIUM"],
                "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
            {
                "symbol": "PE",
                "qty": snse["LOT_SIZE"],
                "ltp": snse["BUY_PREMIUM"],
                "entry": snse["BUY_PREMIUM"],
                "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
        ]
        # append new_list to is_positions list
        is_positions += new_list
    else:
        kwargs["positions"] = [
            {
                "symbol": "CE",
                "qty": -1 * snse["LOT_SIZE"],
                "ltp": snse["SEL_PREMIUM"],
                "entry": snse["SEL_PREMIUM"],
                "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
            {
                "symbol": "CE",
                "qty": snse["LOT_SIZE"],
                "ltp": snse["BUY_PREMIUM"],
                "entry": snse["BUY_PREMIUM"],
                "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
            {
                "symbol": "PE",
                "qty": -1 * snse["LOT_SIZE"],
                "ltp": snse["SEL_PREMIUM"],
                "entry": snse["SEL_PREMIUM"],
                "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
            {
                "symbol": "PE",
                "qty": snse["LOT_SIZE"],
                "ltp": snse["BUY_PREMIUM"],
                "entry": snse["BUY_PREMIUM"],
                "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            },
        ]
    kwargs["txt"] = "entry options with hedge"
    kwargs["fn"] = portfolio_conditions
    return kwargs


kwargs = {}
kwargs = enter_options_with_hedge(**kwargs)
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = _update_metrics(**kwargs)
    next_function = kwargs.pop("fn")
    kwargs = next_function(**kwargs)

    for k, v in kwargs.items():
        if k == "positions":
            table = PrettyTable()
            column_names = v[0].keys()
            table.field_names = column_names
            for item in v:
                table.add_row(item.values())
            print(table)
        else:
            print(f"{k}: {v}")
    sleep(1)
