from omspy_brokers.finvasia import Finvasia
from constants import cnfg, common
from toolkit.printutils import prettier

brkr = Finvasia(**cnfg)
if not brkr.authenticate():
    SystemExit(1)
else:
    print("success")


def orders():
    ord = [{}]
    ord = brkr.orders
    if any(ord):
        for d in ord:
            if "remarks" not in d:
                d["remarks"] = 'no tag'
    keys = [
        "order_id",
        "broker_timestamp",
        "symbol",
        "side",
        "average_price",
        "status",
        "filled_quantity",
        "remarks"
    ]
    if any(ord):
        ord = [{k: d[k] for k in keys} for d in ord]
    return ord


def positions():
    positions = [{}]
    positions = brkr.positions
    keys = [
        "symbol",
        "quantity",
        "last_price",
        "urmtom",
        "rpnl",
    ]
    if any(positions):
        # filter by dict keys
        positions = [{key: dct[key] for key in keys} for dct in positions]
        # calc value
        for pos in positions:
            straddle = 100
            ltp = min(pos["last_price"], straddle)
            pos["value"] = int(pos["quantity"] * ltp)
        # remove positions that does not begin with symbol name
        positions = [
            pos for pos in positions if pos["symbol"].startswith(common['base'])]
    return positions


kwargs = {}
kwargs["orders"] = orders()
kwargs["positions"] = positions()
prettier(**kwargs)
