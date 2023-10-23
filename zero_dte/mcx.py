from constants import logging, utls, smcx, print, Console
import pandas as pd
from round_to_paise import adjust_ltp


class Regative:
    def __init__(self, val):
        self.val = val

    def __rich__(self) -> str:
        if self.val < 0:
            return f"[bold red]{self.val}"
        else:
            return f"[bold green]{self.val}"


class Mcx:

    sorting = True
    brkr = None
    mty = pd.DataFrame()

    @ classmethod
    def get_mcx_positions(cls):
        try:
            utls.slp_for(1)
            df_pos = pd.DataFrame(cls.brkr.positions)

            if df_pos is not None and len(df_pos) == 0:
                return cls.mty
            else:
                df_pos = df_pos[['symbol', 'exchange', 'prd', 'token', 'ti',
                                'quantity', 'urmtom', 'rpnl', 'last_price']]
                df_pos = df_pos[df_pos['exchange'] == 'MCX']
                df_pos = df_pos[~df_pos['symbol'].isin(
                    smcx['IGNORE'])]
                df_print = df_pos.drop(
                    ['exchange', 'prd', 'token', 'ti'], axis=1).set_index('symbol')
                print(df_print)
                return df_pos
        except Exception as e:
            raise

    @ classmethod
    def get_mcx_m2m(cls):
        df_pos = cls.get_mcx_positions()
        pretty = f"{62* ' '}"
        if len(df_pos) > 0:
            unrl = sum(df_pos['urmtom'].values)
            real = sum(df_pos['rpnl'].values)
            totl = int(unrl + real)
            print(pretty, "TOTAL:", Regative(totl), "\n")
            return totl
        else:
            print(pretty, "STOP:", smcx["STOP"], "\n")
            return 0

    @ classmethod
    def get_mcx_orders(cls):
        try:
            utls.slp_for(1)
            df_ord = pd.DataFrame(cls.brkr.orders)
            if df_ord is not None or len(df_ord) == 0:
                return cls.mty
            else:
                cols = ['order_id', 'exchange', 'symbol', 'quantity', 'side',
                        'validity', 'token', 'prd', 'status', ]
                df_ord = df_ord[cols]
                df_ord = df_ord[df_ord['exchange'] == 'MCX']
                condtn = ('OPEN' or 'TRIGGER_PENDING')
                df_ord = df_ord[df_ord['status'] == condtn]
                df_ord = df_ord[~df_ord['symbol'].isin(smcx['IGNORE'])]
                print("===          POSITIONS           ===\n", "df_ord")
                return df_ord
        except Exception as e:
            logging.warning(f"{e} while getting ORDERS")
            return cls.mty

    @ classmethod
    def cancel_order(cls, row):
        try:
            utls.slp_for(1)
            cls.brkr.order_cancel(row['order_id'])
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
            utls.slp_for(0.5)
            dir = 1 if row['quantity'] < 0 else -1
            prc = adjust_ltp(row['last_price'],
                             dir * smcx['BUFF_PERC'], row['ti'])
            #prc = row['last_price'] + \
            #   buff if dir == 1 else row['last_price'] - buff
            args = dict(
                side='B' if row['quantity'] < 0 else 'S',
                product=row['prd'],
                exchange=row['exchange'],
                quantity=abs(row['quantity']),
                disclosed_quantity=abs(row['quantity']),
                order_type="LMT",
                symbol=row['symbol'],
                price=prc,
                tag="zero_dte"
            )
            resp = cls.brkr.order_place(**args)
            if resp:
                logging.debug(f"{args}{resp}")
            else:
                logging.warning(f"closing position {args} with tick size: {row['ti']}")
        except Exception as e:
            logging.error(f"{e} while closing positions")


    @ classmethod
    def pack_and_go(cls):
        try:
            df_pos = cls.get_mcx_positions()
            df_pos = df_pos[df_pos['quantity'] != 0]
            if len(df_pos) > 0:
                df_pos.sort_values(
                    by='rpnl', ascending=cls.sorting, inplace=True)
                cls.sorting = False if cls.sorting else True
                first_row = df_pos.iloc[0]
                cls.close_positions(first_row)

            df_ord = cls.get_mcx_orders()
            if len(df_ord) > 0:
                first_row = df_ord.iloc[0]
                cls.cancel_order(first_row)
        except Exception as e:
            raise (e)
