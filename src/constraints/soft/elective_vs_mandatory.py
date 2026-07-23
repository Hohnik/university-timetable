"""S8: an elective overlapping a mandatory class of a cohort that could take it.

Not forbidden — the SPO explicitly doesn't guarantee elective clash-freedom —
but a student picking that elective would lose a mandatory class, so this
pushes the timetable toward giving every elective a mandatory-free window.
"""
from .. import grid


def conflict_cohorts(a, b):
    ra, rb = set(a["required_by"]), set(b["required_by"])
    ga, gb = set(a["groups"]), set(b["groups"])
    return ((ra & gb) | (rb & ga)) - (ra & rb)


def penalties(inst, solution):
    pen = []
    for i, j, a, b in grid.session_pairs(inst.sessions):
        if not grid.blocks(solution[i], solution[j], a["length"], b["length"]):
            continue
        for g in conflict_cohorts(a, b):
            pen.append((7, f"S8 elective vs mandatory: {inst.label(g)} {a['short']}/{b['short']}"))
    return pen
