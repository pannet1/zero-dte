from toolkit.fileutils import Fileutils
from omspy_brokers.finvasia import Finvasia
from toolkit.utilities import Utilities
from toolkit.logger import Logger


logging = Logger(10)
filh = "../../../"
fils = Fileutils()
cnfg = fils.get_lst_fm_yml(filh + "finvasia_amar.yaml")
brkr = Finvasia(**cnfg)
utls = Utilities()
setg = fils.get_lst_fm_yml("settings.yml")
smcx = setg['MCX']
snse = setg['NSE']
