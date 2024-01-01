from prettytable import PrettyTable
from rich import print
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
            print(Regative(k), Regative(v))
            # print(:25 * "=", " END OF REPORT ", 25 * "=", "\n")
    return kwargs


if __name__ == "__main__":
    kwargs = {"key1": {"key11": 11}, "key2": -2}
    prettier(**kwargs)
