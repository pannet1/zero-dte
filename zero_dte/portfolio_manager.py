import math
import re
from constants import logging
from typing import Literal


class PortfolioManager:
    def __init__(self, lst_of_positions: list[dict], base: dict):
        self.portfolio = lst_of_positions
        self.base = base

    def update(self, list_of_positions: list[dict]):
        self.portfolio = list_of_positions
        return self.portfolio

    def close_positions(self):
        self._sort("value")
        for entry in self.portfolio:
            if entry["quantity"] != 0:
                pos = dict(
                    symbol=entry["symbol"],
                    side="B" if entry["quantity"] < 0 else "S",
                    quantity=abs(entry["quantity"]),
                )
                yield pos

    def reduce_value(self, current_value: int, contains: Literal["C", "P"]):
        self._sort("value")
        lst = [{}]
        for entry in self.portfolio:
            if (
                entry["quantity"] < 0
                and current_value > 0
                and re.search(
                    re.escape(self.base["EXPIRY"] + contains), entry["symbol"]
                )
            ):
                logging.debug(f"{current_value} before reducing")
                pos = {}
                entry_lot = abs(entry["quantity"]) / self.base["LOT_SIZE"]
                val_per_lot = abs(entry["value"]) / entry_lot
                target_lot = math.ceil(
                    current_value / entry["last_price"] / self.base["LOT_SIZE"]
                )
                logging.debug(
                    f"{entry_lot=} vs {target_lot=} for {val_per_lot=}")
                target_lot = 1 if target_lot == 0 else target_lot
                calculated = entry_lot if target_lot > entry_lot else target_lot
                val_for_this = calculated * val_per_lot
                current_value -= val_for_this
                logging.debug(
                    f"{current_value=} after reducing {val_for_this}")
                pos["symbol"] = entry["symbol"]
                pos["quantity"] = calculated * self.base["LOT_SIZE"]
                pos["side"] = "B"
                logging.debug(f"value reduce order details {pos}")
                lst.append(pos)
        return current_value, lst  # Return the resulting current_value in negative

    def _sort(self, sort_key, is_desc=False):
        if any(self.portfolio):
            if sort_key in self.portfolio[0]:
                self.portfolio.sort(
                    key=lambda x: x[sort_key], reverse=is_desc)

    def adjust_highest_ltp(self, requested_value: int, contains: Literal["C", "P"]):
        self._sort("last_price", False)
        contains = self.base["EXPIRY"] + contains
        pos = {}
        val_for_this = 0
        for entry in self.portfolio:
            if entry["quantity"] < 0 and re.search(
                re.escape(contains), entry["symbol"]
            ):
                entry_lot = abs(entry["quantity"]) / self.base["LOT_SIZE"]
                val_per_lot = abs(entry["value"]) / entry_lot
                target_lot = math.ceil(
                    requested_value /
                    entry["last_price"] / self.base["LOT_SIZE"]
                )
                logging.debug(
                    f"{entry_lot=} vs {target_lot=} for {val_per_lot=}")
                calculated = entry_lot if target_lot > entry_lot else target_lot
                calculated = 1 if calculated == 0 else calculated
                # adjust_qty
                pos["symbol"] = entry["symbol"]
                pos["quantity"] = calculated * self.base["LOT_SIZE"]
                pos["side"] = "B"
                val_for_this = calculated * val_per_lot
                logging.debug(
                    f"initially {requested_value=} and finally {val_for_this=}")
                break
        return val_for_this, pos

    def close_profiting_position(self, contains: Literal["C", "P"]) -> int:
        self._sort("value")
        quantity = 0
        for pos in self.portfolio:
            if (
                re.search(
                    re.escape(self.base["EXPIRY"] + contains), pos["symbol"])
                and pos["last_price"] < self.base["COVER_FOR_PROFIT"]
            ):
                quantity = pos["quantity"]
                break
        return quantity

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
    # Example usage of the class with the updated adjust_positions method
    portfolio_manager = PortfolioManager([], base)

# Sample data
    sample_data = [
        {"symbol": "AAPL", "value": -2000},
        {"symbol": "GOOGL", "value": 1500},
        {"symbol": "MSFT", "value": 1800},
        {"symbol": "AMZN", "value": 2500},
    ]

# Call the update method with the sample data
    sorted_portfolio = portfolio_manager.update(sample_data)

# Display the sorted portfolio
    print(sorted_portfolio)