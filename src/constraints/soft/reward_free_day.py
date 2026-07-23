"""S5: reward giving a curriculum a genuinely free day.

A day holding a single lecture is the worst possible use of a student's week
— they commute in for 90 minutes, so many just skip it. Consolidating those
lectures is what actually frees up whole days, which is the outcome worth
rewarding; a week with zero free days at all is penalized too.
"""
from .. import grid

NEAR_EMPTY = 14
NO_FREE_DAY = 20


def penalties(inst, solution):
    pen = []
    for g in inst.curricula:
        free_days = 0
        for day in inst.days:
            timeslots = grid.curriculum_day_timeslots(inst, solution, g, day)
            if not timeslots:
                free_days += 1
            elif len(timeslots) == 1:
                pen.append((NEAR_EMPTY, f"S5 near-empty day: {inst.label(g)} 1 timeslot on {day}"))
        if free_days == 0:
            pen.append((NO_FREE_DAY, f"S5 no free day: {inst.label(g)} teaches 5/5 days"))
    return pen
