# add typing with future compatablity
from __future__ import annotations
import math
import re
from constants import logging


class PortfolioManager:
    def __init__(self, lst_of_positions: list[dict], base: dict):
        self.portfolio = lst_of_positions
        self.base = base

    def update(self, list_of_positions: list[dict]):
        if any(list_of_positions):
            if "value" in list_of_positions:
                list_of_positions.sort(key=lambda x: x["value"], reverse=True)
        self.portfolio = list_of_positions
        return self.portfolio

    def close_positions(self):
        self.portfolio.sort(key=lambda x: x["value"], reverse=True)
        for entry in self.portfolio:
            if entry["quantity"] != 0:
                pos = dict(
                    symbol=entry["symbol"],
                    side="B" if entry["quantity"] < 0 else "S",
                    quantity=abs(entry["quantity"]),
                )
                yield pos

    def reduce_value(self, current_value: int, contains="P" or "C"):
        self.portfolio.sort(key=lambda x: x["last_price"], reverse=False)
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

    def adjust_highest_ltp(self, requested_value=int, contains="P" or "C"):
        contains = self.base["EXPIRY"] + contains
        self.portfolio.sort(key=lambda x: x["last_price"], reverse=False)
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

    def close_profiting_position(self, contains="P" or "C") -> int:
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

    def is_above_highest_ltp(self, contains="P" or "C") -> bool:
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
    manager = PortfolioManager([], base)
