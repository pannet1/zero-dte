class Digits:
    @staticmethod
    def qty_from_perc(**snse):
        """
        calculate quantity from percentage,
        maximum allowed quantity and lot size
        """
        qty = snse["ENTRY_PERC"] / 100 * snse["MAX_QTY"]
        snse["entry_qty"] = (qty / snse["LOT_SIZE"]) * snse["LOT_SIZE"]
        return snse
