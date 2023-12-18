from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger

logging = Logger(30, "debug.log")

fils = Fileutils()
utls = Utilities()

filepath = "../../"
data = filepath + "data/"
cnfg = fils.get_lst_fm_yml(filepath + "finvasia_amar.yaml")
settings = fils.get_lst_fm_yml(filepath + "settings.yml")
smcx = settings["MCX"]
common = settings["common"]
base = settings[common["base"]]
base["PFOLIO"] = base["PFOLIO_LAKHS"] * 100000
print(base)
