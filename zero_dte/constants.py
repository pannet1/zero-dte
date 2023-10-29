from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger

logging = Logger(10)

fils = Fileutils()
utls = Utilities()

filepath = "../../"
cnfg = fils.get_lst_fm_yml(filepath + "finvasia_amar.yaml")
settings = fils.get_lst_fm_yml(filepath + "settings.yml")
smcx = settings["MCX"]
snse = settings["NSE"]
snse["PFOLIO"] = snse["PFOLIO_LAKHS"] * 100000
