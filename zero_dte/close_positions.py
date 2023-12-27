
from omspy_brokers.finvasia import Finvasia
from constants import base, logging, common, cnfg
from symbols import Symbols
import sys
from portfolio_manager import PortfolioManager

slp = 2
SYMBOL = common["base"]

obj_sym = Symbols(base['EXCHANGE'], SYMBOL, base["EXPIRY"])
obj_sym.get_exchange_token_map_finvasia()
pm = PortfolioManager(base)


def _positions():
    positions = [{}]
    positions = brkr.positions
    if any(positions):
        # calc value
        # remove positions that does not begin with symbol name
        positions = [pos for pos in positions if pos["symbol"].startswith(
            SYMBOL)]
    _ = pm.update(positions)
    return positions


def opposite_order(**args):
    print(args)
    if args["quantity"] != 0:
        args["order_type"] = "MKT"
        args['side'] = "B" if args["quantity"] < 0 else "S"
        quantity = abs(args.pop('quantity'))
        args["quantity"] = quantity
        args["exchange"] = base['EXCHANGE']
        args["disclosed_quantity"] = quantity
        # brkr.order_place(**args)


def get_brkr_and_wserver():
    if common["live"]:
        brkr = Finvasia(**cnfg)
        if not brkr.authenticate():
            logging.error("Failed to authenticate")
            sys.exit(0)
    else:
        print("you are in paper trading")
        sys.exit(0)
    return brkr


brkr = get_brkr_and_wserver()
_ = pm.update(_positions())
for pos in pm.close_positions():
    if any(pos):
        pos.update({"tag": "standalone close_positions"})
        opposite_order(**pos)
else:
    print("you go no positions to square")
