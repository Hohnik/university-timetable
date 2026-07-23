"""S5: reward giving a cohort a genuinely free day.

A day holding a single session is the worst possible use of a student's week
— they commute in for 90 minutes, so many just skip it. Consolidating those
sessions is what actually frees up whole days, which is the outcome worth
rewarding; a week with zero free days at all is penalized too.
"""
from .. import grid

NEAR_EMPTY = 14
NO_FREE_DAY = 20


def penalties(inst, solution):
    pen = []
    for g in inst.cohorts:
        free_days = 0
        for day in inst.days:
            slots = grid.cohort_day_slots(inst, solution, g, day)
            if not slots:
                free_days += 1
            elif len(slots) == 1:
                pen.append((NEAR_EMPTY, f"S5 near-empty day: {inst.label(g)} 1 slot on {day}"))
        if free_days == 0:
            pen.append((NO_FREE_DAY, f"S5 no free day: {inst.label(g)} teaches 5/5 days"))
    return pen
