import pandas as pd
import re
from toolkit.fileutils import Fileutils
from typing import Dict, Optional

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
    "SENSEX": {
        "diff": 100,
        "index": "BSE Sensex 50",
        "exch": "BSE",
        "token": "1",
        "depth": 16,
    },
    "BANKEX": {
        "diff": 100,
        "index": "BSE Bankex",
        "exch": "BSE",
        "token": "12",
        "depth": 16,
    }
}


class Symbols:
    def __init__(self, exch, symbol: str, expiry: str):
        self.exch = exch
        self.symbol = symbol
        self.expiry = expiry
        self.csvfile = f"./{self.exch}_symbols.csv"

    def get_exchange_token_map_finvasia(self):
        if Fileutils().is_file_not_2day(self.csvfile):
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
            df.to_csv(self.csvfile, index=False)

    def get_atm(self, ltp) -> int:
        current_strike = ltp - (ltp % dct_sym[self.symbol]["diff"])
        next_higher_strike = current_strike + dct_sym[self.symbol]["diff"]
        if ltp - current_strike < next_higher_strike - ltp:
            return int(current_strike)
        return int(next_higher_strike)

    def get_tokens(self, strike):
        df = pd.read_csv(self.csvfile)
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

    def find_closest_premium(self,
                             quotes: Dict[str, float],
                             premium: float,
                             contains: str) -> Optional[str]:
        contains = self.expiry + contains
        # Create a dictionary to store symbol to absolute difference mapping
        symbol_differences: Dict[str, float] = {}

        for symbol, ltp in quotes.items():
            if re.search(re.escape(contains), symbol):
                difference = abs(ltp - premium)
                symbol_differences[symbol] = difference

        # Find the symbol with the lowest difference
        closest_symbol = min(symbol_differences,
                             key=symbol_differences.get, default=None)

        return closest_symbol

    def find_symbol_in_moneyness(self,
                                 tradingsymbol,
                                 ce_or_pe,
                                 price_type):
        def find_strike(ce_or_pe):
            search = self.symbol + self.expiry + ce_or_pe
            # find the remaining string in the symbol after removing search
            strike = re.sub(search, '', tradingsymbol)
            return search, int(strike)

        search, strike = find_strike(ce_or_pe)
        if ce_or_pe == "C":
            if price_type == "ITM":
                return search + str(strike - dct_sym[self.symbol]["diff"])
            else:
                return search + str(strike + dct_sym[self.symbol]["diff"])
        else:
            if price_type == "ITM":
                return search + str(strike + dct_sym[self.symbol]["diff"])
            else:
                return search + str(strike - dct_sym[self.symbol]["diff"])

    def calc_straddle_value(self, atm: int, quotes: list):
        ce = self.symbol + self.expiry + "C" + str(atm)
        pe = self.symbol + self.expiry + "P" + str(atm)
        return quotes[ce] + quotes[pe]

    def find_option_type(self, tradingsymbol):
        option_pattern = re.compile(rf"{self.symbol}{self.expiry}([CP])\d+")
        match = option_pattern.match(tradingsymbol)
        if match:
            return match.group(1)  # Returns 'C' for call, 'P' for put
        else:
            return False


if __name__ == "__main__":
    symbols = Symbols("BSE", "SENSEX", "29MAR24")
    symbols.get_exchange_token_map_finvasia()
    # print(symbols.find_option_type("BANKNIFTY28DEC23C47000"))
