# add typing with future compatablity
import math


class PortfolioManager:
    def __init__(self, lst_of_positions=[]):
        self.portfolio = lst_of_positions

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

    def trailing_full(self, value_to_reduce, endswith, lotsize):
        self.portfolio.sort(key=lambda x: x["ltp"], reverse=True)

        for entry in self.portfolio:
            if (
                entry["qty"] < 0
                and value_to_reduce > 0
                and entry["symbol"].endswith(endswith)
            ):
                print(f"working on {entry['symbol']}")
                # negative entry lot
                entry_lot = entry["qty"] / lotsize
                # positive value per entry lot
                val_per_lot = entry["value"] / entry_lot
                # postive target lot
                target_lot = math.ceil(value_to_reduce / entry["ltp"] / lotsize)
                print(f"{entry_lot=} {target_lot=} {val_per_lot=}")

                calculated = (
                    target_lot if target_lot <= abs(entry_lot) and target_lot > 0 else 1
                )

                print(f"{calculated=} lot")

                entry["reduced_qty"] = calculated * lotsize
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

    def adjust_quantity(self, total_quantity, endswith=None):
        for entry in self.portfolio:
            symbol = entry["symbol"]
            if (
                (entry["qty"] > 0 and total_quantity < 0)
                or (entry["qty"] < 0 and total_quantity > 0)
            ) and (endswith is None or symbol.endswith(endswith)):
                available_quantity = abs(entry["qty"])
                if total_quantity > 0:  # buying to cover
                    action_quantity = min(total_quantity, available_quantity)
                    entry["qty"] += action_quantity  # Buy
                    total_quantity -= action_quantity
                else:  # selling to close
                    action_quantity = min(abs(total_quantity), available_quantity)
                    entry["qty"] -= action_quantity  # Sell
                    total_quantity -= action_quantity
                entry["reduction_qty"] = action_quantity

                # Calculate the ratio
                ratio = action_quantity / available_quantity

                # Adjust m2m and rpl
                m2m_adjustment = entry["m2m"] * ratio
                entry["m2m"] -= m2m_adjustment
                entry["rpl"] += m2m_adjustment
                yield entry

                if total_quantity == 0:
                    break


if __name__ == "__main__":
    from pprint import pprint

    # Example usage of the class with the updated adjust_positions method
    manager = PortfolioManager()
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
    for entry in manager.adjust_value(total_to_adjust, endswith="CE"):
        print(entry)
