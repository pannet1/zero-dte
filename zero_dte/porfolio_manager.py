# add typing with future compatablity
import math
import re


class PortfolioManager:
    def __init__(self, lst_of_positions, snse):
        self.portfolio = lst_of_positions
        self.snse = snse

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

    def reduce_value(self, value_to_reduce, contains):
        self.portfolio.sort(key=lambda x: x["last_price"], reverse=True)
        lst = [{}]
        for entry in self.portfolio:
            if (
                entry["quantity"] < 0
                and value_to_reduce > 0
                and re.search(
                    re.escape(self.snse["EXPIRY"] + contains), entry["symbol"]
                )
            ):
                print(f"working on {entry['symbol']}")
                pos = {}
                # negative entry lot
                entry_lot = entry["quantity"] / self.snse["LOT_SIZE"]
                # positive value per entry lot
                val_per_lot = abs(entry["value"] / entry_lot)
                # postive target lot
                target_lot = math.ceil(
                    value_to_reduce / entry["last_price"] / self.snse["LOT_SIZE"]
                )
                print(f"{entry_lot=} {target_lot=} {val_per_lot=}")

                calculated = (
                    abs(entry_lot) if target_lot > abs(entry_lot) else target_lot
                )
                calculated = 1 if calculated == 0 else calculated
                print(f"{calculated=} lot")

                val_for_this = calculated * val_per_lot
                value_to_reduce -= val_for_this
                print(f"final {value_to_reduce=}")

                pos["symbol"] = entry["symbol"]
                pos["quantity"] = calculated * self.snse["LOT_SIZE"]
                pos["side"] = "B"
                lst.append(pos)
        return value_to_reduce, lst  # Return the resulting value_to_reduce in negative

    def is_above_highest_ltp(self, contains: str) -> bool:
        if any(
            re.search(re.escape(self.snse["EXPIRY"] + contains), pos["symbol"])
            and pos["quantity"] < 0
            and pos["last_price"] > self.snse["MAX_SOLD_last_price"]
            for pos in self.portfolio
        ):
            return True
        return False

    def adjust_highest_last_price(self, adjust_amount, contains=""):
        contains = self.snse["EXPIRY"] + contains
        self.portfolio.sort(key=lambda x: x["last_price"], reverse=True)
        adjusted = {}
        for entry in self.portfolio:
            if entry["quantity"] < 0 and re.search(
                re.escape(contains), entry["symbol"]
            ):
                # negative entry lot
                target_lot = math.ceil(
                    adjust_amount / entry["last_price"] / self.snse["LOT_SIZE"]
                )
                target_lot = 1 if target_lot == 0 else target_lot
                # adjust_qty
                adjusted["symbol"] = entry["symbol"]
                adjusted["quantity"] = target_lot * self.snse["LOT_SIZE"]
                adjusted["side"] = "B"
                break
        return adjusted

    def close_profiting_position(self, contains):
        quantity = 0
        for pos in self.portfolio:
            if (
                re.search(re.escape(self.snse["EXPIRY"] + contains), pos["symbol"])
                and pos["last_price"] < self.snse["COVER_FOR_PROFIT"]
            ):
                quantity = pos["quantity"]
                break
        return quantity

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
