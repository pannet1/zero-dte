from constants import fils, filepath
from utilities.printutils import prettier
from time import sleep

data = filepath + "data/"
files = fils.get_files_with_extn("json", data)
files = [file.split(".")[0] for file in files]
files = [file for file in files
         if file.isdigit() and len(file) == 6]
files.sort()
for file in files:
    obj = fils.json_fm_file(data + str(file))
    prettier(**obj)
    sleep(0.5)

# sort a list in ascending order
#
