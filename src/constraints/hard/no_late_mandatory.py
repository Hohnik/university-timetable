"""H7 (optional): keep mandatory teaching out of the day's last slot.

Improves soft-score quality a lot when feasible, but removes a fifth of the
week's capacity — some scopes need every slot, so this is tried first and
relaxed rather than applied unconditionally (see solve.search_adaptive).
"""
from ..limits import LATE_BLOCKS


def filter_domain(domain, length):
    """Drop placements whose session would land in the day's last slot.
    Falls back to the unfiltered domain rather than emptying it."""
    filtered = [(d, sl) for d, sl in domain
                if not (set(range(sl, sl + length)) & LATE_BLOCKS)]
    return filtered or domain
