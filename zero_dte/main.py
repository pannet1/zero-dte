from stratergy.mcx import Mcx
from omspy_brokers.finvasia import Finvasia
from constants import common, smcx, cnfg, logging
import pendulum as pdlm
import traceback


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
        if (
            pdlm.now().time().add(hours=common["h"], minutes=common["m"]) > squareoff
        ) or (Mcx.get_mcx_m2m() < smcx["STOP"]):
            Mcx.pack_and_go()
        elif (
            pdlm.now().time().add(hours=common["h"], minutes=common["m"])
            > pdlm.parse("23:40", fmt="HH:mm").time()
        ):
            SystemExit(0)
        else:
            print(
                f"time: {pdlm.now().add(hours=common['h'], minutes=common['m']).format('HH:mm:ss')}"
                + f"                  {smcx['STOP']}                   "
                + f"squareoff: {squareoff}"
            )
    except Exception as e:
        # Handle the exception at the main loop level, e.g., log the error
        logging.error(f"error ccurred in the main loop: {e}")
        print(traceback.print_exc())
        # Re-authenticate and reinitialize
        squareoff = authenticate_and_initialize()
