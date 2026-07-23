"""S2: idle gaps within a cohort's day, priced exponentially.

One dead block is a nuisance; several in a row means going home and coming
back, which is disproportionately worse.
"""
from .. import grid


def penalties(inst, solution):
    pen = []
    for g in inst.cohorts:
        for day in inst.days:
            slots = grid.cohort_day_slots(inst, solution, g, day)
            if not slots:
                continue
            span = set(range(slots[0], slots[-1] + 1))
            gaps = len(span - set(slots))
            if gaps:
                pen.append((2 ** gaps,
                            f"S2 gap: {inst.label(g)} {gaps} idle block(s) {day}"))
    return pen
