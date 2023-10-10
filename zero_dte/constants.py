from toolkit.fileutils import Fileutils
from omspy_brokers.finvasia import Finvasia
from toolkit.logger import Logger

logging = Logger()
filh = "../../../"
fils = Fileutils()
cnfg = fils.get_lst_fm_yml(filh + "finvasia.yaml")
brkr = Finvasia(**cnfg)
