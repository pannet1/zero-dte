import re
from typing import Literal, Dict, Tuple


def get_val_and_pos(
    entry, target_value, base_lot_size, tag
):
    # find the lot size of the position
    entry_lot = abs(entry["quantity"]) / base_lot_size
    # find the value of each position lot
    val_per_entry_lot = abs(entry["value"]) / base_lot_size
    # find the target lot to be covered for the target value
    target_lot = round(target_value / val_per_entry_lot)
    # if the target lot is 0 make it 1
    target_min_one_lot = 1 if target_lot <= 0 else target_lot
    # ensure that the target is not more than the actual position we have
    target_final_lot = entry_lot if target_min_one_lot > entry_lot else target_min_one_lot
    # how much value we will reduce if we square
    val_for_this = target_final_lot * base_lot_size * entry["last_price"]
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

    # TODO fix Any is not subscriptable
    def close_positions(self):
        for entry in self.portfolio:
            if entry["quantity"] != 0:
                pos = dict(
                    symbol=entry["symbol"],
                    side="B" if entry["quantity"] < 0 else "S",
                    quantity=min(abs(entry["quantity"]), self.base["MAX_QTY"]),
                )
                yield pos

    def is_above_highest_ltp(self, contains: Literal["C", "P"]) -> bool:
        if any(
            re.search(re.escape(self.base["EXPIRY"] + contains), pos["symbol"])
            and pos["quantity"] < 0
            and pos["last_price"] > self.base["MAX_SOLD_LTP"]
            for pos in self.portfolio
        ):
            return True
        return False

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
                return val_for_this, pos
        return 0, {}

    def close_profiting_position(self, target_value: int,
                                 tag: str) -> Tuple[int, Dict]:
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
                return val_for_this, pos
        return 0, {}


if __name__ == "__main__":
    from constants import base
    from time import sleep
    from toolkit.printutils import prettier

    # Example usage of the class with the updated adjust_positions method
    pm = PortfolioManager(base)

# Sample data
    sample_data = [
        {"symbol": "BANKNIFTY10JAN24C24500", "quantity": 50,
            "last_price": 333.12, "value": -2000},
        {"symbol": "BANKNIFTY10JAN24P25500", "quantity": -
            500, "last_price": 300, "value": -150000},
        {"symbol": "BANKNIFTY10JAN24C26600", "quantity": 500,
            "last_price": 111.01, "value": 1800},
        {"symbol": "BANKNIFTY10JAN24P27000", "quantity": 500,
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
    value_to_reduce = 100
    option_type = "P"
    tag = "test"
    print(f"{value_to_reduce = } in {option_type = } {tag} \n")
    excess_value, pos = pm.reduce_value(value_to_reduce, option_type, tag)
    sleep(2)
    print(f"{excess_value = } in {pos} \n")
