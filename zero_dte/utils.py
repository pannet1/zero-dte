def calc_m2m(pos):
    if pos["qty"] > 0:
        return (pos["qty"] * pos["ltp"]) - pos["bought"]
    elif pos["qty"] < 0:
        return pos["sold"] - (abs(pos["qty"]) * pos["ltp"])
