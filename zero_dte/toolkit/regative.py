from rich.console import Console


class Regative:
    def __init__(self, val):
        self.val = val

    def __rich__(self) -> str:
        if isinstance(self.val, (int, float)) and self.val < 0:
            return f"[bold red]{self.val}"
        else:
            return f"[bold green]{self.val}"


if __name__ == "__main__":
    from rich import print

    print(Regative("a"))
