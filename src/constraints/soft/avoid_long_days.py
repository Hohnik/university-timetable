"""S6: cohort days longer than the daily cap are penalized progressively."""
from .. import grid
from ..limits import MAX_PER_DAY


def penalties(inst, solution):
    pen = []
    for g in inst.cohorts:
        for day in inst.days:
            slots = grid.cohort_day_slots(inst, solution, g, day)
            if len(slots) > MAX_PER_DAY:
                over = len(slots) - MAX_PER_DAY
                pen.append((6 * (2 ** over),
                            f"S6 long day: {inst.label(g)} {len(slots)} slots {day}"))
    return pen
