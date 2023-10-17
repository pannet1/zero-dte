from constants import logging, utls, smcx, print
import pandas as pd
from adjust_ltp import adjust_ltp


class Mcx:

    sorting = True
    brkr = None

    @ classmethod
    def get_mcx_positions(cls):
        df_pos = pd.DataFrame(cls.brkr.positions)
        if len(df_pos) > 0:
            df_pos = df_pos[['symbol', 'exchange', 'prd', 'token', 'ti',
                            'quantity', 'urmtom', 'rpnl', 'last_price']]
            df_pos = df_pos[df_pos['exchange'] == 'MCX']
            df_pos = df_pos[~df_pos['symbol'].isin(
                smcx['IGNORE'])]
            df_print = df_pos.drop(
                ['exchange', 'prd', 'token', 'ti'], axis=1).set_index('symbol')
            print("positions \n", df_print)
        return df_pos

    @ classmethod
    def get_mcx_m2m(cls):
        utls.slp_til_nxt_sec()
        df_pos = cls.get_mcx_positions()
        unrl = sum(df_pos['urmtom'].values)
        real = sum(df_pos['rpnl'].values)
        totl = int(unrl + real)
        print(f"total: {totl}")
        return totl

    @ classmethod
    def get_mcx_orders(cls):
        utls.slp_til_nxt_sec()
        df_ord = pd.DataFrame(brkr.orders)
        if len(df_ord) > 0:
            cols = ['order_id', 'exchange', 'symbol', 'quantity', 'side',
                    'validity', 'token', 'prd', 'status', ]
            df_ord = df_ord[cols]
            df_ord = df_ord[df_ord['exchange'] == 'MCX']
            condtn = ('OPEN' or 'TRIGGER_PENDING')
            df_ord = df_ord[df_ord['status'] == condtn]
            df_ord = df_ord[~df_ord['symbol'].isin(smcx['IGNORE'])]
            print("orders \n", "df_ord")
        return df_ord

    @ staticmethod
    def cancel_order(row):
        logging.debug(
            f"canceling order# {row['order_id']} "
            f"with {row['side']} {row['symbol']}"
        )
        brkr.order_cancel(row['order_id'])

    @staticmethod
    def close_positions(row):
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
        resp = brkr.order_place(**args)
        if resp:
            logging.info(resp)

    @ classmethod
    def pack_and_go(cls):
        df_ord = cls.get_mcx_orders()
        if len(df_ord) > 0:
            first_row = df_ord.iloc[0]
            cls.cancel_order(first_row)
        df_pos = cls.get_mcx_positions()
        df_pos = df_pos[df_pos['quantity'] != 0]
        if len(df_pos) > 0:
            df_pos.sort_values(by='rpnl', ascending=cls.sorting, inplace=True)
            cls.sorting = False if cls.sorting else True
            first_row = df_pos.iloc[0]
            cls.close_positions(first_row)
