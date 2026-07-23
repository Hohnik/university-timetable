"""Solve the HS Landshut timetabling instance with `python-constraint`.

One variable per weekly SESSION, value = (day, first 45-minute block). Rooms
are not modeled — assigning them is a comparatively easy post-processing step
(bipartite matching per timeslot), left for later. See constraints.md for the
hard/soft rule catalogue; each rule lives in constraints/hard/ or
constraints/soft/, one file per rule.

Usage
-----
    uv run src/solve.py                       # semester 2, all programs
    uv run src/solve.py --semester 4
    uv run src/solve.py --faculty              # every session, all semesters
    uv run src/solve.py --published            # score the real published timetable
    uv run src/solve.py --solver minconflicts
"""

from __future__ import annotations

import argparse
import collections
import random
import re
import time

import constraint as C
from constraint import Problem

import curriculum as CU
from constraints import grid, hard, limits, soft
from instance import Instance

# ---------------------------------------------------------------------------
# Hard constraints
# ---------------------------------------------------------------------------


def build_problem(inst: Instance, rng=None, solver=None,
                  hard_long_day=False, hard_no_late_mandatory=False):
    problem = Problem(solver) if solver is not None else Problem()
    n_slots = len(inst.grid)

    for i, s in enumerate(inst.sessions):
        length = s["length"]
        allowed = inst.available_days(s)                                     # H3
        # A session may run from before the lunch break to after it — a long
        # practical scheduled 10:30-14:20 is legitimate, students simply take
        # their lunch within it. Nothing about lunch is filtered here.
        domain = [(day, slot)
                  for day in inst.days if day in allowed
                  for slot in range(n_slots - length + 1)]

        if hard_no_late_mandatory and s["required_by"]:
            domain = hard.no_late_mandatory.filter_domain(domain, length)     # H7

        if rng:
            rng.shuffle(domain)
        problem.addVariable(i, domain)

    for i, j, a, b in grid.session_pairs(inst.sessions):
        la, lb = a["length"], b["length"]

        if not grid.is_parallel(a, b):                                       # H5 exemption
            clash_cohorts = hard.cohort_no_overlap.conflicts(a, b)            # H1
            clash_prof = bool(hard.lecturer_no_overlap.conflicts(a, b))       # H2
            if clash_cohorts or clash_prof:
                problem.addConstraint(
                    lambda x, y, la=la, lb=lb: not grid.blocks(x, y, la, lb), (i, j))

        if hard.module_daily_cap.applies(a, b):                               # H4
            cap = hard.module_daily_cap.cap_for(la, lb)
            problem.addConstraint(
                lambda x, y, la=la, lb=lb, cap=cap:
                    hard.module_daily_cap.pairwise(x, y, la, lb, cap), (i, j))

        if hard.contiguous_same_type.applies(a, b):                           # H6
            problem.addConstraint(
                lambda x, y, la=la, lb=lb:
                    hard.contiguous_same_type.touching(x, y, la, lb), (i, j))

    # H4 (exact): modules with 3+ sessions need an n-ary check, since pairwise
    # sums can't see three separate 1-slot sessions piling onto one day.
    for idx in hard.module_daily_cap.groups_by_module(inst).values():
        if len(idx) >= 3:
            problem.addConstraint(hard.module_daily_cap.n_ary_constraint(inst, idx), idx)

    # H8 (optional): n-ary over a whole cohort's sessions — the shape that
    # makes backtracking degenerate into generate-and-test, but MinConflicts
    # copes.
    if hard_long_day:
        for g in inst.cohorts:
            idx = hard.cohort_day_cap.cohort_sessions(inst, g)
            if len(idx) > limits.MAX_PER_DAY:
                problem.addConstraint(hard.cohort_day_cap.build_constraint(inst, idx), idx)

    return problem


# ---------------------------------------------------------------------------
# Soft constraints
# ---------------------------------------------------------------------------


def soft_score(inst: Instance, solution):
    pen = [p for rule in soft.RULES for p in rule(inst, solution)]
    return sum(p for p, _ in pen), pen


# ---------------------------------------------------------------------------
# Independent hard-constraint validator
# ---------------------------------------------------------------------------


def validate(inst: Instance, solution):
    errors = []
    S = inst.sessions

    for i, s in enumerate(S):
        day, _slot = solution[i]
        if day not in inst.available_days(s):
            errors.append(f"H3 availability: {s['short']} on {day}")

    for i, j, a, b in grid.session_pairs(S):
        if grid.is_parallel(a, b):
            continue                                                          # H5
        if not grid.blocks(solution[i], solution[j], a["length"], b["length"]):
            continue
        if hard.cohort_no_overlap.conflicts(a, b):
            errors.append(f"H1 mandatory clash: {a['short']} / {b['short']}")
        if hard.lecturer_no_overlap.conflicts(a, b):
            errors.append(f"H2 lecturer clash: {a['short']} / {b['short']}")

    for i, j, a, b in grid.session_pairs(S):
        if not hard.contiguous_same_type.applies(a, b):
            continue
        if not hard.contiguous_same_type.touching(solution[i], solution[j], a["length"], b["length"]):
            errors.append(f"H6 split lecture: {a['course'][:28]} twice on {solution[i][0]}")

    for (g, key), idx in hard.module_daily_cap.groups_by_module(inst).items():
        for day, count in hard.module_daily_cap.violations(inst, idx, solution):
            errors.append(f"H4 block too long: {inst.label(g)} {key[:26]} {count} slots on {day}")

    return errors


# ---------------------------------------------------------------------------
# SWS budget check (diagnostic, from the SPO)
# ---------------------------------------------------------------------------

def student_slots(inst: Instance, group):
    """Slots ONE student of this cohort actually sits through in a week.

    Summing raw sessions overstates the load by ~50%, for two reasons that
    both had to be handled before the SPO's SWS figures could be matched:

      * PARALLEL GROUPS — a Praktikum offered to several lab groups appears
        once per group in the data, but a student attends one. Collapsed by
        taking a single representative lv_id per module (fach_id).

      * RHYTHM — `rhythmus 14` means fortnightly. Such a session averages
        half its length per week. And where two fortnightly sessions share
        an lv_id, they are alternating halves of one group (occurrences 7
        and 8 over a 15-week semester), so a student attends one, not both.

    Verified against the SPO: this brings IF2 from a nonsensical 38 SWS to 22
    against a prescribed 26, the remainder being electives not counted here.
    """
    byfach = collections.defaultdict(lambda: collections.defaultdict(list))
    for s in inst.sessions:
        if group in s["required_by"]:
            byfach[s["fach_id"]][s["lv_id"]].append(s)

    total = 0.0
    for lvs in byfach.values():
        best = 0.0
        for sessions in lvs.values():
            weekly = sum(s["length"] for s in sessions if s["rhythm"] != "14")
            fortnightly = [s["length"] for s in sessions if s["rhythm"] == "14"]
            weekly += max(fortnightly) * 0.5 if fortnightly else 0
            best = max(best, weekly)
        total += best
    return total


def sws_report(inst: Instance):
    """Compare a student's weekly load against the SWS the SPO prescribes.

    One 90-minute grid slot = 2 SWS.
    """
    rows = []
    for g, c in inst.cohorts.items():
        m = re.search(r"(\d)", c["label"])
        sem = int(m.group(1)) if m else None
        want = CU.expected_sws(c["program"], sem)
        if not want:
            continue
        rows.append((c["label"], want, student_slots(inst, g) * 2))
    return rows


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

SOLVERS = {
    "backtracking": lambda: C.BacktrackingSolver(),
    "forwardcheck": lambda: C.BacktrackingSolver(forwardcheck=True),
    "recursive": lambda: C.RecursiveBacktrackingSolver(),
    "minconflicts": lambda: C.MinConflictsSolver(),
}


def search_adaptive(inst: Instance, seconds, solver="minconflicts"):
    """Try the strictest model first, relax if it proves unsatisfiable.

    Banning compulsory teaching from the last slot improves quality a lot
    (soft 236 -> 140 on semester 2) but removes a fifth of the week's
    capacity. Semester 4 needs 19 of the 20 slots that remain, so the strict
    model is infeasible there. Rather than pick one globally, spend half the
    budget on the strict model and fall back if it yields nothing.
    """
    best = search(inst, seconds / 2, solver, hard_no_late_mandatory=True)
    if best[0] is not None:
        return best + ("strict",)
    relaxed = search(inst, seconds / 2, solver, hard_no_late_mandatory=False)
    return relaxed + ("relaxed",)


def search(inst: Instance, seconds, solver="minconflicts", per_restart=30,
           hard_long_day=True, hard_no_late_mandatory=True):
    """Random-restart search.

    Backtracking on this model is heavy-tailed: some variable orderings solve
    in milliseconds, others stall indefinitely. Reshuffling the domains and
    restarting is a cheap and very effective mitigation.
    """
    best = best_score = best_pen = None
    seen = restarts = 0
    deadline = time.time() + seconds

    while time.time() < deadline:
        restarts += 1
        random.seed(restarts)          # MinConflicts draws from the global RNG
        problem = build_problem(inst, rng=random.Random(restarts),
                                solver=SOLVERS[solver](),
                                hard_long_day=hard_long_day,
                                hard_no_late_mandatory=hard_no_late_mandatory)
        try:
            if solver == "minconflicts":
                # local search: one shot per restart, and it may hand back an
                # assignment that is not actually valid, so check it
                sol = problem.getSolution()
                candidates = [sol] if sol and not validate(inst, sol) else []
            else:
                candidates = []
                for sol in problem.getSolutionIter():
                    candidates.append(sol)
                    if time.time() > deadline or len(candidates) >= per_restart:
                        break
            for sol in candidates:
                seen += 1
                score, pen = soft_score(inst, sol)
                if best_score is None or score < best_score:
                    best, best_score, best_pen = sol, score, pen
        except (StopIteration, RuntimeError):
            pass
        if best is not None and time.time() > deadline:
            break
    return best, best_score, best_pen, seen, restarts


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def to_records(inst: Instance, solution) -> list[dict]:
    """One row per (session, attending group) — day/start/end/course/lecturer/
    cohort — independent of internal grid-block indices. The one interchange
    format for display, JSON, or CSV."""
    rows = []
    for i, s in enumerate(inst.sessions):
        day, slot = solution[i]
        start, _ = inst.grid[slot]
        _, end = inst.grid[slot + s["length"] - 1]
        who = ", ".join(p.split(",")[0] for p in s["lecturers"]) or "—"
        for g in s["groups"]:
            rows.append({
                "cohort": inst.label(g), "day": day, "start": start, "end": end,
                "course": s["course"], "lecturer": who,
                "kind": "mandatory" if g in s["required_by"] else "elective",
            })
    day_index = {d: i for i, d in enumerate(inst.days)}
    return sorted(rows, key=lambda r: (r["cohort"], day_index[r["day"]], r["start"]))


def print_timetable(inst: Instance, solution):
    records = to_records(inst, solution)
    for cohort in dict.fromkeys(r["cohort"] for r in records):
        print(f"\n=== {cohort} ===")
        for r in records:
            if r["cohort"] != cohort:
                continue
            kind = "  " if r["kind"] == "mandatory" else "(W)"
            print(f"  {r['day']} {r['start']}-{r['end']:<8} {kind} "
                  f"{r['course'][:36]:<36} {r['lecturer'][:20]}")


def published_solution(inst: Instance):
    return {i: (s["published"]["day"], s["published"]["slot"])
            for i, s in enumerate(inst.sessions)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--program", default=None)
    ap.add_argument("--semester", type=int, default=2)
    ap.add_argument("--faculty", action="store_true")
    ap.add_argument("--seconds", type=float, default=15)
    # MinConflicts is the default: it is local search rather than exhaustive
    # backtracking, and it solves the full faculty instance in ~0.05s where
    # backtracking does not finish at all. It is INCOMPLETE — it can return
    # an assignment that still violates constraints, and can never prove
    # infeasibility — so every result is re-checked by validate().
    ap.add_argument("--solver", default="minconflicts", choices=list(SOLVERS))
    ap.add_argument("--published", action="store_true")
    args = ap.parse_args()

    if args.faculty:
        inst, label = Instance(), "faculty IF, all semesters"
    else:
        inst = Instance(scope=args.program, semester=args.semester or None)
        label = f"{args.program or 'faculty IF'}, semester {args.semester or 'all'}"

    n_mand = sum(1 for s in inst.sessions if s["required_by"])
    print(f"scope: {label}")
    print(f"{len(inst.sessions)} sessions ({n_mand} mandatory, "
          f"{len(inst.sessions)-n_mand} elective), {len(inst.cohorts)} cohorts, "
          f"{len({p for s in inst.sessions for p in s['lecturers']})} lecturers")

    if args.published:
        sol = published_solution(inst)
        errs = validate(inst, sol)
        score, _pen = soft_score(inst, sol)
        print(f"\nPUBLISHED timetable: {len(errs)} hard violations, soft {score}")
        for e, n in collections.Counter(x.split(":")[0] for x in errs).items():
            print(f"  {e}: {n}")
        return

    t0 = time.time()
    best, score, pen, seen, restarts, mode = search_adaptive(
        inst, args.seconds, args.solver)
    if best is None:
        print(f"\nNo timetable found in {time.time()-t0:.0f}s ({restarts} restarts).")
        return

    print_timetable(inst, best)
    print(f"\nsolver={args.solver} ({mode})  {seen} timetables seen, "
          f"{restarts} restarts, {time.time()-t0:.1f}s")
    print(f"soft penalty {score}")
    for p, text in sorted(pen, reverse=True)[:12]:
        print(f"  -{p:>3}  {text}")
    errs = validate(inst, best)
    print("\nhard validation:",
          "OK — no violations" if not errs else f"{len(errs)} VIOLATIONS")
    for e in errs[:10]:
        print("  -", e)


if __name__ == "__main__":
    main()
