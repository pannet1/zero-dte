def calc_m2m(pos):
    if pos["quantity"] > 0:
        return (pos["quantity"] * pos["ltp"]) - pos["bought"]
    elif pos["quantity"] < 0:
        return pos["sold"] - (abs(pos["quantity"]) * pos["ltp"])
