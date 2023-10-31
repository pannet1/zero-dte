class PortfolioManager:
    def __init__(self, lst_of_positions=[]):
        self.portfolio = lst_of_positions

    def add_position(self, position_dict):
        symbol = position_dict["symbol"]
        quantity = position_dict["qty"]

        for entry in self.portfolio:
            if entry["symbol"] == symbol:
                entry["qty"] += quantity
                break
        else:
            self.portfolio.append(position_dict)

    def adjust_positions(self, total_quantity, endswith=None):
        for entry in self.portfolio:
            symbol = entry["symbol"]
            if (
                (entry["qty"] > 0 and total_quantity < 0)
                or (entry["qty"] < 0 and total_quantity > 0)
            ) and (endswith is None or symbol.endswith(endswith)):
                available_quantity = abs(entry["qty"])
                if total_quantity > 0:  # Buying
                    action_quantity = min(total_quantity, available_quantity)
                    entry["qty"] += action_quantity  # Buy
                    entry["reduction_qty"] = action_quantity
                else:  # Selling
                    action_quantity = min(abs(total_quantity), available_quantity)
                    entry["qty"] -= action_quantity  # Sell
                    total_quantity -= action_quantity
                    entry["reduction_qty"] = action_quantity
                yield entry

                if total_quantity == 0:
                    break


if __name__ == "__main__":
    # Example usage of the class with the updated adjust_positions method
    manager = PortfolioManager()
    manager.add_position({"symbol": "NIFTY25APR17550CE", "qty": 50})
    manager.add_position({"symbol": "NIFTY25APR17550CE", "qty": -500})
    manager.add_position({"symbol": "NIFTY25APR17600PE", "qty": 20})

    # Positive total_to_adjust (buying)
    total_to_adjust = 150
    for entry in manager.adjust_positions(total_to_adjust, endswith="CE"):
        print(f"{entry['action_quantity']}Q {entry['symbol']} bought")

    # Negative total_to_adjust (selling)
    total_to_adjust = -100
    for entry in manager.adjust_positions(total_to_adjust, endswith="PE"):
        print(f"{entry['action_quantity']}Q {entry['symbol']} sold")
