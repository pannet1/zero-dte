from toolkit.logger import Logger
from toolkit.utilities import Utilities
from toolkit.round_to_paise import adjust_ltp
from toolkit.regative import Regative
from rich import print
import pandas as pd

logging = Logger(10)


class Mcx:
    sorting = True
    brkr = None
    smcx = {}
    mty = pd.DataFrame()

    @classmethod
    def get_mcx_positions(cls):
        try:
            Utilities().slp_for(1)
            df_pos = pd.DataFrame(cls.brkr.positions)
            columns_to_check = [
                "symbol",
                "exchange",
                "prd",
                "token",
                "ti",
                "quantity",
                "urmtom",
                "rpnl",
                "last_price",
            ]
            if df_pos is not None and len(df_pos) == 0:
                return cls.mty
            elif all(column in df_pos.columns for column in columns_to_check):
                df_pos = df_pos[columns_to_check]
                df_pos = df_pos[df_pos["exchange"] == "MCX"]
                if cls.smcx.get("IGNORE", False):
                    df_pos = df_pos[~df_pos["symbol"].isin(cls.smcx["IGNORE"])]
                df_print = df_pos.drop(
                    ["exchange", "prd", "token", "ti"], axis=1
                ).set_index("symbol")
                print(df_print)
                return df_pos
        except Exception as e:
            raise

    @classmethod
    def get_mcx_m2m(cls):
        df_pos = cls.get_mcx_positions()
        pretty = f"{62* ' '}"
        if len(df_pos) > 0:
            unrl = sum(df_pos["urmtom"].values)
            real = sum(df_pos["rpnl"].values)
            totl = int(unrl + real)
            print(pretty, "TOTAL:", Regative(totl), "\n")
            return totl
        else:
            print(pretty, "STOP:", cls.smcx["STOP"], "\n")
            return 0

    @classmethod
    def get_mcx_orders(cls):
        try:
            Utilities().slp_for(1)
            df_ord = pd.DataFrame(cls.brkr.orders)
            if df_ord is not None or len(df_ord) == 0:
                return cls.mty
            else:
                cols = [
                    "order_id",
                    "exchange",
                    "symbol",
                    "quantity",
                    "side",
                    "validity",
                    "token",
                    "prd",
                    "status",
                ]
                df_ord = df_ord[cols]
                df_ord = df_ord[df_ord["exchange"] == "MCX"]
                condtn = "OPEN" or "TRIGGER_PENDING"
                df_ord = df_ord[df_ord["status"] == condtn]
                if cls.smcx.get("IGNORE", False):
                    df_ord = df_ord[~df_ord["symbol"].isin(cls.smcx["IGNORE"])]
                print("===          POSITIONS           ===\n", "df_ord")
                return df_ord
        except Exception as e:
            logging.warning(f"{e} while getting ORDERS")
            return cls.mty

    @classmethod
    def cancel_order(cls, row):
        try:
            Utilities().slp_for(1)
            cls.brkr.order_cancel(row["order_id"])
        except Exception as e:
            logging.warning(f"{e} while CANCELLING order for {row['symbol']}")
        else:
            logging.debug(
                f"cancelled order# {row['order_id']} "
                f"with {row['side']} {row['symbol']} "
            )

    @classmethod
    def close_positions(cls, row):
        try:
            Utilities().slp_for(0.5)
            dir = 1 if row["quantity"] < 0 else -1
            prc = adjust_ltp(row["last_price"], dir * cls.smcx["BUFF_PERC"], row["ti"])
            # prc = row['last_price'] + \
            #   buff if dir == 1 else row['last_price'] - buff
            args = dict(
                side="B" if row["quantity"] < 0 else "S",
                product=row["prd"],
                exchange=row["exchange"],
                quantity=abs(row["quantity"]),
                disclosed_quantity=abs(row["quantity"]),
                order_type="LMT",
                symbol=row["symbol"],
                price=prc,
                tag="zero_dte",
            )
            resp = cls.brkr.order_place(**args)
            if resp:
                logging.debug(f"{args}{resp}")
            else:
                logging.warning(f"closing position {args} with tick size: {row['ti']}")
        except Exception as e:
            logging.error(f"{e} while closing positions")

    @classmethod
    def pack_and_go(cls):
        try:
            df_pos = cls.get_mcx_positions()
            df_pos = df_pos[df_pos["quantity"] != 0]
            if len(df_pos) > 0:
                df_pos.sort_values(by="rpnl", ascending=cls.sorting, inplace=True)
                cls.sorting = False if cls.sorting else True
                first_row = df_pos.iloc[0]
                cls.close_positions(first_row)

            df_ord = cls.get_mcx_orders()
            if len(df_ord) > 0:
                first_row = df_ord.iloc[0]
                cls.cancel_order(first_row)
        except Exception as e:
            raise (e)
