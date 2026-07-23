"""H3: teachers with enough observed teaching evidence are only scheduled on
days they're known to teach.

Availability is inferred from the published timetable ("this teacher is
never seen on a Friday"), which makes it self-fulfilling for anyone with too
little data — 33 of 61 teachers teach a single lecture, so they'd look
available exactly one day a week. Only teachers with enough lectures to make
an absence meaningful are constrained at all.
"""
from ..limits import MIN_AVAILABILITY_EVIDENCE


def available_days(inst, lecture):
    """Days this lecture may be placed on.

    If intersecting still empties the set (co-teachers with disjoint observed
    days), the restriction is dropped rather than making the instance infeasible.
    """
    days = set(inst.days)
    for p in lecture["teachers"]:
        if inst.teach_count[p] >= MIN_AVAILABILITY_EVIDENCE:
            days &= set(inst.teacher_days.get(p, inst.days))
    return days or set(inst.days)
