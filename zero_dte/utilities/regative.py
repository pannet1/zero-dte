from rich import print
from rich.console import Console, ConsoleOptions, RenderResult
from rich.segment import Segment, Style


class Regative:
    def __init__(self, val):
        self.val = val

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        if isinstance(self.val, (int, float)):
            if self.val < 0:
                # return f"[bold red]{self.val}"
                yield Segment(str(self.val), Style(color="Red"))
            # Handle the case where the conversion to float fails
        else:
            yield Segment(str(self.val), Style(color="Green"))


if __name__ == "__main__":
    print(Regative(-.01))
