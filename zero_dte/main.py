from constants import brkr, logging

if not brkr.authenticate():
    logging.error("failed to authenticate")
    SystemExit(1)

posn = brkr.positions
if any(posn):
    print(posn)
