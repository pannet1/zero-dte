import re
from utilities.list_of_dict import sort
from constants import base


class PortfolioManager:

    def update(self, list_of_positions: list[dict]):
        self.portfolio = sort(list_of_positions, "value")
        return self.portfolio

    # TODO fix Any is not subscriptable
    def close_positions(self):
        for entry in self.portfolio:
            if (
                entry["quantity"] != 0 and
                re.search(
                    re.escape(base["EXPIRY"]), entry["symbol"])
            ):
                pos = dict(
                    symbol=entry["symbol"],
                    side="B" if entry["quantity"] < 0 else "S",
                    quantity=min(abs(entry["quantity"]), base["MAX_QTY"]),
                )
                yield pos


if __name__ == "__main__":
    from utilities.printutils import prettier

    # Example usage of the class with the updated adjust_positions method
    pm = PortfolioManager()

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
    print(f"{excess_value = } in {pos} \n")
