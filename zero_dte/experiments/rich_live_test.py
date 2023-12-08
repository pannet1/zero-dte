import time

from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table


def generate_table(**kwargs) -> Table:
    kwargs["e"] = {"e": 4}
    for k, v in kwargs.items():
        table = Table()
        if isinstance(v, dict):
            for p, q in v.items():
                table.add_column(p)
                table.add_row(str(q) + ",dsfadf")
                print(p, q)
        return table


console = Console()

with Live(console=console, screen=True, auto_refresh=False) as live:
    while True:
        kwargs = {"kwargs": {"a": 1, "b": 2, "c": 3}}
        live.update(generate_table(**kwargs), refresh=True)
        time.sleep(1)
