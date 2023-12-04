from random import randint
import pendulum as plum
import pandas as pd


class Paper:
    def __init__(self, exchtkn: list):
        self.orders = pd.DataFrame(
            columns=["entry_time", "side", "quantity", "symbol", "price", "tag"]
        )
        self.exchtkn = exchtkn

    def simultp(self, ltp, speed, tick=0.05):
        new_ltp = round(ltp + (randint(-1 * speed, speed) * tick), 2)
        if new_ltp <= 0:
            new_ltp = tick
        return new_ltp

    """
    def replace_position(self, position_dict):
        symbol = position_dict["symbol"]
        for entry in self.positions:
            if entry["symbol"] == symbol:
                entry = position_dict
    """

    @property
    def ltp(self):
        dct = {}
        for token in self.exchtkn:
            dct[token] = randint(1, 200)
        return dct

    def order_place(self, position_dict):
        args = dict(
            entry_time=plum.now().to_time_string(),
            side=position_dict["side"],
            quantity=int(position_dict["qty"]),
            symbol=position_dict["symbol"],
            price=position_dict.get("prc", randint(1, 200)),
            tag=position_dict["tag"],
        )
        self.orders = pd.concat([self.orders, pd.DataFrame([args])], ignore_index=True)

    @property
    def positions(self):
        df = self.orders
        df_buy = df[df.side == "B"][["symbol", "quantity", "price"]]
        df_sell = df[df.side == "S"][["symbol", "quantity", "price"]]
        df = pd.merge(
            df_buy, df_sell, on="symbol", suffixes=("_buy", "_sell"), how="outer"
        ).fillna(0)
        df["bought"] = df.quantity_buy * df.price_buy
        df["sold"] = df.quantity_sell * df.price_sell
        df["qty"] = df.quantity_buy - df.quantity_sell
        df["m2m"] = df.sold - df.bought
        dct = df.to_dict(orient="records")
        return dct
