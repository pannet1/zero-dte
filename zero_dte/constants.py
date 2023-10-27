from toolkit.fileutils import Fileutils
from toolkit.utilities import Utilities
from toolkit.logger import Logger
from rich import print

logging = Logger(10)

fils = Fileutils()
utls = Utilities()

filepath = "../../"
cnfg = fils.get_lst_fm_yml(filepath + "finvasia_amar.yaml")

settings = fils.get_lst_fm_yml("settings.yml")
smcx = settings["MCX"]
snse = settings["NSE"]
