from abc import ABC, abstractmethod


class Strategy(ABC):
    """
    base stratergy that abstracs
    """

    @abstractmethod
    def on_entry(self):
        pass

    @abstractmethod
    def on_exit(self):
        pass

    @abstractmethod
    def on_tick(self):
        pass

    @abstractmethod
    def on_order(self):
        pass

    @abstractmethod
    def on_trade(self):
        pass


class OptionsStrategy(ABC):
    """
    base option stratergy that abstracts
    """

    @abstractmethod
    def on_entry(self):
        pass

    @abstractmethod
    def on_exit(self):
        pass

    @abstractmethod
    def on_tick(self):
        pass

    @abstractmethod
    def on_order(self):
        pass

    @abstractmethod
    def on_trade(self):
        pass
