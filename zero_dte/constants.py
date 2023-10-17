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

try:
    from rich import print
except ImportError:
    # Module is not installed, attempt to install it
    import subprocess
    import sys

    # Replace 'your_module' with the actual module name you want to install
    module_name = "rich"

    # Use 'pip' to install the module
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", module_name])
    except subprocess.CalledProcessError:
        print(f"Failed to install {module_name}. Please install it manually.")
    else:
        # Module installed successfully, now you can import it
        from rich import print


