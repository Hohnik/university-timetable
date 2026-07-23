"""H6: a course's same-teaching-type lectures sharing a day must be contiguous.

No maths lecture at 08:45, other courses, maths again at 16:10. A lecture and
its practical may legitimately sit apart on the same day (see
soft.keep_lecture_practical_together) — this only applies when both lectures
are of the same teaching type.
"""
from .. import grid


def applies(a, b):
    return (a["course_key"] == b["course_key"] and a["practical"] == b["practical"]
            and not grid.is_parallel(a, b) and set(a["curricula"]) & set(b["curricula"]))


def touching(x, y, la, lb):
    """True if the two placements don't collide on a day, or do and are adjacent/overlapping."""
    if x[0] != y[0]:
        return True
    ax, bx = x[1], x[1] + la
    ay, by = y[1], y[1] + lb
    if ax < by and ay < bx:
        return True                    # overlapping
    return bx == ay or by == ax        # must touch
