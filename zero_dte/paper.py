from random import randint
import pendulum as plum
import pandas as pd
from utils import calc_m2m


class Paper:
    def __init__(self, exchtkn: list, dct_tokens: dict):
        self.orders = pd.DataFrame(
            columns=["entry_time", "side", "quantity", "symbol", "price", "tag"]
        )
        self.exchtkn = exchtkn
        self.dct_tokens = dct_tokens

    def simultp(self, ltp, speed, tick=0.05):
        new_ltp = round(ltp + (randint(-1 * speed, speed) * tick), 2)
        if new_ltp <= 0:
            new_ltp = tick
        return new_ltp

    @property
    def ltp(self):
        dct = {}
        for token in self.exchtkn:
            dct[token] = randint(1, 100)
        return dct

    def order_place(self, **position_dict):
        args = dict(
            entry_time=plum.now().to_time_string(),
            exchange="NFO",
            side=position_dict["side"],
            quantity=int(position_dict["quantity"]),
            symbol=position_dict["symbol"],
            price=position_dict.get("prc", randint(1, 200)),
            tag=position_dict["tag"],
        )
        self.orders = pd.concat([self.orders, pd.DataFrame([args])], ignore_index=True)

    @property
    def positions(self):
        df = self.orders
        print(df)
        df_buy = df[df.side == "B"][["symbol", "quantity", "price"]]
        df_sell = df[df.side == "S"][["symbol", "quantity", "price"]]
        df = pd.merge(
            df_buy, df_sell, on="symbol", suffixes=("_buy", "_sell"), how="outer"
        ).fillna(0)
        df["bought"] = df.quantity_buy * df.price_buy
        df["sold"] = df.quantity_sell * df.price_sell
        df["quantity"] = df.quantity_buy - df.quantity_sell

        df = df.groupby("symbol").sum().reset_index()
        dct = df.to_dict(orient="records")
        quotes = self.ltp
        quotes = {self.dct_tokens[key]: value for key, value in quotes.items()}
        for pos in dct:
            pos["ltp"] = quotes[pos["symbol"]]
            pos["value"] = int(pos["quantity"] * pos["ltp"])
            pos["m2m"] = calc_m2m(pos) if pos["quantity"] != 0 else 0
            # TODO
            pos["rpl"] = pos["sold"] - pos["bought"] if pos["quantity"] == 0 else 0
        return dct
