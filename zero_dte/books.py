from omspy_brokers.finvasia import Finvasia
from constants import snse, logging, common, cnfg
from print import prettier

brkr = Finvasia(**cnfg)
if not brkr.authenticate():
    SystemExit(1)
else:
    print("success")


def orders():
    pos = brkr.orders
    keys = [
        "order_id",
        "symbol",
        "side",
        "average_price",
        "status",
        "filled_quantity",
    ]
    pos = [{k: d[k] for k in keys} for d in pos]
    return pos


def positions():
    pos = brkr.positions
    keys = [
        "symbol",
        "quantity",
        "last_price",
        "urmtom",
        "rpnl",
    ]
    pos = [{k: d[k] for k in keys} for d in pos]
    return pos[0]


kwargs = {}
kwargs["orders"] = orders()
kwargs["positions"] = positions()
prettier(**kwargs)
