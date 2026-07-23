"""S8: an elective overlapping a mandatory class of a curriculum that could take it.

Not forbidden — the SPO explicitly doesn't guarantee elective clash-freedom —
but a student picking that elective would lose a mandatory class, so this
pushes the timetable toward giving every elective a mandatory-free window.
"""
from .. import grid


def conflict_curricula(a, b):
    ra, rb = set(a["required_by"]), set(b["required_by"])
    ga, gb = set(a["curricula"]), set(b["curricula"])
    return ((ra & gb) | (rb & ga)) - (ra & rb)


def penalties(inst, solution):
    pen = []
    for i, j, a, b in grid.lecture_pairs(inst.lectures):
        if not grid.blocks(solution[i], solution[j], a["length"], b["length"]):
            continue
        for g in conflict_curricula(a, b):
            pen.append((7, f"S8 elective vs mandatory: {inst.label(g)} {a['short']}/{b['short']}"))
    return pen
