def calc_m2m(pos):
    if pos["quantity"] > 0:
        sold = int(pos["quantity"]) * int(pos["last_price"])
        return sold - pos["bought"]
    elif pos["quantity"] < 0:
        return pos["sold"] - (abs(pos["quantity"]) * pos["last_price"])
    elif pos["quantity"] == 0:
        return 0
