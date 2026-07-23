"""H3: lecturers with enough observed teaching evidence are only scheduled on
days they're known to teach.

Availability is inferred from the published timetable ("this lecturer is
never seen on a Friday"), which makes it self-fulfilling for anyone with too
little data — 33 of 61 lecturers teach a single session, so they'd look
available exactly one day a week. Only lecturers with enough sessions to make
an absence meaningful are constrained at all.
"""
from ..limits import MIN_AVAILABILITY_EVIDENCE


def available_days(inst, session):
    """Days this session may be placed on.

    If intersecting still empties the set (co-teachers with disjoint observed
    days), the restriction is dropped rather than making the instance infeasible.
    """
    days = set(inst.days)
    for p in session["lecturers"]:
        if inst.teach_count[p] >= MIN_AVAILABILITY_EVIDENCE:
            days &= set(inst.lecturer_days.get(p, inst.days))
    return days or set(inst.days)
