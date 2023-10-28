from stratergy.base import OptionsStrategy
from typing import Dict
from time import sleep
from rich import print
from constants import snse
from random import randint


def random_func(start, end):
    # return a random number
    return randint(start, end)


def _update_metrics(**kwargs):
    kwargs["m2m"] = random_func(-50000, 50000)
    kwargs["total_positions"] = random_func(50, 5000)
    kwargs["lowest"] = min(kwargs["m2m"], kwargs.get("lowest", kwargs["m2m"]))
    kwargs["highest"] = max(kwargs["m2m"], kwargs.get("highest", kwargs["m2m"]))
    print("update_metrics")
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
        kwargs["fn"] = portfolio_conditions
    print("pfortfolio_conditions")
    return kwargs


def trailing_stop(**kwargs):
    profit_on_pfolio = calculate_percentage(kwargs["m2m"], snse["PFOLIO"])
    decline_perc = calculate_percentage(
        kwargs["highest"] - kwargs["m2m"], snse["PFOLIO"]
    )
    kwargs["txt"] = "trailing stop"
    kwargs["fn"] = portfolio_conditions
    return kwargs


def enter_options_with_hedge(**kwargs):
    print("enter_options_with_hedge")
    kwargs["txt"] = "entry options with hedge"
    kwargs["fn"] = portfolio_conditions
    return kwargs


kwargs = {"fn": enter_options_with_hedge}
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = _update_metrics(**kwargs)
    next_function = kwargs.pop("fn")
    kwargs = next_function(**kwargs)
    print(kwargs)
    sleep(1)
