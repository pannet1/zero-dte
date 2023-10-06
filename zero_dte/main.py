from builder import Builder
from copy import deepcopy
import inspect
from time import sleep
from quotes import option_chain
from chain import get_ltp_fm_chain
from netools import load_ymls_from_github, load_dict_from_github
from toolkit.redis_client import RedisClient
from toolkit.logger import Logger

logging = Logger(10)

try:
    kite = RedisClient()
    kite.authenticate()
    yaml_file = "Curr_Week_NIFTY_fm_FUT.yaml"
    if yaml_file is not None:
        data = load_dict_from_github("netools", "oc-trade", yaml_file)
        logging.debug(data)
        if data is not None:
            d_bld = data
            bldr = Builder(d_bld)
            # get ltp of the underlying:Warning to get the ATM
            ulying = kite.ltp(d_bld['base_script'])
            base_ltp = ulying[d_bld['base_script']]["last_price"]
            # more settings for builder
            atm = bldr.get_atm_strike(base_ltp)
            d_bld['exchsym'] = bldr.get_syms_fm_atm(atm)
            d_bld["oc"] = bldr
except Exception as e:
    logging.debug(e)
