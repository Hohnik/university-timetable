"""Solve the HS Landshut timetabling instance with `python-constraint`.

Modeled as Curriculum-Based Course Timetabling (CB-CTT, Di Gaspero & Schaerf
2003 / ITC-2007): one variable per weekly LECTURE, value = (day, first
45-minute timeslot). Rooms are not modeled — assigning them is a
comparatively easy post-processing step (bipartite matching per timeslot),
left for later. See constraints.md for the hard/soft rule catalogue; each
rule lives in constraints/hard/ or constraints/soft/, one file per rule.

Usage
-----
    uv run src/solve.py                       # semester 2, all programs
    uv run src/solve.py --semester 4
    uv run src/solve.py --faculty              # every lecture, all semesters
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
    n_timeslots = len(inst.grid)

    for i, lec in enumerate(inst.lectures):
        length = lec["length"]
        allowed = inst.available_days(lec)                                   # H3
        # A lecture may run from before the lunch break to after it — a long
        # practical scheduled 10:30-14:20 is legitimate, students simply take
        # their lunch within it. Nothing about lunch is filtered here.
        domain = [(day, timeslot)
                  for day in inst.days if day in allowed
                  for timeslot in range(n_timeslots - length + 1)]

        if hard_no_late_mandatory and lec["required_by"]:
            domain = hard.no_late_mandatory.filter_domain(domain, length)     # H7

        if rng:
            rng.shuffle(domain)
        problem.addVariable(i, domain)

    for i, j, a, b in grid.lecture_pairs(inst.lectures):
        la, lb = a["length"], b["length"]

        if not grid.is_parallel(a, b):                                       # H5 exemption
            clash_curricula = hard.curriculum_no_overlap.conflicts(a, b)      # H1
            clash_teacher = bool(hard.teacher_no_overlap.conflicts(a, b))     # H2
            if clash_curricula or clash_teacher:
                problem.addConstraint(
                    lambda x, y, la=la, lb=lb: not grid.blocks(x, y, la, lb), (i, j))

        if hard.course_daily_cap.applies(a, b):                               # H4
            cap = hard.course_daily_cap.cap_for(la, lb)
            problem.addConstraint(
                lambda x, y, la=la, lb=lb, cap=cap:
                    hard.course_daily_cap.pairwise(x, y, la, lb, cap), (i, j))

        if hard.contiguous_same_type.applies(a, b):                           # H6
            problem.addConstraint(
                lambda x, y, la=la, lb=lb:
                    hard.contiguous_same_type.touching(x, y, la, lb), (i, j))

    # H4 (exact): courses with 3+ lectures need an n-ary check, since pairwise
    # sums can't see three separate 1-timeslot lectures piling onto one day.
    for idx in hard.course_daily_cap.groups_by_course(inst).values():
        if len(idx) >= 3:
            problem.addConstraint(hard.course_daily_cap.n_ary_constraint(inst, idx), idx)

    # H8 (optional): n-ary over a whole curriculum's lectures — the shape that
    # makes backtracking degenerate into generate-and-test, but MinConflicts
    # copes.
    if hard_long_day:
        for g in inst.curricula:
            idx = hard.curriculum_day_cap.curriculum_lectures(inst, g)
            if len(idx) > limits.MAX_PER_DAY:
                problem.addConstraint(hard.curriculum_day_cap.build_constraint(inst, idx), idx)

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
    L = inst.lectures

    for i, lec in enumerate(L):
        day, _timeslot = solution[i]
        if day not in inst.available_days(lec):
            errors.append(f"H3 availability: {lec['short']} on {day}")

    for i, j, a, b in grid.lecture_pairs(L):
        if grid.is_parallel(a, b):
            continue                                                          # H5
        if not grid.blocks(solution[i], solution[j], a["length"], b["length"]):
            continue
        if hard.curriculum_no_overlap.conflicts(a, b):
            errors.append(f"H1 mandatory clash: {a['short']} / {b['short']}")
        if hard.teacher_no_overlap.conflicts(a, b):
            errors.append(f"H2 teacher clash: {a['short']} / {b['short']}")

    for i, j, a, b in grid.lecture_pairs(L):
        if not hard.contiguous_same_type.applies(a, b):
            continue
        if not hard.contiguous_same_type.touching(solution[i], solution[j], a["length"], b["length"]):
            errors.append(f"H6 split lecture: {a['course'][:28]} twice on {solution[i][0]}")

    for (g, key), idx in hard.course_daily_cap.groups_by_course(inst).items():
        for day, count in hard.course_daily_cap.violations(inst, idx, solution):
            errors.append(f"H4 course overload: {inst.label(g)} {key[:26]} {count} timeslots on {day}")

    return errors


# ---------------------------------------------------------------------------
# SWS budget check (diagnostic, from the SPO)
# ---------------------------------------------------------------------------

def student_timeslots(inst: Instance, curriculum):
    """Timeslots ONE student of this curriculum actually sits through in a week.

    Summing raw lectures overstates the load by ~50%, for two reasons that
    both had to be handled before the SPO's SWS figures could be matched:

      * PARALLEL LAB SECTIONS — a Praktikum offered to several lab sections
        appears once per section in the data, but a student attends one.
        Collapsed by taking a single representative lv_id per course (fach_id).

      * RHYTHM — `rhythmus 14` means fortnightly. Such a lecture averages
        half its length per week. And where two fortnightly lectures share
        an lv_id, they are alternating halves of one section (occurrences 7
        and 8 over a 15-week semester), so a student attends one, not both.

    Verified against the SPO: this brings IF2 from a nonsensical 38 SWS to 22
    against a prescribed 26, the remainder being electives not counted here.
    """
    byfach = collections.defaultdict(lambda: collections.defaultdict(list))
    for lec in inst.lectures:
        if curriculum in lec["required_by"]:
            byfach[lec["fach_id"]][lec["lv_id"]].append(lec)

    total = 0.0
    for lvs in byfach.values():
        best = 0.0
        for lecs in lvs.values():
            weekly = sum(lec["length"] for lec in lecs if lec["rhythm"] != "14")
            fortnightly = [lec["length"] for lec in lecs if lec["rhythm"] == "14"]
            weekly += max(fortnightly) * 0.5 if fortnightly else 0
            best = max(best, weekly)
        total += best
    return total


def sws_report(inst: Instance):
    """Compare a student's weekly load against the SWS the SPO prescribes.

    One 90-minute grid timeslot pair = 2 SWS.
    """
    rows = []
    for g, c in inst.curricula.items():
        m = re.search(r"(\d)", c["label"])
        sem = int(m.group(1)) if m else None
        want = CU.expected_sws(c["program"], sem)
        if not want:
            continue
        rows.append((c["label"], want, student_timeslots(inst, g) * 2))
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

    Banning compulsory teaching from the last timeslot improves quality a lot
    (soft 236 -> 140 on semester 2) but removes a fifth of the week's
    capacity. Semester 4 needs 19 of the 20 timeslots that remain, so the
    strict model is infeasible there. Rather than pick one globally, spend
    half the budget on the strict model and fall back if it yields nothing.
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
    """One row per (lecture, attending curriculum) — day/start/end/course/
    teacher/curriculum — independent of internal grid-timeslot indices. The
    one interchange format for display, JSON, or CSV."""
    rows = []
    for i, lec in enumerate(inst.lectures):
        day, timeslot = solution[i]
        start, _ = inst.grid[timeslot]
        _, end = inst.grid[timeslot + lec["length"] - 1]
        who = ", ".join(p.split(",")[0] for p in lec["teachers"]) or "—"
        for g in lec["curricula"]:
            rows.append({
                "curriculum": inst.label(g), "day": day, "start": start, "end": end,
                "course": lec["course"], "teacher": who,
                "kind": "mandatory" if g in lec["required_by"] else "elective",
            })
    day_index = {d: i for i, d in enumerate(inst.days)}
    return sorted(rows, key=lambda r: (r["curriculum"], day_index[r["day"]], r["start"]))


def print_timetable(inst: Instance, solution):
    records = to_records(inst, solution)
    for curriculum in dict.fromkeys(r["curriculum"] for r in records):
        print(f"\n=== {curriculum} ===")
        for r in records:
            if r["curriculum"] != curriculum:
                continue
            kind = "  " if r["kind"] == "mandatory" else "(W)"
            print(f"  {r['day']} {r['start']}-{r['end']:<8} {kind} "
                  f"{r['course'][:36]:<36} {r['teacher'][:20]}")


def published_solution(inst: Instance):
    return {i: (lec["published"]["day"], lec["published"]["timeslot"])
            for i, lec in enumerate(inst.lectures)}


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
        inst = Instance()
    else:
        inst = Instance(scope=args.program, semester=args.semester or None)
    faculties = "+".join(sorted({c["faculty"] for c in inst.curricula.values()}))

    if args.faculty:
        label = f"faculty {faculties}, all semesters"
    else:
        label = f"{args.program or f'faculty {faculties}'}, semester {args.semester or 'all'}"

    n_mand = sum(1 for lec in inst.lectures if lec["required_by"])
    print(f"scope: {label}")
    print(f"{len(inst.lectures)} lectures ({n_mand} mandatory, "
          f"{len(inst.lectures)-n_mand} elective), {len(inst.curricula)} curricula, "
          f"{len({p for lec in inst.lectures for p in lec['teachers']})} teachers")

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
