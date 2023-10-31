# Initialize a list of dictionaries to represent the table-like structure
portfolio = [
    {"symbol": "NIFTY25APR17500CE", "quantity": -50},
    {"symbol": "NIFTY25APR17550CE", "quantity": -500},
    {"symbol": "NIFTY25APR17600PE", "quantity": 20},
    # Add more symbols and quantities as needed
]


# Function to print the portfolio
def print_portfolio(title, portfolio):
    print(title)
    for entry in portfolio:
        print(f"{entry['symbol']}: {entry['quantity']}Q")
    print()


# Generator function to yield symbols and quantities for reduction
def reduce_positions(total_quantity):
    print_portfolio("Portfolio Before Reduction:", portfolio)

    remaining_quantity = total_quantity
    for entry in portfolio:
        if entry["quantity"] < 0:  # Handle only sold quantities
            symbol = entry["symbol"]
            sold_quantity = abs(entry["quantity"])  # Absolute value of sold quantity
            setoff_quantity = min(
                sold_quantity, remaining_quantity
            )  # Calculate setoff quantity
            entry["quantity"] += setoff_quantity  # Set off the corresponding entry
            remaining_quantity -= setoff_quantity
            if remaining_quantity <= 0:
                break  # Exit if the total quantity is reduced
            yield symbol, setoff_quantity

    print_portfolio("Portfolio After Reduction:", portfolio)


# Example usage of the generator
total_to_reduce = 150  # Total quantity to reduce
for symbol, setoff_quantity in reduce_positions(total_to_reduce):
    print(f"Reducing {setoff_quantity}Q for {symbol}")
    # Place the opposite order and close the corresponding hedge here
