"""S7: a lecture and its practical of one subject sitting apart, same day.

H6 forbids splitting the SAME teaching type; this only prices the mixed case
(lecture vs. practical), which is tolerable but not ideal.
"""
from .. import grid
from ..hard import contiguous_same_type


def penalties(inst, solution):
    pen = []
    for i, j, a, b in grid.session_pairs(inst.sessions):
        if a["module_key"] != b["module_key"] or a["practical"] == b["practical"]:
            continue
        x, y = solution[i], solution[j]
        if contiguous_same_type.touching(x, y, a["length"], b["length"]):
            continue
        pen.append((5, f"S7 lecture/practical apart: {a['course'][:26]} on {x[0]}"))
    return pen
