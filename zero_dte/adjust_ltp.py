import unittest


def adjust_ltp(current_ltp, buffer_percentage, tick_size, dir=1):
    # Calculate the buffer amount based on the percentage.
    buffer_amount = (buffer_percentage / 100) * current_ltp

    # Determine the adjustment direction (addition or subtraction).
    if dir == 1:
        adjusted_ltp = current_ltp + buffer_amount
    elif dir == -1:
        adjusted_ltp = current_ltp - buffer_amount
    else:
        raise ValueError(
            "Invalid 'dir' value. Use 1 for addition or -1 for subtraction.")

    # Ensure the adjusted LTP aligns with the tick size.
    adjusted_ltp = round(adjusted_ltp / tick_size) * tick_size

    return adjusted_ltp


class TestAdjustLTP(unittest.TestCase):
    def test_add_buffer(self):
        current_ltp = 1000
        buffer_percentage = 0.5
        tick_size = 1
        adjusted_ltp = adjust_ltp(
            current_ltp, buffer_percentage, tick_size, dir=1)
        self.assertAlmostEqual(adjusted_ltp, 1005, places=2)

    def test_subtract_buffer(self):
        current_ltp = 100.0
        buffer_percentage = 0.05
        tick_size = 0.05
        adjusted_ltp = adjust_ltp(
            current_ltp, buffer_percentage, tick_size, dir=-1)
        self.assertAlmostEqual(adjusted_ltp, 99.95, places=2)


if __name__ == '__main__':
    unittest.main()
