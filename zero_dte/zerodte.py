from toolkit.digits import Digits
from toolkit.regative import Regative
from time import sleep
from rich import print
from prettytable import PrettyTable
from constants import snse
from random import randint
from copy import deepcopy
from porfolio_manager import PortfolioManager

pm = PortfolioManager()


def random_func(start, end):
    # return a random number
    return randint(start, end)


def _prettify(lst):
    table = PrettyTable()
    table.field_names = lst[0].keys()
    for dct in lst:
        table.add_row(dct.values())
    print(table)


def _update_metrics(**kwargs):
    positions = kwargs["positions"]
    for pos in positions:
        # TODO
        if pos["qty"] < 0:
            pos["ltp"] = random_func(1, 111)
        pos["value"] = abs(pos["qty"] * pos["ltp"])
        pos["m2m"] = (pos["ltp"] - pos["entry"]) * pos["qty"]
    positions.sort(key=lambda x: x["value"], reverse=True)
    kwargs["value"] = sum(pos["value"] for pos in positions if pos["qty"] < 0)
    kwargs["m2m"] = sum(pos["m2m"] for pos in positions)
    kwargs["total_sell_positions"] = abs(
        sum(pos["qty"] for pos in positions if pos["qty"] < 0)
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


def enter_options_with_hedge(**kwargs):
    lotsize = 0
    if kwargs.get("total_sell_positions", 0) < snse["MAX_QTY"]:
        rough_total = snse["ENTRY_PERC"] / 100 * snse["MAX_QTY"]
        lotsize = int(rough_total / snse["LOT_SIZE"]) * snse["LOT_SIZE"]

    if lotsize > 0:
        kwargs["last"] = "enter options with hedge"
        pm.add_position(
            {
                "symbol": snse["SYMBOL"] + str(random_func(1, 5)) + "CE",
                "qty": -1 * lotsize,
                "ltp": snse["SEL_PREMIUM"],
                "entry": snse["SEL_PREMIUM"],
                "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            }
        )
        pm.add_position(
            {
                "symbol": snse["SYMBOL"] + str(random_func(16, 20)) + "CE",
                "qty": lotsize,
                "ltp": snse["BUY_PREMIUM"],
                "entry": snse["BUY_PREMIUM"],
                "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            }
        )
        pm.add_position(
            {
                "symbol": snse["SYMBOL"] + str(random_func(1, 5)) + "PE",
                "qty": -1 * lotsize,
                "ltp": snse["SEL_PREMIUM"],
                "entry": snse["SEL_PREMIUM"],
                "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            }
        )
        pm.add_position(
            {
                "symbol": snse["SYMBOL"] + str(random_func(16, 20)) + "PE",
                "qty": lotsize,
                "ltp": snse["BUY_PREMIUM"],
                "entry": snse["BUY_PREMIUM"],
                "value": snse["BUY_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
            }
        )
        kwargs["positions"] = pm.portfolio

    kwargs["fn"] = portfolio_conditions
    return kwargs


def portfolio_conditions(**kwargs):
    kwargs = _update_metrics(**kwargs)
    kwargs["fn"] = set_trailing_mode
    if kwargs["last"] == "enter options with hedge":
        return kwargs

    increase = kwargs["highest"] - kwargs["lowest"]
    if kwargs["m2m"] > kwargs["total_sell_positions"] * 2:
        kwargs["fn"] = enter_options_with_hedge
    elif (increase > kwargs["total_sell_positions"] * 5) and kwargs["m2m"] < 0:
        kwargs["fn"] = enter_options_with_hedge
    return kwargs


def set_trailing_mode(**kwargs):
    def _exit_by_trail(**kwargs):
        """
        buy 20% of the positions value
        starting from the highest ltp
        """
        if kwargs["trailing"]["decline_perc"] > 0.1:
            kwargs["last"] = "exit by trail"
            # TODO
            reduction_amount = 0.2 * kwargs["value"]
            reduction_qty = int(reduction_amount / snse["LOT_SIZE"]) * snse["LOT_SIZE"]
            print(f"{reduction_qty=} for {reduction_amount}")
            positions = deepcopy(kwargs["positions"])
            buy_pos = [pos for pos in positions if pos["qty"] > 0]
            _prettify(buy_pos)
            sell_pos = [pos for pos in positions if pos["qty"] < 0]
            _prettify(sell_pos)
            buy_pm = PortfolioManager(buy_pos)
            sell_pm = PortfolioManager(sell_pos)
            for cover_result in sell_pm.adjust_positions(reduction_qty):
                print(f"cover result: {cover_result}")
                endswith = "CE" if cover_result["symbol"].endswith("CE") else "PE"
                for sell_result in buy_pm.adjust_positions(
                    -1 * cover_result["reduction_qty"], endswith=endswith
                ):
                    print("sell_result: ", sell_result)
            kwargs.pop("trailing")
            sleep(10)
        kwargs["fn"] = enter_options_with_hedge
        return kwargs

    if kwargs["profit_on_pfolio"] >= 0.5 and kwargs["decline_perc"] >= 1:
        trailing_stop = True
    else:
        trailing_stop = False

    is_trailing = kwargs.get("trailing", False)
    if trailing_stop and not is_trailing:
        kwargs["trailing"] = {"highest": 0, "decline_perc": 0}
        kwargs["last"] = "trailing mode ON"
    elif not trailing_stop and is_trailing:
        kwargs.pop("trailing")
        kwargs["last"] = "trailing mode OFF"

    if trailing_stop:
        kwargs = _exit_by_trail(**kwargs)
    else:
        kwargs["fn"] = enter_options_with_hedge
    return kwargs


kwargs = {}
kwargs = enter_options_with_hedge(**kwargs)
kwargs = _update_metrics(**kwargs)
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
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
            print(k, ":", Regative(v))
    sleep(0.5)
