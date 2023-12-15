from omspy_brokers.finvasia import Finvasia
from constants import cnfg
from print import prettier

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
    pos = [{}]
    pos = brkr.positions
    keys = [
        "symbol",
        "quantity",
        "last_price",
        "urmtom",
        "rpnl",
    ]
    if any(pos):
        pos = [{k: d[k] for k in keys} for d in pos]
    return pos[0]


kwargs = {}
kwargs["orders"] = orders()
kwargs["positions"] = positions()
prettier(**kwargs)
