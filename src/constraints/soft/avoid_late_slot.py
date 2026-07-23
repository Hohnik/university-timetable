"""S4: the day's last timeslot is unpopular; discourage placing lectures there."""
from ..limits import LATE_TIMESLOTS

POINTS = 6


def penalties(inst, solution):
    pen = []
    for i, lec in enumerate(inst.lectures):
        day, timeslot = solution[i]
        if set(range(timeslot, timeslot + lec["length"])) & LATE_TIMESLOTS:
            pen.append((POINTS, f"S4 late timeslot: {lec['short']} ({day})"))
    return pen
