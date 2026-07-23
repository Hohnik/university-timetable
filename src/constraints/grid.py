"""Shared grid math, reused across hard and soft rules."""

import itertools


def occupies(value, length):
    """Grid timeslots (day, timeslot) covered by a lecture placed at `value`."""
    day, timeslot = value
    return {(day, timeslot + k) for k in range(length)}


def blocks(a, b, la, lb):
    """True if two placements overlap in time."""
    if a[0] != b[0]:
        return False
    return a[1] < b[1] + lb and b[1] < a[1] + la


def is_parallel(a, b):
    """Parallel lab groups of one course (H5): same subject, different
    lecture, meant to run simultaneously — exempt from H1/H2/H4/H6."""
    return a["fach_id"] == b["fach_id"] and a["lv_id"] != b["lv_id"]


def lecture_pairs(lectures):
    """Yield (i, j, lecture_i, lecture_j) for every unordered pair."""
    for i, j in itertools.combinations(range(len(lectures)), 2):
        yield i, j, lectures[i], lectures[j]


def curriculum_day_timeslots(inst, solution, curriculum, day):
    """Sorted grid timeslots this curriculum sits in lecture for, on this day."""
    return sorted({
        ts for i, lec in enumerate(inst.lectures) if curriculum in lec["curricula"]
        for d, ts in occupies(solution[i], lec["length"]) if d == day
    })
