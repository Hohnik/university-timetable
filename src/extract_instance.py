"""Extract a CB-CTT scheduling problem instance from the scraped Primuss timetable data.

Input : raw/groups/*.json  (real HS Landshut events, from fetch_primuss.py)
        raw/tree.json      (faculty -> program -> study group mapping)
Output: data/instance.json (clean problem instance for the solver)

The scraped data is a *solved* timetable: every event already has a day, time
and room. This script throws that solution away and keeps only the *problem*:
which lectures exist, who teaches them (teachers), which curricula attend,
how long they are, plus the aggregate report (teachers, courses, hours/week)
needed for resourcing. The original placement is kept separately as
`published_solution` so the produced schedule can be compared against the
real one.

Key transformations
-------------------
1. DEDUPE.       The same lesson appears once per study group that attends it
                 (24722 raw events -> 14801 distinct). Collapsed on
                 (lv_id, dtstart), remembering the set of attending curricula.
2. LECTURISE.    Individual calendar dates are collapsed into weekly lectures
                 keyed by (lv_id, weekday, start, end). A lecture recurring 15x
                 over the semester is one thing to schedule, not 15.
3. GRID.         Real start times snap onto the HS Landshut 45-minute timeslot
                 grid; a longer lecture occupies several consecutive timeslots.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "raw"
OUT = ROOT / "data" / "instance.json"

FACULTIES = ["IF", "SA"]

# --- The HS Landshut teaching grid, at 45-minute TIMESLOT resolution -------
# The day is a sequence of 45-minute timeslots with a 15-minute break after
# every two, and a 50-minute lunch (12:00-12:50) after the fourth. A lecture
# spans one or more consecutive timeslots -- a single 45-minute talk is 1
# timeslot, a standard 90-minute lecture 2, a long practical 4.
TIMESLOTS = [
    ("08:45", "09:30"),   # 0
    ("09:30", "10:15"),   # 1
    # 15-min break
    ("10:30", "11:15"),   # 2
    ("11:15", "12:00"),   # 3
    # lunch 12:00-12:50
    ("12:50", "13:35"),   # 4
    ("13:35", "14:20"),   # 5
    # 15-min break
    ("14:30", "15:15"),   # 6
    ("15:15", "16:00"),   # 7
    # 15-min break
    ("16:10", "16:55"),   # 8
    ("16:55", "17:40"),   # 9
    # 15-min break
    ("17:50", "18:35"),   # 10
    ("18:35", "19:20"),   # 11
]
GRID = TIMESLOTS          # alias kept for the instance JSON's "grid" field
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

# Minimum times a lecture must recur to count as a regular weekly lecture.
# Filters out one-off block events, exam dates and excursions.
MIN_OCCURRENCES = 4

# One grid timeslot is 45 minutes.
TIMESLOT_HOURS = 0.75


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_curricula_meta():
    """stgru -> curriculum metadata (faculty, degree, program, label)."""
    tree = json.loads((DATA / "tree.json").read_text())
    meta = {}
    for fac in tree:
        for deg in fac["degrees"]:
            for prog in deg["programs"]:
                for g in prog["groups"]:
                    meta[g["stgru"]] = {
                        "faculty": fac["label"],
                        "degree": deg["label"],
                        "program": prog["name"],
                        "label": g["label"],
                    }
    return meta


def load_events():
    """All scraped events, tagged with the study group whose file they came from."""
    events = []
    for path in sorted((DATA / "groups").glob("*.json")):
        stgru = path.stem
        for e in json.loads(path.read_text()):
            e["_stgru"] = stgru
            events.append(e)
    return events


def dedupe(events):
    """Collapse the same lesson appearing in several curricula's files."""
    merged = {}
    for e in events:
        key = (e["lv_id"], e["dtstart"])
        entry = merged.setdefault(
            key, {k: v for k, v in e.items() if k != "_stgru"} | {"_curricula": set()})
        entry["_curricula"].add(e["_stgru"])
    return list(merged.values())


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def teachers(event):
    """['Kromer, Eduard', 'Remmele, Stefanie'] -- 'NN,' means 'not yet assigned'."""
    m = re.search(r"Dozent:\s*(.*)", event.get("description", ""))
    if not m:
        return []
    names = [p.strip() for p in m.group(1).split(";") if p.strip()]
    return [n for n in names if n not in ("NN,", "NN")]


def _to_min(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def timeslot_of_start(hhmm, tol=25):
    """Nearest timeslot whose START matches this time, or None if too far off."""
    m = _to_min(hhmm)
    best = min(range(len(TIMESLOTS)), key=lambda i: abs(m - _to_min(TIMESLOTS[i][0])))
    return best if abs(m - _to_min(TIMESLOTS[best][0])) <= tol else None


def timeslot_of_end(hhmm):
    """Nearest timeslot whose END matches this time."""
    m = _to_min(hhmm)
    return min(range(len(TIMESLOTS)), key=lambda i: abs(m - _to_min(TIMESLOTS[i][1])))


def timeslot_span(start_hhmm, end_hhmm):
    """(start_timeslot, length_in_timeslots) for a lecture, or None if unplaceable.

    Length is read directly from the clock: how many timeslots lie between the
    lecture's start and end. Internal short breaks are absorbed (a 4-timeslot
    lecture legitimately runs across the 10:15-10:30 break), so a 08:45-12:00
    lecture comes out as 4 timeslots, an 08:45-10:15 lecture as 2, a lone
    45-minute talk as 1.
    """
    sb = timeslot_of_start(start_hhmm)
    if sb is None:
        return None
    eb = timeslot_of_end(end_hhmm)
    return sb, max(1, eb - sb + 1)


# ---------------------------------------------------------------------------
# Building lectures
# ---------------------------------------------------------------------------

def build_lectures(events, curricula_meta, faculties):
    """Collapse dated events into recurring weekly lectures."""
    wanted = {g for g, m in curricula_meta.items() if m["faculty"] in faculties}
    buckets = collections.defaultdict(list)

    for e in events:
        curricula = e["_curricula"] & wanted
        if not curricula:
            continue
        start = dt.datetime.fromisoformat(e["dtstart"])
        day = start.strftime("%a")
        if day not in DAYS:
            continue                      # a handful of Sat/Sun events
        span = timeslot_span(e["dtstart"][11:16], e["dtend"][11:16])
        if span is None:
            continue                      # off-grid one-offs
        si, length = span
        key = (e["lv_id"], day, si, length)
        buckets[key].append((e, curricula))

    lectures = []
    for (lv_id, day, si, length), items in buckets.items():
        if len(items) < MIN_OCCURRENCES:
            continue                      # block events, exams, excursions
        sample = items[0][0]
        profs = sorted({p for e, _ in items for p in teachers(e)})
        curricula = sorted({g for _, gs in items for g in gs})
        lectures.append({
            "id": f"{lv_id}-{day}-{si}",
            "lv_id": lv_id,
            "fach_id": sample["fach_id"],
            "course": sample["fach_name"],
            "short": sample["summary"],
            "teachers": profs,
            "curricula": curricula,
            "length": length,
            "rhythm": sample.get("rhythmus"),
            "occurrences": len(items),
            # the real placement, kept for comparison only:
            "published": {"day": day, "timeslot": si},
        })
    return lectures


# ---------------------------------------------------------------------------
# Teacher availability, derived from the published timetable
# ---------------------------------------------------------------------------

def teacher_availability(lectures):
    """
    A teacher who never appears on a given weekday across the whole semester
    is treated as unavailable that day. Many HS Landshut teachers are
    part-time practitioners, so this is a real and quite binding constraint.
    """
    days = collections.defaultdict(set)
    for lec in lectures:
        for p in lec["teachers"]:
            days[p].add(lec["published"]["day"])
    return {p: [d for d in DAYS if d in ds] for p, ds in days.items()}


# ---------------------------------------------------------------------------
# Aggregate report: teachers, courses, hours/week
# ---------------------------------------------------------------------------

def weekly_timeslots(lecture):
    """A lecture's length in timeslots, halved if it only runs every other
    week (rhythmus 14 = fortnightly)."""
    return lecture["length"] * (0.5 if lecture["rhythm"] == "14" else 1)


def report(lectures):
    """The scheduling-relevant aggregates: who teaches what, and how much."""
    teachers_ = sorted({p for lec in lectures for p in lec["teachers"]})
    courses = sorted({lec["course"] for lec in lectures})
    return {
        "teachers": teachers_,
        "courses": courses,
        "course_hours_per_week": {
            c: sum(weekly_timeslots(lec) for lec in lectures if lec["course"] == c) * TIMESLOT_HOURS
            for c in courses},
        "teacher_hours_per_week": {
            p: sum(weekly_timeslots(lec) for lec in lectures if p in lec["teachers"]) * TIMESLOT_HOURS
            for p in teachers_},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    curricula_meta = load_curricula_meta()
    events = dedupe(load_events())
    lectures = build_lectures(events, curricula_meta, FACULTIES)
    avail = teacher_availability(lectures)

    attending = {g for lec in lectures for g in lec["curricula"]}
    curricula = {
        g: curricula_meta[g] for g in attending
        if curricula_meta[g]["faculty"] in FACULTIES and curricula_meta[g]["label"] != "Fakultät"
    }
    curricula = dict(sorted(curricula.items(), key=lambda kv: kv[1]["label"]))

    summary = report(lectures)
    instance = {
        "meta": {
            "source": "HS Landshut Primuss",
            "faculties": FACULTIES,
            "days": DAYS,
            "grid": GRID,
        },
        "curricula": curricula,
        "teacher_days": dict(sorted(avail.items())),
        "lectures": sorted(lectures, key=lambda lec: lec["id"]),
        "summary": summary,
    }

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(instance, indent=1, ensure_ascii=False))

    print(f"faculties {'+'.join(FACULTIES)}: {len(lectures)} weekly lectures, "
          f"{len({lec['fach_id'] for lec in lectures})} courses, "
          f"{len(curricula)} curricula, {len(avail)} teachers")
    print(f"\n{len(summary['teachers'])} teachers, {len(summary['courses'])} courses")
    print("\nteacher hours/week (top 10):")
    for p, h in sorted(summary["teacher_hours_per_week"].items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {p:30} {h:.2f}h")
    print(f"\nwritten to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
