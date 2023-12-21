class Adjustment:

    DECLINE = 0.25

    def __init__(self,
                 diff_threshold: float,
                 multiplier: int,
                 max_qty: int,
                 admoun
                 ):
        self.above = multiplier * diff_threshold
        self.below = multiplier * -1 * diff_threshold
        self.max_qty = max_qty

    def mode(self, ratio: float):
        """ mode return the direction of adjustment to be made """
        if ratio > self.above:
            return "C"
        elif ratio < self.below:
            return "P"
        return False

    def is_declined(self, decline: float):
        return decline > self.DECLINE

    def is_pnl_negative(self, pnl: float):
        return pnl < 0
