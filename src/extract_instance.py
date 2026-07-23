"""Extract a scheduling problem instance from the scraped Primuss timetable data.

Input : raw/groups/*.json  (real HS Landshut events, from fetch_primuss.py)
        raw/tree.json      (faculty -> program -> study group mapping)
Output: data/instance.json (clean problem instance for the solver)

The scraped data is a *solved* timetable: every event already has a day, time
and room. This script throws that solution away and keeps only the *problem*:
which sessions exist, who teaches them, which cohorts attend, how long they
are, plus the aggregate report (professors, courses, hours/week) needed for
resourcing. The original placement is kept separately as `published_solution`
so the produced schedule can be compared against the real one.

Key transformations
-------------------
1. DEDUPE.       The same lesson appears once per study group that attends it
                 (24722 raw events -> 14801 distinct). Collapsed on
                 (lv_id, dtstart), remembering the set of attending groups.
2. SESSIONISE.   Individual calendar dates are collapsed into weekly sessions
                 keyed by (lv_id, weekday, start, end). A session recurring 15x
                 over the semester is one thing to schedule, not 15.
3. GRID.         Real start times snap onto the HS Landshut 45-minute block
                 grid; a longer block occupies several consecutive slots.
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

FACULTY = "IF"

# --- The HS Landshut teaching grid, at 45-minute BLOCK resolution ----------
# The day is a sequence of 45-minute blocks with a 15-minute break after every
# two, and a 50-minute lunch (12:00-12:50) after the fourth. A lecture spans
# one or more consecutive blocks -- a single 45-minute talk is 1 block, a
# standard 90-minute lecture 2, a long practical 4.
BLOCKS = [
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
GRID = BLOCKS             # kept under the old name for the solver
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

# Minimum times a session must recur to count as a regular weekly session.
# Filters out one-off block events, exam dates and excursions.
MIN_OCCURRENCES = 4

# One grid block is 45 minutes.
BLOCK_HOURS = 0.75


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_group_meta():
    """stgru -> (faculty, degree, program, label)"""
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
    """Collapse the same lesson appearing in several study groups' files."""
    merged = {}
    for e in events:
        key = (e["lv_id"], e["dtstart"])
        entry = merged.setdefault(
            key, {k: v for k, v in e.items() if k != "_stgru"} | {"_groups": set()})
        entry["_groups"].add(e["_stgru"])
    return list(merged.values())


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def lecturers(event):
    """['Kromer, Eduard', 'Remmele, Stefanie'] -- 'NN,' means 'not yet assigned'."""
    m = re.search(r"Dozent:\s*(.*)", event.get("description", ""))
    if not m:
        return []
    names = [p.strip() for p in m.group(1).split(";") if p.strip()]
    return [n for n in names if n not in ("NN,", "NN")]


def _to_min(hhmm):
    return int(hhmm[:2]) * 60 + int(hhmm[3:5])


def block_of_start(hhmm, tol=25):
    """Nearest block whose START matches this time, or None if too far off."""
    m = _to_min(hhmm)
    best = min(range(len(BLOCKS)), key=lambda i: abs(m - _to_min(BLOCKS[i][0])))
    return best if abs(m - _to_min(BLOCKS[best][0])) <= tol else None


def block_of_end(hhmm):
    """Nearest block whose END matches this time."""
    m = _to_min(hhmm)
    return min(range(len(BLOCKS)), key=lambda i: abs(m - _to_min(BLOCKS[i][1])))


def block_span(start_hhmm, end_hhmm):
    """(start_block, length_in_blocks) for a session, or None if unplaceable.

    Length is read directly from the clock: how many blocks lie between the
    session's start and end. Internal short breaks are absorbed (a 4-block
    lecture legitimately runs across the 10:15-10:30 break), so a 08:45-12:00
    block comes out as 4 blocks, an 08:45-10:15 lecture as 2, a lone 45-minute
    talk as 1.
    """
    sb = block_of_start(start_hhmm)
    if sb is None:
        return None
    eb = block_of_end(end_hhmm)
    return sb, max(1, eb - sb + 1)


# ---------------------------------------------------------------------------
# Sessionising
# ---------------------------------------------------------------------------

def build_sessions(events, group_meta, faculty):
    """Collapse dated events into recurring weekly sessions."""
    wanted = {g for g, m in group_meta.items() if m["faculty"] == faculty}
    buckets = collections.defaultdict(list)

    for e in events:
        groups = e["_groups"] & wanted
        if not groups:
            continue
        start = dt.datetime.fromisoformat(e["dtstart"])
        day = start.strftime("%a")
        if day not in DAYS:
            continue                      # a handful of Sat/Sun events
        span = block_span(e["dtstart"][11:16], e["dtend"][11:16])
        if span is None:
            continue                      # off-grid one-offs
        si, length = span
        key = (e["lv_id"], day, si, length)
        buckets[key].append((e, groups))

    sessions = []
    for (lv_id, day, si, length), items in buckets.items():
        if len(items) < MIN_OCCURRENCES:
            continue                      # block events, exams, excursions
        sample = items[0][0]
        profs = sorted({p for e, _ in items for p in lecturers(e)})
        groups = sorted({g for _, gs in items for g in gs})
        sessions.append({
            "id": f"{lv_id}-{day}-{si}",
            "lv_id": lv_id,
            "fach_id": sample["fach_id"],
            "course": sample["fach_name"],
            "short": sample["summary"],
            "lecturers": profs,
            "groups": groups,
            "length": length,
            "rhythm": sample.get("rhythmus"),
            "occurrences": len(items),
            # the real placement, kept for comparison only:
            "published": {"day": day, "slot": si},
        })
    return sessions


# ---------------------------------------------------------------------------
# Lecturer availability, derived from the published timetable
# ---------------------------------------------------------------------------

def lecturer_availability(sessions):
    """
    A lecturer who never appears on a given weekday across the whole semester
    is treated as unavailable that day. Many HS Landshut lecturers are
    part-time practitioners, so this is a real and quite binding constraint.
    """
    days = collections.defaultdict(set)
    for s in sessions:
        for p in s["lecturers"]:
            days[p].add(s["published"]["day"])
    return {p: [d for d in DAYS if d in ds] for p, ds in days.items()}


# ---------------------------------------------------------------------------
# Aggregate report: professors, courses, hours/week
# ---------------------------------------------------------------------------

def weekly_blocks(session):
    """A session's length in blocks, halved if it only runs every other week
    (rhythmus 14 = fortnightly)."""
    return session["length"] * (0.5 if session["rhythm"] == "14" else 1)


def report(sessions):
    """The scheduling-relevant aggregates: who teaches what, and how much."""
    professors = sorted({p for s in sessions for p in s["lecturers"]})
    courses = sorted({s["course"] for s in sessions})
    return {
        "professors": professors,
        "courses": courses,
        "course_hours_per_week": {
            c: sum(weekly_blocks(s) for s in sessions if s["course"] == c) * BLOCK_HOURS
            for c in courses},
        "professor_hours_per_week": {
            p: sum(weekly_blocks(s) for s in sessions if p in s["lecturers"]) * BLOCK_HOURS
            for p in professors},
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    group_meta = load_group_meta()
    events = dedupe(load_events())
    sessions = build_sessions(events, group_meta, FACULTY)
    avail = lecturer_availability(sessions)

    attending = {g for s in sessions for g in s["groups"]}
    cohorts = {
        g: group_meta[g] for g in attending
        if group_meta[g]["faculty"] == FACULTY and group_meta[g]["label"] != "Fakultät"
    }
    cohorts = dict(sorted(cohorts.items(), key=lambda kv: kv[1]["label"]))

    summary = report(sessions)
    instance = {
        "meta": {
            "source": "HS Landshut Primuss",
            "faculty": FACULTY,
            "days": DAYS,
            "grid": GRID,
        },
        "cohorts": cohorts,
        "lecturer_days": dict(sorted(avail.items())),
        "sessions": sorted(sessions, key=lambda s: s["id"]),
        "summary": summary,
    }

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(instance, indent=1, ensure_ascii=False))

    print(f"faculty {FACULTY}: {len(sessions)} weekly sessions, "
          f"{len({s['fach_id'] for s in sessions})} courses, "
          f"{len(cohorts)} cohorts, {len(avail)} lecturers")
    print(f"\n{len(summary['professors'])} professors, {len(summary['courses'])} courses")
    print("\nprofessor hours/week (top 10):")
    for p, h in sorted(summary["professor_hours_per_week"].items(), key=lambda kv: -kv[1])[:10]:
        print(f"  {p:30} {h:.2f}h")
    print(f"\nwritten to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
