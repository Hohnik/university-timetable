"""S7: a lecture and its practical of one course sitting apart, same day.

H6 forbids splitting the SAME teaching type; this only prices the mixed case
(lecture vs. practical), which is tolerable but not ideal.
"""
from .. import grid
from ..hard import contiguous_same_type


def penalties(inst, solution):
    pen = []
    for i, j, a, b in grid.lecture_pairs(inst.lectures):
        if a["course_key"] != b["course_key"] or a["practical"] == b["practical"]:
            continue
        x, y = solution[i], solution[j]
        if contiguous_same_type.touching(x, y, a["length"], b["length"]):
            continue
        pen.append((5, f"S7 lecture/practical apart: {a['course'][:26]} on {x[0]}"))
    return pen
