def sort(positions, sort_key, is_desc=False):
    if any(positions):
        if sort_key in positions[0]:
            positions.sort(
                key=lambda x: x[sort_key], reverse=is_desc)
    return positions


def get_val_and_pos(
    entry: dict, target_value: float, base_lot_size: int, tag: str
):
    # find the lot size of the position
    entry_lot = abs(entry["quantity"]) / base_lot_size
    # find the value of each position lot
    val_per_entry_lot = abs(entry["value"]) / entry_lot
    # find the target lot to be covered for the target value
    target_lot = int(target_value / val_per_entry_lot) / val_per_entry_lot
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


if __name__ == "__main__":

    # Sample data
    sample_data = [
        {"symbol": "BANKNIFTY10JAN24C24500", "quantity": 30,
            "last_price": 61, "value": -1830},
        {"symbol": "BANKNIFTY10JAN24P25500", "quantity": -
            500, "last_price": 300, "value": -150000},
        {"symbol": "BANKNIFTY10JAN24C26600", "quantity": 500,
            "last_price": 111.01, "value": 1800},
        {"symbol": "BANKNIFTY10JAN24P27000", "quantity": 500,
            "last_price": 111.03, "value": -5000},
    ]

    val, pos = get_val_and_pos(sample_data[0], 500, 15, "test")
    print(f'{val = }, "\n", {pos = }')
