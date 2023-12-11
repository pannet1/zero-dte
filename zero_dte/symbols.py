import pandas as pd
import re

dct_sym = {
    "NIFTY": {
        "diff": 50,
        "index": "Nifty 50",
        "exch": "NSE",
        "token": "26000",
        "depth": 16,
    },
    "BANKNIFTY": {
        "diff": 100,
        "index": "Nifty Bank",
        "exch": "NSE",
        "token": "26009",
        "depth": 25,
    },
    "MIDCPNIFTY": {
        "diff": 100,
        "index": "NIFTY MID SELECT",
        "exch": "NSE",
        "token": "26074",
        "depth": 21,
    },
    "FINNIFTY": {
        "diff": 50,
        "index": "Nifty Fin Services",
        "exch": "NSE",
        "token": "26037",
        "depth": 16,
    },
}


class Symbols:
    def __init__(self, exch, symbol: str, expiry: str):
        self.exch = exch
        self.symbol = symbol
        self.expiry = expiry

    def get_exchange_token_map_finvasia(self):
        url = f"https://api.shoonya.com/{self.exch}_symbols.txt.zip"
        print(f"{url}")
        df = pd.read_csv(url)
        # filter the response
        df = df[
            (df["Exchange"] == self.exch)
            # & (df["TradingSymbol"].str.contains(self.symbol + self.expiry))
        ][["Token", "TradingSymbol"]]
        # split columns with necessary values
        df[["Symbol", "Expiry", "OptionType", "StrikePrice"]] = df[
            "TradingSymbol"
        ].str.extract(r"([A-Z]+)(\d+[A-Z]+\d+)([CP])(\d+)")
        df.to_csv(f"{self.exch}_symbols.csv", index=False)

    def get_atm(self, ltp) -> int:
        current_strike = ltp - (ltp % dct_sym[self.symbol]["diff"])
        next_higher_strike = current_strike + dct_sym[self.symbol]["diff"]
        if ltp - current_strike < next_higher_strike - ltp:
            return int(current_strike)
        return int(next_higher_strike)

    def get_tokens(self, strike):
        df = pd.read_csv(f"{self.exch}_symbols.csv")
        lst = []
        lst.append(self.symbol + self.expiry + "C" + str(strike))
        lst.append(self.symbol + self.expiry + "P" + str(strike))
        for v in range(1, dct_sym[self.symbol]["depth"]):
            lst.append(
                self.symbol
                + self.expiry
                + "C"
                + str(strike + v * dct_sym[self.symbol]["diff"])
            )
            lst.append(
                self.symbol
                + self.expiry
                + "P"
                + str(strike + v * dct_sym[self.symbol]["diff"])
            )
            lst.append(
                self.symbol
                + self.expiry
                + "C"
                + str(strike - v * dct_sym[self.symbol]["diff"])
            )
            lst.append(
                self.symbol
                + self.expiry
                + "P"
                + str(strike - v * dct_sym[self.symbol]["diff"])
            )

        df["Exchange"] = self.exch
        tokens_found = (
            df[df["TradingSymbol"].isin(lst)]
            .assign(tknexc=df["Exchange"] + "|" + df["Token"].astype(str))[
                ["tknexc", "TradingSymbol"]
            ]
            .set_index("tknexc")
        )
        dct = tokens_found.to_dict()
        return dct["TradingSymbol"]

    def find_closest_premium(self, quotes, premium, contains):
        contains = self.expiry + contains
        closest_symbol = None
        closest_difference = float("inf")

        for symbol, ltp in quotes.items():
            if re.search(re.escape(contains), symbol):
                difference = abs(ltp - premium)
                if difference < closest_difference:
                    closest_difference = difference
                    closest_symbol = symbol
        return closest_symbol


if __name__ == "__main__":
    symbols = Symbols("NFO", "NIFTY", "14DEC23")
    symbols.get_exchange_token_map_finvasia()
    print(symbols.get_tokens(20250))
