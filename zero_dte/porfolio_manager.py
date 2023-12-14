# add typing with future compatablity
import math
import re
from constants import logging


class PortfolioManager:
    def __init__(self, lst_of_positions, base):
        self.portfolio = lst_of_positions
        self.base = base

    def update(self, list_of_positions=[], sort_key="value"):
        if any(list_of_positions):
            self.portfolio = list_of_positions
        if sort_key in self.portfolio:
            self.portfolio.sort(key=lambda x: x[sort_key], reverse=True)
        self.portfolio = [
            {k: v for k, v in pos.items() if k != "reduced_qty"}
            for pos in self.portfolio
        ]
        return self.portfolio

    def close_positions(self):
        self.portfolio.sort(key=lambda x: x["last_price"], reverse=True)
        for entry in self.portfolio:
            if entry["quantity"] != 0:
                pos = dict(
                    symbol=entry["symbol"],
                    side="B" if entry["quantity"] < 0 else "S",
                    quantity=abs(entry["quantity"]),
                )
                yield pos

    def reduce_value(self, current_value, contains):
        self.portfolio.sort(key=lambda x: x["last_price"], reverse=True)
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
                logging.debug(f"{entry_lot=} vs {target_lot=} for {val_per_lot=}")
                calculated = entry_lot if target_lot > entry_lot else target_lot
                calculated = 1 if calculated == 0 else calculated
                val_for_this = calculated * val_per_lot
                current_value -= val_for_this
                logging.debug(f"{current_value=} after reducing {val_for_this}")
                pos["symbol"] = entry["symbol"]
                pos["quantity"] = calculated * self.base["LOT_SIZE"]
                pos["side"] = "B"
                logging.debug(f"value reduce order details {pos}")
                lst.append(pos)
        return current_value, lst  # Return the resulting current_value in negative


    def adjust_highest_ltp(self, requested_value, contains=""):
        contains = self.base["EXPIRY"] + contains
        self.portfolio.sort(key=lambda x: x["last_price"], reverse=True)
        for entry in self.portfolio:
            if entry["quantity"] < 0 and re.search(
                re.escape(contains), entry["symbol"]
            ):
                pos = {}
                entry_lot = abs(entry["quantity"]) / self.base["LOT_SIZE"]
                val_per_lot = abs(entry["value"]) / entry_lot
                target_lot = math.ceil(
                    requested_value / entry["last_price"] / self.base["LOT_SIZE"]
                )
                logging.debug(f"{entry_lot=} vs {target_lot=} for {val_per_lot=}")
                calculated = entry_lot if target_lot > entry_lot else target_lot
                calculated = 1 if calculated == 0 else calculated
                # adjust_qty
                pos["symbol"] = entry["symbol"]
                pos["quantity"] = calculated * self.base["LOT_SIZE"]
                pos["side"] = "B"
                val_for_this = calculated * val_per_lot
                logging.debug(f"initially {requested_value=} and finally {val_for_this=}")
                break
        return val_for_this, pos

    def close_profiting_position(self, contains):
        quantity = 0
        for pos in self.portfolio:
            if (
                re.search(re.escape(self.base["EXPIRY"] + contains), pos["symbol"])
                and pos["last_price"] < self.base["COVER_FOR_PROFIT"]
            ):
                quantity = pos["quantity"]
                break
        return quantity

    def is_above_highest_ltp(self, contains: str) -> bool:
        if any(
            re.search(re.escape(self.base["EXPIRY"] + contains), pos["symbol"])
            and pos["quantity"] < 0
            and pos["last_price"] > self.base["MAX_SOLD_LTP"]
            for pos in self.portfolio
        ):
            return True
        return False
    """
    def adjust_value(self, value_to_reduce, endswith=None):
        for entry in self.portfolio:
            symbol = entry["symbol"]
            opp_val = -1 * entry["value"]
            opp_qty = -1 * entry["quantity"]
            entry["reduction_qty"] = 0
            if (
                value_to_reduce > 0
                and (entry["value"] < 0 and value_to_reduce >= opp_val)
            ) and (endswith is None or symbol.endswith(endswith)):
                # sell to close
                value_to_reduce += entry["value"]
                entry["reduction_qty"] = opp_qty
                entry["quantity"] = 0
                entry["value"] = 0
            elif (
                value_to_reduce < 0
                and (entry["value"] > 0 and value_to_reduce <= opp_val)
            ) and (endswith is None or symbol.endswith(endswith)):
                # buy to cover
                value_to_reduce += entry["value"]
                entry["reduction_qty"] = opp_qty
                entry["quantity"] = 0
                entry["value"] = 0

            # Adjust m2m and rpl
            entry["rpl"] += entry["m2m"]
            entry["m2m"] = 0
            yield entry

            if value_to_reduce == 0:
                break

    """


if __name__ == "__main__":
    from constants import base

    # Example usage of the class with the updated adjust_positions method
    manager = PortfolioManager([], base)
