from constants import snse
from pprint import pprint as prn


class Utils:

    @staticmethod
    def qty_from_perc(**snse):
        """
            calculate quantity from percentage,
            maximum allowed quantity and lot size
        """
        qty = snse['ENTRY_PERC'] / 100 * snse['MAX_QTY']
        snse['entry_qty'] = (qty / snse['LOT_SIZE']) * snse['LOT_SIZE']
        return snse

    @staticmethod
    def place_order(*lst, **snse):
    """
            places order for based on argument
            entry, pyramid etc
        """
    return ["call", "put"]

    @staticmethod
    def update(**snse):
        """
            update snse with current m2m and 
            max and min m2m so far with a map 
            of positions
        """
    def is_pyramid(**postions):
        return True


snse = Utils.qty_from_perc(**snse)
lst = ['c', 'entry']
snse = Utils.place_order(*lst, **snse)
lst = ['p', 'entry']
snse = Utils.place_order(*lst, **snse)
while True:
    snse = update(snse):
