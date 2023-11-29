# add typing with future compatablity
import math


class PortfolioManager:
    def __init__(self, lst_of_positions, lotsize, highest_ltp):
        self.portfolio = lst_of_positions
        self.lotsize = lotsize
        self.highest_ltp = highest_ltp

    def update(self, list_of_positions=[], sort_key="value"):
        if any(list_of_positions):
            self.portfolio = list_of_positions
        self.portfolio.sort(key=lambda x: x[sort_key], reverse=True)
        self.portfolio = [
            {k: v for k, v in pos.items() if k != "reduced_qty"}
            for pos in self.portfolio
        ]
        return self.portfolio

    def add_position(self, position_dict):
        is_append = True
        for entry in self.portfolio:
            if entry["symbol"] == position_dict["symbol"]:
                entry["qty"] += position_dict["qty"]
                entry["m2m"] += position_dict["m2m"]
                entry["rpl"] += position_dict["rpl"]
                entry["ltp"] = position_dict["ltp"]
                entry["value"] = position_dict["value"]
                is_append = False
                break
        if is_append:
            self.portfolio.append(position_dict)

    def replace_position(self, position_dict):
        symbol = position_dict["symbol"]
        for entry in self.portfolio:
            if entry["symbol"] == symbol:
                entry = position_dict

    def close_positions(self):
        self.portfolio.sort(key=lambda x: x["ltp"], reverse=True)

        for entry in self.portfolio:
            if entry["qty"] != 0:
                entry["rpl"] += entry["m2m"]
                entry["m2m"] = 0
                entry["reduced_qty"] = -1 * entry["qty"]
                entry["qty"] = 0
                yield entry

    def reduce_value(self, value_to_reduce, endswith):
        self.portfolio.sort(key=lambda x: x["ltp"], reverse=True)

        for entry in self.portfolio:
            if (
                entry["qty"] < 0
                and value_to_reduce > 0
                and entry["symbol"].endswith(endswith)
            ):
                print(f"working on {entry['symbol']}")
                # negative entry lot
                entry_lot = entry["qty"] / self.lotsize
                # positive value per entry lot
                val_per_lot = abs(entry["value"] / entry_lot)
                # postive target lot
                target_lot = math.ceil(value_to_reduce / entry["ltp"] / self.lotsize)
                print(f"{entry_lot=} {target_lot=} {val_per_lot=}")
                calculated = (
                    abs(entry_lot) if target_lot > abs(entry_lot) else target_lot
                )
                calculated = 1 if calculated == 0 else calculated
                print(f"{calculated=} lot")

                entry["reduced_qty"] = calculated * self.lotsize
                entry["qty"] += entry["reduced_qty"]

                # neutral m2m
                m2m_per_lot = entry["m2m"] / abs(entry_lot)
                m2m_for_this = m2m_per_lot * calculated
                print(f"{m2m_for_this=} {m2m_per_lot=} * {calculated}")

                entry["m2m"] -= m2m_for_this
                entry["rpl"] += m2m_for_this

                val_for_this = calculated * val_per_lot
                entry["value"] += val_for_this
                value_to_reduce -= val_for_this

                print(f"final {value_to_reduce=}")
        return value_to_reduce  # Return the resulting value_to_reduce in negative

    def is_above_highest_ltp(self, endswith: str) -> bool:
        if any(
            pos["symbol"].endswith(endswith)
            and pos["qty"] < 0
            and pos["ltp"] > self.highest_ltp
            for pos in self.portfolio
        ):
            return True
        return False

    def adjust_highest_ltp(self, adjust_amount, endswith=None):
        self.portfolio.sort(key=lambda x: x["ltp"], reverse=True)
        adjusted = {"reduction_qty": 0}
        for entry in self.portfolio:
            if entry["qty"] < 0 and entry["symbol"].endswith(endswith):
                # negative entry lot
                entry_lot = entry["qty"] / self.lotsize
                # positive value per entry lot
                val_per_lot = abs(adjust_amount / entry_lot)
                # postive target lot
                target_lot = math.ceil(adjust_amount / entry["ltp"] / self.lotsize)
                target_lot = 1 if target_lot == 0 else target_lot
                # adjust_qty
                action_quantity = target_lot * self.lotsize
                entry["qty"] += action_quantity  # buy
                # Adjust m2m and rpl
                m2m_adjustment = val_per_lot * target_lot
                entry["m2m"] -= m2m_adjustment
                entry["rpl"] += m2m_adjustment
                adjusted["reduction_qty"] = action_quantity
                adjusted.update(entry)
                break

        return adjusted

    def find_closest_premium(self, quotes, premium, endswith):
        closest_symbol = None
        closest_difference = float("inf")

        for symbol, ltp in quotes.items():
            if symbol.endswith(endswith):
                difference = abs(ltp - premium)
                if difference < closest_difference:
                    closest_difference = difference
                    closest_symbol = symbol

        return closest_symbol

    """
    def adjust_value(self, value_to_reduce, endswith=None):
        for entry in self.portfolio:
            symbol = entry["symbol"]
            opp_val = -1 * entry["value"]
            opp_qty = -1 * entry["qty"]
            entry["reduction_qty"] = 0
            if (
                value_to_reduce > 0
                and (entry["value"] < 0 and value_to_reduce >= opp_val)
            ) and (endswith is None or symbol.endswith(endswith)):
                # sell to close
                value_to_reduce += entry["value"]
                entry["reduction_qty"] = opp_qty
                entry["qty"] = 0
                entry["value"] = 0
            elif (
                value_to_reduce < 0
                and (entry["value"] > 0 and value_to_reduce <= opp_val)
            ) and (endswith is None or symbol.endswith(endswith)):
                # buy to cover
                value_to_reduce += entry["value"]
                entry["reduction_qty"] = opp_qty
                entry["qty"] = 0
                entry["value"] = 0

            # Adjust m2m and rpl
            entry["rpl"] += entry["m2m"]
            entry["m2m"] = 0
            yield entry

            if value_to_reduce == 0:
                break

    """


if __name__ == "__main__":
    from pprint import pprint

    # Example usage of the class with the updated adjust_positions method
    manager = PortfolioManager([], 50, 70)
    manager.add_position(
        {"symbol": "NIFTY25APR17550CE", "qty": -50, "value": -500, "m2m": 20, "rpl": 20}
    )
    manager.add_position(
        {"symbol": "NIFTY25APR17750CE", "qty": 0, "value": 0, "m2m": 20, "rpl": 20}
    )
    manager.add_position(
        {
            "symbol": "NIFTY25APR17650CE",
            "qty": -200,
            "value": -100,
            "m2m": 20,
            "rpl": 20,
        }
    )
    pprint(manager.portfolio)
    # Positive total_to_adjust (buying)
    total_to_adjust = 650
    print(f"{total_to_adjust=}")
    for entry in manager.trailing_full(total_to_adjust, endswith="CE"):
        print(entry)
