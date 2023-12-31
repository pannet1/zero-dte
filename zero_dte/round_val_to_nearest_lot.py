def round_val_to_qty(
    val: int, ltp: float, base_lot: int = 15
):
    qty = val / ltp
    print(f"{qty=}")
    lot = round(qty / base_lot)
    lot = 1 if lot == 0 else lot
    print(f"{lot=}")
    qty = lot * base_lot
    print(f"{qty=}")
    return qty


round_val_to_qty(
    1,
    1
)
