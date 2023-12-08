def adjust(threshold, pfolio, symbolendswith):
    if (pfolio > threshold and symbolendswith == "CE") or (
        pfolio < threshold and symbolendswith == "PE"
    ):
        print("condiiton is True")

    else:
        print("condition is False")


if __name__ == "__main__":
    td = -0.7
    pf = 0.8
    endswith = "CE"
    adjust(td, pf, endswith)
