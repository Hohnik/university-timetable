"""S4: the day's last slot is unpopular; discourage placing sessions there."""
from ..limits import LATE_BLOCKS

POINTS = 6


def penalties(inst, solution):
    pen = []
    for i, s in enumerate(inst.sessions):
        day, slot = solution[i]
        if set(range(slot, slot + s["length"])) & LATE_BLOCKS:
            pen.append((POINTS, f"S4 late slot: {s['short']} ({day})"))
    return pen
