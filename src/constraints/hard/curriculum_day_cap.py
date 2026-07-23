"""H8 (optional): cap a curriculum's total daily teaching load.

n-ary over all of a curriculum's lectures — exactly the shape that makes
backtracking degenerate into generate-and-test, but MinConflicts (local
search) copes fine with it.
"""
import collections

from .. import grid
from ..limits import MAX_PER_DAY


def curriculum_lectures(inst, curriculum):
    return [i for i, lec in enumerate(inst.lectures) if curriculum in lec["curricula"]]


def build_constraint(inst, idx):
    lens = [inst.lectures[i]["length"] for i in idx]

    def check(*vals):
        per_day = collections.defaultdict(set)
        for v, ln in zip(vals, lens):
            for day, timeslot in grid.occupies(v, ln):
                per_day[day].add(timeslot)
        return all(len(timeslots) <= MAX_PER_DAY for timeslots in per_day.values())

    return check
