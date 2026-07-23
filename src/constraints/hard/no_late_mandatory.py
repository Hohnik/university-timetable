"""H7 (optional): keep mandatory teaching out of the day's last timeslot.

Improves soft-score quality a lot when feasible, but removes a fifth of the
week's capacity — some scopes need every timeslot, so this is tried first and
relaxed rather than applied unconditionally (see solve.search_adaptive).
"""
from ..limits import LATE_TIMESLOTS


def filter_domain(domain, length):
    """Drop placements whose lecture would land in the day's last timeslot.
    Falls back to the unfiltered domain rather than emptying it."""
    filtered = [(d, ts) for d, ts in domain
                if not (set(range(ts, ts + length)) & LATE_TIMESLOTS)]
    return filtered or domain
