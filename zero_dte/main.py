from constants import brkr, logging, utls, setg
import pandas as pd
import pendulum as pdlm

m2m = 10000
if not brkr.authenticate():
    logging.error("failed to authenticate")
    SystemExit(1)


class Mcx:

    sorted = True

    @ classmethod
    def mcx_positions(cls):
        df_pos = pd.DataFrame(brkr.positions)
        if len(df_pos) > 0:
            print(df_pos.columns)
            df_pos = df_pos[['symbol', 'exchange', 's_prdt_ali', 'token',
                            'quantity', 'urmtom', 'rpnl', 'last_price']]
            print("positions \n", df_pos)
            df_pos = df_pos[df_pos['exchange'] == 'MCX']
            df_pos = df_pos[df_pos['quantity'] != 0]
            df_pos = df_pos[~df_pos['symbol'].isin(setg['ignore'])]
        return df_pos

    @ classmethod
    def get_mcx_m2m(cls):
        utls.slp_til_nxt_sec()
        df_pos = cls.mcx_positions()
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
            print(df_ord)
        return df_ord

    @ staticmethod
    def cancel_order(row):
        brkr.order_cancel(row['order_id'])

    @staticmethod
    def close_positions(row):
        args = dict(
            side='B' if row['quantity'] < 0 else 'S',
            product=row['prd'],
            exchange=row['exchange'],
            quantity=abs(row['quantity']),
            disclosed_quantity=abs(row['quantity']),
            order_type="LMT",
            symbol=row['symbol'],
            price=0,
            tag="zero_dte"
        )
        logging.debug(args)
        resp = brkr.order_place(**args)
        if resp:
            print(resp)

    @ classmethod
    def pack_and_go(cls):
        df_ord = cls.get_mcx_orders()
        if len(df_ord) > 0:
            df_ord.apply(cls.cancel_order, axis=1)
        df_pos = cls.mcx_positions()
        if len(df_pos) > 0:
            df_pos.apply(cls.close_positions, axis=1)


while (
    (pdlm.now().time() < pdlm.time(23, 30))
    and (Mcx.get_mcx_m2m() > m2m)
):
    pass

Mcx.pack_and_go()
