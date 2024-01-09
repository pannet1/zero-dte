
def sort(positions, sort_key, is_desc=False):
    if any(positions):
        if sort_key in positions[0]:
            positions.sort(
                key=lambda x: x[sort_key], reverse=is_desc)
    return positions


def get_val_and_pos(
    entry, target_value, base_lot_size, tag
):
    # find the lot size of the position
    entry_lot = abs(entry["quantity"]) / base_lot_size
    # find the value of each position lot
    val_per_entry_lot = abs(entry["value"]) / base_lot_size
    # find the target lot to be covered for the target value
    target_lot = round(target_value / val_per_entry_lot)
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
