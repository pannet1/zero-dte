from prettytable import PrettyTable
from toolkit.regative import Regative


def prettier(**kwargs) -> dict:
    for k, v in kwargs.items():
        if k == "quotes":
            continue
        table = PrettyTable()
        if isinstance(v, dict):
            table.field_names = v.keys()
            table.add_row(v.values())
            print(table)
        elif isinstance(v, list) and any(v):
            table.field_names = v[0].keys()
            for item in v:
                table.add_row(item.values())
            print(table)
        else:
            print(f"{k}: {v}")
    print(25 * "=", " END OF REPORT ", 25 * "=", "\n")
    return kwargs


"""
# TODO to be removed
def _prettify(lst):
    if isinstance(lst, dict):
        lst = [lst]
    table = PrettyTable()
    table.field_names = lst[0].keys()
    for dct in lst:
        table.add_row(dct.values())
    print(table)
"""

if __name__ == "__main__":
    kwargs = {"key": {"key2": 2}, "key2": 1}
    prettier(**kwargs)
