from typing import Literal, Tuple, Dict
from constants import base
from utilities.list_of_dict import sort, get_val_and_pos
import re


def adjust_highest_ltp(positions: list[dict],
                       target_value: int,
                       contains: Literal["C", "P"],
                       tag: str
                       ):
    positions = sort(positions, "last_price", True)
    contains = base["EXPIRY"] + contains
    for entry in positions:
        if entry["quantity"] < 0 and re.search(
            re.escape(contains), entry["symbol"]
        ):
            val_for_this, pos = get_val_and_pos(
                entry, target_value, base['LOT_SIZE'], tag
            )
            return val_for_this, pos
    return 0, {}


def reduce_value(positions, target_value: int,
                 contains: Literal["C", "P"], tag):
    # arrange the positions starting from highest ltp
    positions = sort(positions, "last_price", is_desc=True)
    # initial an empty list
    lst = []
    # process the position list one at a time
    for entry in positions:
        if (
            # is the position sell and target value is positive
            entry["quantity"] < 0 and target_value > 0
            # is the position our trading symbol
            and re.search(
                re.escape(base["EXPIRY"] + contains), entry["symbol"]
            )
        ):
            val_for_this, pos = get_val_and_pos(
                entry, target_value, base['LOT_SIZE'], tag
            )
            # reduced that much value from the initial target
            target_value -= val_for_this
            # add to the main list
            lst.append(pos)
    return target_value, lst


def is_above_highest_ltp(positions, contains: Literal["C", "P"]) -> bool:
    if any(
        re.search(re.escape(base["EXPIRY"] + contains), pos["symbol"])
        and pos["quantity"] < 0
        and pos["last_price"] > base["MAX_SOLD_LTP"]
        for pos in positions
    ):
        return True
    return False


def close_profiting_position(positions, tag: str) -> Tuple[int, Dict]:
    for entry in positions:
        if (
            entry["quantity"] < 0 and
            re.search(
                re.escape(base["EXPIRY"]), entry["symbol"])
            and entry["last_price"] < base["COVER_FOR_PROFIT"]
        ):
            qty = abs(entry["quantity"])
            val_for_this = base['LOT_SIZE'] * entry["last_price"] * qty
            pos = {}
            pos["symbol"] = entry["symbol"]
            pos["quantity"] = qty
            pos["side"] = "B"
            pos["tag"] = tag
            return val_for_this, pos
    return 0, {}


if __name__ == "__main__":

    # Sample data
    sample_data = [
        {"symbol": "BANKNIFTY14FEB24C24500", "quantity": 50,
            "last_price": 333.12, "value": -2000},
        {"symbol": "BANKNIFTY14FEB24P25500", "quantity": -
            500, "last_price": 300, "value": -150000},
        {"symbol": "BANKNIFTY14FEB24C26600", "quantity": 500,
            "last_price": 111.01, "value": 1800},
        {"symbol": "BANKNIFTY14FEB24P27000", "quantity": 500,
            "last_price": 111.03, "value": -5000},
    ]
    target_value = 1000

    val, pos = adjust_highest_ltp(sample_data, target_value, "C", "test")
    print(f'{val = }, "\n", {pos = }')

    val, pos = reduce_value(sample_data, target_value, "C", "test")
    print(f'reduce value {val = }, "\n", {pos = }')

    val, pos = close_profiting_position(sample_data, target_value, "test")
    print(f'{val = }, "\n", {pos = }')
