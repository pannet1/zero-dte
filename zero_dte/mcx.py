from constants import logging, utls, smcx, print
import pandas as pd
from adjust_ltp import adjust_ltp


class Mcx:

    sorting = True
    brkr = None
    mty = pd.DataFrame()

    @ classmethod
    def get_mcx_positions(cls):
        try:
            utls.slp_for(1)
            df_pos = pd.DataFrame(cls.brkr.positions)

            if not df_pos or len(df_pos) == 0:
                return cls.mty
            else:
                df_pos = df_pos[['symbol', 'exchange', 'prd', 'token', 'ti',
                                'quantity', 'urmtom', 'rpnl', 'last_price']]
                df_pos = df_pos[df_pos['exchange'] == 'MCX']
                df_pos = df_pos[~df_pos['symbol'].isin(
                    smcx['IGNORE'])]
                df_print = df_pos.drop(
                    ['exchange', 'prd', 'token', 'ti'], axis=1).set_index('symbol')
                print("===       POSITIONS         === \n", df_print)
                return df_pos
        except Exception as e:
            raise

    @ classmethod
    def get_mcx_m2m(cls):
        df_pos = cls.get_mcx_positions()
        if len(df_pos) > 0:
            unrl = sum(df_pos['urmtom'].values)
            real = sum(df_pos['rpnl'].values)
            totl = int(unrl + real)
            print(f"total: {totl}")
            return totl
        else:
            print(f"no positions to STOP: {smcx['STOP']}")
            return 0

    @ classmethod
    def get_mcx_orders(cls):
        try:
            utls.slp_for(1)
            df_ord = pd.DataFrame(cls.brkr.orders)
            if not df_ord or len(df_ord) == 0:
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

    @staticmethod
    def cancel_order(row):
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

    @staticmethod
    def close_positions(row):
        try:
            utls.slp_for(0.5)
            dir = 1 if row['quantity'] < 0 else -1
            args = dict(
                side='B' if row['quantity'] < 0 else 'S',
                product=row['prd'],
                exchange=row['exchange'],
                quantity=abs(row['quantity']),
                disclosed_quantity=abs(row['quantity']),
                order_type="LMT",
                symbol=row['symbol'],
                price=adjust_ltp(row['last_price'],
                                 smcx['BUFF_PERC'], row['ti'], dir),
                tag="zero_dte"
            )
            logging.debug(f"closing position {args}")
            resp = cls.brkr.order_place(**args)
        except Exception as e:
            logging.error(f"{e} while placing order")

        if resp:
            print(resp)
        else:
            logging.warning(
                f"no reponse while trying to close {row['symbol']}")

    @ classmethod
    def pack_and_go(cls):
        try:
            df_ord = cls.get_mcx_orders()
            if len(df_ord) > 0:
                first_row = df_ord.iloc[0]
                cls.cancel_order(first_row)
            df_pos = cls.get_mcx_positions()
            df_pos = df_pos[df_pos['quantity'] != 0]
            if len(df_pos) > 0:
                df_pos.sort_values(
                    by='rpnl', ascending=cls.sorting, inplace=True)
                cls.sorting = False if cls.sorting else True
                first_row = df_pos.iloc[0]
                cls.close_positions(first_row)
        except Exception as e:
            raise (e)
