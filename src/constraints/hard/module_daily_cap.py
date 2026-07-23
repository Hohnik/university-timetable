"""H4: cap how much of one subject may land on a single day, applied per (cohort, module).

Identical module names recur independently across five programs (e.g.
"Programmieren II" exists once per program) — capping by course name alone
merges them into one shared subject capped at two slots a week for the whole
faculty, which is instantly infeasible. A session cannot be split, so a
single session already longer than the cap (two exist in the data, ~5h
blocks) may stand alone; the cap then only stops anything else joining it
that day.
"""
import collections

from .. import grid
from ..limits import MAX_MODULE_BLOCKS_PER_DAY


def applies(a, b):
    return (a["module_key"] == b["module_key"] and not grid.is_parallel(a, b)
            and set(a["groups"]) & set(b["groups"]))


def cap_for(*lengths):
    return max(MAX_MODULE_BLOCKS_PER_DAY, *lengths)


def pairwise(x, y, la, lb, cap):
    if x[0] != y[0]:
        return True
    return la + lb <= cap


def groups_by_module(inst):
    """(cohort, module_key) -> session indices. Feeds the exact n-ary check
    below, needed once 3+ sessions of one module can pile onto a cohort's day
    — a pairwise sum can't see that on its own."""
    bymod = collections.defaultdict(list)
    for i, s in enumerate(inst.sessions):
        for g in s["groups"]:
            bymod[(g, s["module_key"])].append(i)
    return bymod


def n_ary_constraint(inst, idx):
    lens = [inst.sessions[i]["length"] for i in idx]
    fach = [inst.sessions[i]["fach_id"] for i in idx]
    cap = cap_for(*lens)

    def check(*vals):
        per_day = collections.defaultdict(set)
        for v, ln, f in zip(vals, lens, fach):
            for day, slot in grid.occupies(v, ln):
                per_day[day].add((slot, f))   # parallel groups share slots
        return all(len(cells) <= cap for cells in per_day.values())

    return check


def violations(inst, idx, solution):
    """(day, slot_count) for every day this (cohort, module) group exceeds its cap."""
    lens = [inst.sessions[i]["length"] for i in idx]
    cap = cap_for(*lens)
    per_day = collections.defaultdict(set)
    for i in idx:
        for day, slot in grid.occupies(solution[i], inst.sessions[i]["length"]):
            per_day[day].add((slot, inst.sessions[i]["fach_id"]))
    return [(day, len(cells)) for day, cells in per_day.items() if len(cells) > cap]
