import random
import time

from rich.live import Live
from rich.table import Table


def generate_table(**kwargs) -> Table:
    for k, v in kwargs.items():
        table = Table()
        if isinstance(v, dict):
            for p, q in v.items():
                table.add_column(p)

                table.add_row(str(q) + ",dsfadf")
        return table


while True:
    kwargs = {"kwargs": {"a": 1, "b": 2}}
    with Live(generate_table(**kwargs), refresh_per_second=1) as live:
        live.update(generate_table())
        time.sleep(1)
