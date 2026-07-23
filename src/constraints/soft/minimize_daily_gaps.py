"""S2: idle timeslots within a curriculum's day, priced exponentially.

One dead timeslot is a nuisance; several in a row means going home and coming
back, which is disproportionately worse.
"""
from .. import grid


def penalties(inst, solution):
    pen = []
    for g in inst.curricula:
        for day in inst.days:
            timeslots = grid.curriculum_day_timeslots(inst, solution, g, day)
            if not timeslots:
                continue
            span = set(range(timeslots[0], timeslots[-1] + 1))
            gaps = len(span - set(timeslots))
            if gaps:
                pen.append((2 ** gaps,
                            f"S2 gap: {inst.label(g)} {gaps} idle timeslot(s) {day}"))
    return pen
