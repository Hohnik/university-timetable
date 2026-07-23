"""H8 (optional): cap a cohort's total daily teaching load.

n-ary over all of a cohort's sessions — exactly the shape that makes
backtracking degenerate into generate-and-test, but MinConflicts (local
search) copes fine with it.
"""
import collections

from .. import grid
from ..limits import MAX_PER_DAY


def cohort_sessions(inst, group):
    return [i for i, s in enumerate(inst.sessions) if group in s["groups"]]


def build_constraint(inst, idx):
    lens = [inst.sessions[i]["length"] for i in idx]

    def check(*vals):
        per_day = collections.defaultdict(set)
        for v, ln in zip(vals, lens):
            for day, slot in grid.occupies(v, ln):
                per_day[day].add(slot)
        return all(len(slots) <= MAX_PER_DAY for slots in per_day.values())

    return check
