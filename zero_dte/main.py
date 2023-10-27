from stratergy.mcx import Mcx
from omspy_brokers.finvasia import Finvasia
from constants import smcx, snse, cnfg, logging
import pendulum as pdlm


def authenticate_and_initialize():
    brkr = Finvasia(**cnfg)
    if not brkr.authenticate():
        logging.error("Failed to authenticate")
        SystemExit(1)

    Mcx.brkr = brkr
    Mcx.smcx = smcx
    squareoff = pdlm.parse(smcx["SQUAREOFF"], fmt="HH:mm").time()
    return squareoff


squareoff = authenticate_and_initialize()

while True:
    try:
        if (pdlm.now().time() > squareoff) or (Mcx.get_mcx_m2m() < smcx["STOP"]):
            Mcx.pack_and_go()
        else:
            print(
                f"time: {pdlm.now().format('HH:mm:ss')}"
                + f"                  {smcx['STOP']}                   "
                + f"squareoff: {squareoff}"
            )
    except Exception as e:
        # Handle the exception at the main loop level, e.g., log the error
        logging.error(f"An exception occurred in the main loop: {e}")

        # Re-authenticate and reinitialize
        squareoff = authenticate_and_initialize()
