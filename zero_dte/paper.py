from random import randint
import pendulum as plum
import pandas as pd
from utils import calc_m2m
from print import prettier


class Paper:
    cols = ["entry_time", "side", "filled_quantity",
            "symbol", "average_price", "remark"]

    def __init__(self, exchtkn: list, dct_tokens: dict):
        self.orders = pd.DataFrame()
        self.exchtkn = exchtkn
        self.dct_tokens = dct_tokens

    @property
    def ltp(self):
        dct = {}
        for token in self.exchtkn:
            symbol = self.dct_tokens[token]
            dct[symbol] = randint(1, 200) * 0.05
        return dct

    def order_place(self, **position_dict):
        args = dict(
            broker_timestamp=plum.now().to_time_string(),
            side=position_dict["side"],
            filled_quantity=int(position_dict["quantity"]),
            symbol=position_dict["symbol"],
            status="COMPLETED",
            average_price=position_dict.get("prc", randint(1, 2000) * 0.05),
            remarks=position_dict["tag"],
        )
        if not self.orders.empty:
            self.orders = pd.concat(
                [self.orders, pd.DataFrame([args])], ignore_index=True)
        else:
            self.orders = pd.DataFrame(columns=self.cols, data=[args])
        self.orders = pd.concat(
            [self.orders, pd.DataFrame([args])], ignore_index=True)

    @property
    def positions(self):
        df = self.orders
        df_buy = df[df.side == "B"][[
            "symbol", "filled_quantity", "average_price"]]
        df_sell = df[df.side == "S"][[
            "symbol", "filled_quantity", "average_price"]]
        df = pd.merge(
            df_buy, df_sell, on="symbol", suffixes=("_buy", "_sell"), how="outer"
        ).fillna(0)
        df["bought"] = df.filled_quantity_buy * df.average_price_buy
        df["sold"] = df.filled_quantity_sell * df.average_price_sell
        df["quantity"] = df.filled_quantity_buy - df.filled_quantity_sell
        df = df.groupby("symbol").sum().reset_index()
        lst = df.to_dict(orient="records")
        for pos in lst:
            pos["last_price"] = randint(47000, 47100)
            pos["urmtom"] = pos["quantity"]
            pos["urmtom"] = calc_m2m(pos)
            pos["rpnl"] = (pos["sold"] - pos["bought"]
                           ) if pos["quantity"] == 0 else 0
        keys = ['symbol', 'quantity', 'urmtom', 'rpnl', 'last_price']
        lst = [
            {k: d[k] for k in keys} for d in lst]
        """
        for pos in kwargs["positions"]:
            pos["last_price"] = kwargs["quotes"][pos["symbol"]]
            pos["urmtom"] = calc_m2m(pos) if pos["quantity"] != 0 else 0
            # TODO
            pos["rpnl"] = pos["sold"] - pos["bought"] if pos["quantity"] == 0 else 0
        """
        return lst


if __name__ == "__main__":
    from constants import base, common
    from symbols import Symbols
    SYMBOL = common["base"]
    obj_sym = Symbols(base['EXCHANGE'], SYMBOL, base["EXPIRY"])
    obj_sym.get_exchange_token_map_finvasia()

    dct_tokens = obj_sym.get_tokens(20250)
    lst_tokens = list(dct_tokens.keys())
    brkr = Paper(lst_tokens, dct_tokens)

    args = dict(
        broker_timestamp=plum.now().to_time_string(),
        side="B",
        quantity="50",
        symbol=SYMBOL + base['EXPIRY'] + "C" + "23500",
        tag="paper",
    )
    brkr.order_place(**args)
    args.update({"side": "S", "symbol": SYMBOL +
                base['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)
    args.update({"side": "S", "symbol": SYMBOL +
                base['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)
    args.update({"side": "B", "symbol": SYMBOL +
                base['EXPIRY'] + "P" + "22400"})
    brkr.order_place(**args)

    kwargs = {
        "pos": brkr.positions
    }
    prettier(**kwargs)
