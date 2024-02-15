from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger

fname = "finvasia_amar"
filepath = "../../"
logging = Logger(10, f"{filepath}{fname}.log")
fils = Fileutils()
utls = Utilities()

data = filepath + "data/"
settings = fils.get_lst_fm_yml(f"{filepath}{fname}.yaml")
cnfg = settings["config"]
smcx = settings["MCX"]
common = settings["common"]
base = settings[common["base"]]
base["PFOLIO"] = base["PFOLIO_LAKHS"] * 100000
print(f"{cnfg =}\n")
print(f"{smcx =}\n")
print(f"{common =}\n")
print(f"{base=}\n")
