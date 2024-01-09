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

    @staticmethod
    def calc_perc(smaller=0, bigger=0, precision=2):
        if bigger == 0 or smaller == 0:
            return 0
        else:
            return round(smaller / bigger * 100, precision)
