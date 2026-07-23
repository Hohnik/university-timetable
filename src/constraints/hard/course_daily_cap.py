"""H4: cap how much of one course may land on a single day, applied per (curriculum, course).

Identical course names recur independently across five programs (e.g.
"Programmieren II" exists once per program) — capping by course name alone
merges them into one shared course capped at two timeslots a week for the
whole faculty, which is instantly infeasible. A lecture cannot be split, so a
single lecture already longer than the cap (two exist in the data, ~5h
blocks) may stand alone; the cap then only stops anything else joining it
that day.
"""
import collections

from .. import grid
from ..limits import MAX_COURSE_TIMESLOTS_PER_DAY


def applies(a, b):
    return (a["course_key"] == b["course_key"] and not grid.is_parallel(a, b)
            and set(a["curricula"]) & set(b["curricula"]))


def cap_for(*lengths):
    return max(MAX_COURSE_TIMESLOTS_PER_DAY, *lengths)


def pairwise(x, y, la, lb, cap):
    if x[0] != y[0]:
        return True
    return la + lb <= cap


def groups_by_course(inst):
    """(curriculum, course_key) -> lecture indices. Feeds the exact n-ary check
    below, needed once 3+ lectures of one course can pile onto a curriculum's
    day — a pairwise sum can't see that on its own."""
    bycourse = collections.defaultdict(list)
    for i, lec in enumerate(inst.lectures):
        for g in lec["curricula"]:
            bycourse[(g, lec["course_key"])].append(i)
    return bycourse


def n_ary_constraint(inst, idx):
    lens = [inst.lectures[i]["length"] for i in idx]
    fach = [inst.lectures[i]["fach_id"] for i in idx]
    cap = cap_for(*lens)

    def check(*vals):
        per_day = collections.defaultdict(set)
        for v, ln, f in zip(vals, lens, fach):
            for day, timeslot in grid.occupies(v, ln):
                per_day[day].add((timeslot, f))   # parallel groups share timeslots
        return all(len(cells) <= cap for cells in per_day.values())

    return check


def violations(inst, idx, solution):
    """(day, timeslot_count) for every day this (curriculum, course) group exceeds its cap."""
    lens = [inst.lectures[i]["length"] for i in idx]
    cap = cap_for(*lens)
    per_day = collections.defaultdict(set)
    for i in idx:
        for day, timeslot in grid.occupies(solution[i], inst.lectures[i]["length"]):
            per_day[day].add((timeslot, inst.lectures[i]["fach_id"]))
    return [(day, len(cells)) for day, cells in per_day.items() if len(cells) > cap]
