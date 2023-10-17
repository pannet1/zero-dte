from mcx import Mcx
from constants import brkr, smcx, logging
import pendulum as pdlm

if not brkr.authenticate():
    logging.error("failed to authenticate")
    SystemExit(1)

Mcx.brkr = brkr
squareoff = pdlm.parse(smcx['SQUAREOFF'], fmt="HH:mm").time()

while True:
    if (
        (pdlm.now().time() > squareoff)
        or (Mcx.get_mcx_m2m() < smcx['STOP'])
    ):
        Mcx.pack_and_go()
    else:
        print(
            f"time: {pdlm.now().format('HH:mm:ss')} squareoff: {squareoff} ")

