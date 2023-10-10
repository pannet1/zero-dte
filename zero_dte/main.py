from constants import brkr, logging, utls
import pandas as pd
import pendulum as pdlm


m2m = -100

if not brkr.authenticate():
    logging.error("failed to authenticate")
    SystemExit(1)


def mcx_positions():
    df_pos = pd.DataFrame(brkr.positions)
    df_pos = df_pos[df_pos['exchange'] == 'MCX']
    df_pos = df_pos[df_pos['quantity'] != 0]
    df_pos = df_pos[['symbol', 's_prdt_ali', 'token', 'instname', 'ls', 'ti',
                    'daybuyqty', 'daysellqty', 'quantity', 'urmtom', 'rpnl']]
    print(df_pos)
    return df_pos


def get_mcx_m2m():
    df_pos = mcx_positions()
    m2m = sum(df_pos['urmtom'].values)
    return m2m


def close_orders():
    df_ord = pd.DataFrame(brkr.orders)
    print(df_ord)
    utls.slp_til_nxt_sec()


def pack_and_go():
    close_orders()


while (
    (pdlm.now().time() < pdlm.time(23, 30))
    and (get_mcx_m2m() > m2m)
):
    utls.slp_til_nxt_sec()

pack_and_go()
