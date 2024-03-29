from typing import Callable
import unittest
from decimal import Decimal, ROUND_HALF_EVEN


def calc_m2m(pos):
    if pos["quantity"] > 0:
        sold = int(pos["quantity"]) * int(pos["last_price"])
        return sold - pos["bought"]
    elif pos["quantity"] < 0:
        return pos["sold"] - (abs(pos["quantity"]) * pos["last_price"])
    elif pos["quantity"] == 0:
        return 0


def round_val_to_qty(
    val: int, ltp: float, base_lot: int
):
    """
        removed from zero_dte
    """
    if ltp == 0:
        ltp = 0.05
    qty = val / ltp
    lot = round(qty / base_lot)
    qty = lot * base_lot
    return qty


def val_to_qty(
    val: int, ltp: float, base_lot: int, calc_method: Callable
):
    if ltp == 0:
        ltp = 0.05
    val_per_ltp = val / ltp
    lot = calc_method(val_per_ltp / base_lot)
    qty = lot * base_lot
    return qty


def adjust_ltp(buy_price: float, buffer_percent=0.5, tick_size=0.05):
    buy_price_decimal = Decimal(str(buy_price))
    buffer_amount_decimal = buy_price_decimal * \
        (Decimal(str(buffer_percent)) / 100)

    # Calculate the buffered price without rounding
    pending_order_price = buy_price_decimal + buffer_amount_decimal

    # Calculate the number of ticks (tick_size) needed to round to the nearest tick
    ticks_needed = (pending_order_price / Decimal(str(tick_size))
                    ).to_integral_value(rounding=ROUND_HALF_EVEN)

    # Calculate the rounded price
    pending_order_price_rounded = ticks_needed * Decimal(str(tick_size))
    print(pending_order_price_rounded)

    return float(pending_order_price_rounded)


class TestAdjustLtp(unittest.TestCase):

    def test_adjust_ltp(self):
        buy_price = 100.05
        buffer_percent = 2
        tick_size = 0.05
        expected_result = 98.05  # Adjusted buy price should be 100.5

        result = adjust_ltp(buy_price, -1*buffer_percent, tick_size)

        self.assertAlmostEqual(result, expected_result, places=2)


if __name__ == '__main__':
    unittest.main()
