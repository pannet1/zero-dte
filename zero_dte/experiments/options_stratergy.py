from base import OptionsStrategy


class Zerodte(OptionsStrategy):
    def on_entry(self):
        print("Zerodte on_entry method called")

    def on_exit(self):
        print("Zerodte on_exit method called")

    def on_tick(self):
        print("Zerodte on_tick method called")

    def on_order(self):
        print("Zerodte on_order method called")

    def on_trade(self):
        print("Zerodte on_trade method called")
