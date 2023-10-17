from mcx import Mcx
from constants import brkr, smcx, snse, logging
import pendulum as pdlm

if not brkr.authenticate():
    logging.error("failed to authenticate")
    SystemExit(1)

Mcx.brkr = brkr
while True:
    if (
        (pdlm.now().time() > pdlm.time(23, 25))
        or (Mcx.get_mcx_m2m() < smcx['STOP'])
    ):
        Mcx.pack_and_go()
    else:
        print(f"time: {pdlm.now().time()} squareoff: {pdlm.time(23,25)}")
