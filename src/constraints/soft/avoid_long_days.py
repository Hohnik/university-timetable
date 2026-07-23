"""S6: curriculum days longer than the daily cap are penalized progressively."""
from .. import grid
from ..limits import MAX_PER_DAY


def penalties(inst, solution):
    pen = []
    for g in inst.curricula:
        for day in inst.days:
            timeslots = grid.curriculum_day_timeslots(inst, solution, g, day)
            if len(timeslots) > MAX_PER_DAY:
                over = len(timeslots) - MAX_PER_DAY
                pen.append((6 * (2 ** over),
                            f"S6 long day: {inst.label(g)} {len(timeslots)} timeslots {day}"))
    return pen
