from toolkit.digits import Digits
from toolkit.regative import Regative
from time import sleep
from rich import print
from prettytable import PrettyTable
from constants import snse
from random import randint
from porfolio_manager import PortfolioManager

pm = PortfolioManager()


def random_func(start, end):
    # return a random number
    return randint(start, end)


def _prettify(lst):
    if isinstance(lst, dict):
        lst = [lst]
    table = PrettyTable()
    table.field_names = lst[0].keys()
    for dct in lst:
        table.add_row(dct.values())
    print(table)


def pyramid(**kwargs):
    kwargs["fn"] = portfolio_conditions
    lotsize = 0
    if (
        kwargs.get("quantity", "EMPTY") == "EMPTY"
        or kwargs["quantity"]["sell"] < snse["MAX_QTY"]
    ):
        rough_total = snse["ENTRY_PERC"] / 100 * snse["MAX_QTY"]
        lotsize = int(rough_total / snse["LOT_SIZE"]) * snse["LOT_SIZE"]

    if lotsize > 0:
        kwargs["last"] = "pyramid complete"
        pm.add_position(
            {
                "symbol": snse["SYMBOL"] + str(random_func(1, 5)) + "CE",
                "qty": -1 * lotsize,
                "ltp": snse["SEL_PREMIUM"],
                "entry": snse["SEL_PREMIUM"],
                "value": snse["SEL_PREMIUM"] * snse["LOT_SIZE"],
                "m2m": 0,
                "rpl": 0,
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
                "rpl": 0,
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
                "rpl": 0,
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
                "rpl": 0,
            }
        )
        kwargs["positions"] = pm.portfolio

    return kwargs


def _update_metrics(**kwargs):
    positions = kwargs["positions"]
    for pos in positions:
        # TODO
        if pos["qty"] < 0:
            pos["ltp"] = random_func(1, 111)
        pos["value"] = pos["qty"] * pos["ltp"]
        pos["m2m"] = (pos["ltp"] - pos["entry"]) * pos["qty"]
    positions.sort(key=lambda x: x["value"], reverse=False)

    # portfolio
    sell_value = abs(sum(pos["value"] for pos in positions if pos["qty"] < 0))
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
    on_pfolio = Digits.calc_perc(pnl, snse["PFOLIO"])
    decline = Digits.calc_perc((highest - pnl), highest)
    kwargs["perc"] = dict(
        perc="perc",
        on_pfolio=on_pfolio,
        decline=decline,
    )

    # trailing mode
    if kwargs.get("trailing", False):
        kwargs["trailing"]["reset_high"] = max(pnl, kwargs["trailing"]["reset_high"])
        kwargs["trailing"]["perc_decline"] = Digits.calc_perc(
            (kwargs["trailing"]["reset_high"] - pnl),
            kwargs["trailing"]["reset_high"],
        )

    # adjustment
    call_value = sum(pos["value"] for pos in positions if pos["symbol"].endswith("CE"))
    put_value = sum(pos["value"] for pos in positions if pos["symbol"].endswith("PE"))
    diff = call_value - put_value
    ratio = 0 if sell_value == 0 else diff / sell_value

    kwargs["adjust"] = dict(
        adjust="adjust",
        call_value=call_value,
        put_value=put_value,
        diff=diff,
        ratio=round(ratio, 2),
        amount=round(ratio * snse["ADJUST_PERC"] / 100, 2),
    )

    kwargs["pnl"] = pnl
    return kwargs


def portfolio_conditions(**kwargs):
    kwargs["fn"] = set_trailing_mode
    if kwargs["last"] != "attempt to pyramid" or kwargs["last"] != "pyramid complete":
        increase = kwargs["portfolio"]["highest"] - kwargs["portfolio"]["lowest"]
        if kwargs["pnl"] > kwargs["quantity"]["sell"] * 2:
            kwargs["last"] = "pyramid complete"
            kwargs["fn"] = pyramid
        elif increase > kwargs["quantity"]["sell"] * 5 and kwargs["pnl"] < 0:
            kwargs["last"] = "pyramid complete"
            kwargs["fn"] = pyramid
    return kwargs


def set_trailing_mode(**kwargs):
    kwargs["fn"] = adjust_buy_to_cover

    def _exit_by_trail(**kwargs):
        """
        buy 20% of the positions sell value value
        starting from the high-est ltp
        """
        kwargs["fn"] = adjust_buy_to_cover
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

            kwargs.pop("trailing")
            sleep(10)
        return kwargs

    if kwargs["perc"]["on_pfolio"] >= 0.5 and kwargs["perc"]["decline"] >= 1:
        trailing_stop = True
    else:
        trailing_stop = False

    is_trailing = kwargs.get("trailing", False)
    if trailing_stop and not is_trailing:
        kwargs["trailing"] = {"reset_high": 0, "perc_decline": 0}
        kwargs["last"] = "trailing mode ON"
    elif not trailing_stop and is_trailing:
        kwargs.pop("trailing")
        kwargs["last"] = "trailing mode OFF"

    if trailing_stop:
        kwargs = _exit_by_trail(**kwargs)
    return kwargs


def adjust_buy_to_cover(**kwargs):
    kwargs["fn"] = pyramid
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
        kwargs["last"] = "adjust mode ON"
    return kwargs


kwargs = {}
kwargs = pyramid(**kwargs)
while kwargs.get("fn", "PACK_AND_GO") != "PACK_AND_GO":
    kwargs = _update_metrics(**kwargs)
    next_function = kwargs.pop("fn")
    kwargs = next_function(**kwargs)
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
    sleep(0.5)
