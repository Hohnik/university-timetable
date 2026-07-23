"""Shared grid math, reused across hard and soft rules."""

import itertools


def occupies(value, length):
    """Grid slots (day, slot) covered by a session placed at `value`."""
    day, slot = value
    return {(day, slot + k) for k in range(length)}


def blocks(a, b, la, lb):
    """True if two placements overlap in time."""
    if a[0] != b[0]:
        return False
    return a[1] < b[1] + lb and b[1] < a[1] + la


def is_parallel(a, b):
    """Parallel lab groups of one module (H5): same subject, different
    session, meant to run simultaneously — exempt from H1/H2/H4/H6."""
    return a["fach_id"] == b["fach_id"] and a["lv_id"] != b["lv_id"]


def session_pairs(sessions):
    """Yield (i, j, session_i, session_j) for every unordered pair."""
    for i, j in itertools.combinations(range(len(sessions)), 2):
        yield i, j, sessions[i], sessions[j]


def cohort_day_slots(inst, solution, group, day):
    """Sorted grid slots this cohort sits in session for, on this day."""
    return sorted({
        sl for i, s in enumerate(inst.sessions) if group in s["groups"]
        for d, sl in occupies(solution[i], s["length"]) if d == day
    })
