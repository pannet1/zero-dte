from constants import brkr, logging, utls, setg
import pandas as pd
import pendulum as pdlm
from adjust_ltp import adjust_ltp

if not brkr.authenticate():
    logging.error("failed to authenticate")
    SystemExit(1)


class Mcx:

    sorting = True

    @ classmethod
    def get_mcx_positions(cls):
        df_pos = pd.DataFrame(brkr.positions)
        if len(df_pos) > 0:
            df_pos = df_pos[['symbol', 'exchange', 'prd', 'token', 'ti',
                            'quantity', 'urmtom', 'rpnl', 'last_price']]
            df_pos = df_pos[df_pos['exchange'] == 'MCX']
            df_pos = df_pos[df_pos['quantity'] != 0]
            df_pos = df_pos[~df_pos['symbol'].isin(setg['ignore'])]
            print("positions \n", df_pos)
        return df_pos

    @ classmethod
    def get_mcx_m2m(cls):
        utls.slp_til_nxt_sec()
        df_pos = cls.get_mcx_positions()
        unrl = sum(df_pos['urmtom'].values)
        real = sum(df_pos['rpnl'].values)
        totl = unrl + real
        logging.info(f"total: {totl}")
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
            # Delete rows where 'symbol' is in the 'ignore' list
            df_ord = df_ord[~df_ord['symbol'].isin(setg['ignore'])]
            print("orders \n", "df_ord)
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
                             setg['buff_per'], row['ti'], dir),
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
        if len(df_pos) > 0:
            df_pos.sort_values(by='rpnl', ascending=cls.sorting, inplace=True)
            cls.sorting = True if cls.sorting else False
            first_row = df_pos.iloc[0]
            cls.close_positions(first_row)


while True:
    if (
        (pdlm.now().time() > pdlm.time(23, 30))
        or (Mcx.get_mcx_m2m() < setg['stop'])
    ):
        Mcx.pack_and_go()
