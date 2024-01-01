import math
import re

from constants import logging
from typing import Literal, Dict


def target_lot_fm_value(
    target_val: int,
    entry_last_price: float,
    base_lot: int = 15
):
    # find target quantity
    target_qty = target_val / entry_last_price       # round qty to the nearest lot
    target_lot = round(target_qty / base_lot)
    return target_lot


def get_val_and_pos(
    entry, target_value, base_lot_size, tag
):
    # find the lot size of the position
    entry_lot = abs(entry["quantity"]) / base_lot_size
    # find the value of each position lot
    val_per_entry_lot = abs(entry["value"]) / entry_lot
    # find the target lot to be covered for the target value
    target_lot = target_lot_fm_value(
        target_value, entry["last_price"], base_lot_size
    )
    # if the target lot is 0 make it 1
    target_min_one_lot = 1 if target_lot == 0 else target_lot
    # ensure that the target is not more than the actual position we have
    target_final_lot = entry_lot if target_min_one_lot > entry_lot else target_min_one_lot
    # how much value we will reduce if we square
    val_for_this = target_final_lot * val_per_entry_lot
    # reduced that much value from the initial target
    # add the covering trade details to the empty pos dictionary
    pos = {}
    pos["symbol"] = entry["symbol"]
    pos["quantity"] = target_final_lot * base_lot_size
    pos["side"] = "B"
    pos["tag"] = tag
    return val_for_this, pos


class PortfolioManager:
    def __init__(self, base: dict):
        self.base = base

    def _sort(self, sort_key, is_desc=False):
        if any(self.portfolio):
            if sort_key in self.portfolio[0]:
                self.portfolio.sort(
                    key=lambda x: x[sort_key], reverse=is_desc)

    def update(self, list_of_positions: list[dict]):
        self.portfolio = list_of_positions
        self._sort("value")
        return self.portfolio

    def close_positions(self):
        for entry in self.portfolio:
            if entry["quantity"] != 0:
                pos = dict(
                    symbol=entry["symbol"],
                    side="B" if entry["quantity"] < 0 else "S",
                    quantity=abs(entry["quantity"]),
                )
                yield pos

    def reduce_value(self, target_value: int,
                     contains: Literal["C", "P"], tag):
        # arrange the positions starting from highest ltp
        self._sort("last_price", is_desc=True)
        # initial an empty list
        lst = []
        # process the position list one at a time
        for entry in self.portfolio:
            if (
                # is the position sell and target value is positive
                entry["quantity"] < 0 and target_value > 0
                # is the position our trading symbol
                and re.search(
                    re.escape(self.base["EXPIRY"] + contains), entry["symbol"]
                )
            ):
                val_for_this, pos = get_val_and_pos(
                    entry, target_value, self.base['LOT_SIZE'], tag
                )
                # reduced that much value from the initial target
                target_value -= val_for_this
                # add to the main list
                lst.append(pos)
        return target_value, lst  # Return the resulting target_value in negative

    def adjust_highest_ltp(self, target_value: int,
                           contains: Literal["C", "P"], tag: str
                           ):
        self._sort("last_price", True)
        contains = self.base["EXPIRY"] + contains
        for entry in self.portfolio:
            if entry["quantity"] < 0 and re.search(
                re.escape(contains), entry["symbol"]
            ):
                val_for_this, pos = get_val_and_pos(
                    entry, target_value, self.base['LOT_SIZE'], tag
                )
                val_for_this = target_value - val_for_this
                return val_for_this, pos
        return 0, {}

    def close_profiting_position(self, target_value: int, tag: str):
        for entry in self.portfolio:
            if (
                entry["quantity"] < 0 and
                re.search(
                    re.escape(self.base["EXPIRY"]), entry["symbol"])
                and entry["last_price"] < self.base["COVER_FOR_PROFIT"]
            ):
                val_for_this, pos = get_val_and_pos(
                    entry, target_value, self.base['LOT_SIZE'], tag
                )
                val_for_this = target_value - val_for_this
                return val_for_this, pos
        return 0, {}

    def is_above_highest_ltp(self, contains: Literal["C", "P"]) -> bool:
        if any(
            re.search(re.escape(self.base["EXPIRY"] + contains), pos["symbol"])
            and pos["quantity"] < 0
            and pos["last_price"] > self.base["MAX_SOLD_LTP"]
            for pos in self.portfolio
        ):
            return True
        return False


if __name__ == "__main__":
    from constants import base
    from time import sleep
    from print import prettier

    # Example usage of the class with the updated adjust_positions method
    pm = PortfolioManager(base)

# Sample data
    sample_data = [
        {"symbol": "BANKNIFTY28DEC23C24500", "quantity": 50,
            "last_price": 333.12, "value": -2000},
        {"symbol": "BANKNIFTY28DEC23P25500", "quantity": -
            500, "last_price": 300, "value": -500},
        {"symbol": "BANKNIFTY28DEC23C26600", "quantity": 500,
            "last_price": 111.01, "value": 1800},
        {"symbol": "BANKNIFTY28DEC23P27000", "quantity": 500,
            "last_price": 111.03, "value": -5000},
    ]

    # Call the update method with the sample data
    pm.update(sample_data)

    # Display the sorted portfolio
    pf = {
        "last": "before adjusting",
        "pm": pm.portfolio,
    }
    prettier(**pf)
    val, pos = pm.reduce_value(498, 'P', "test")
    sleep(2)
    print(val, pos)
