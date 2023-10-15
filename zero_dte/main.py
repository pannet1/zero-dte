from mcx import Mcx
from constants import brkr, setg
import pendulum as pdlm

if not brkr.authenticate():
    logging.error("failed to authenticate")
    SystemExit(1)

Mcx.brkr = brkr
while True:
    if (
        (pdlm.now().time() > pdlm.time(23, 30))
        or (Mcx.get_mcx_m2m() < setg['stop'])
    ):
        Mcx.pack_and_go()
