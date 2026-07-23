"""Spike: solve the same CB-CTT instance with Google OR-Tools CP-SAT instead
of python-constraint's backtracking/MinConflicts (see solve.py), to check
whether a dedicated combinatorial solver beats local search + random restarts
on the full IF+SA instance.

Reuses solve.py's soft_score()/validate() as the single source of truth for
scoring and correctness, so results are directly comparable to `solve.py`'s
numbers on the same instance.

Fidelity notes (this is a spike, not a full port):
  - H1/H2/H3/H5/H6/H7 are modeled exactly, reusing the same predicate
    functions solve.py's build_problem() calls (constraints/hard/*.py).
  - H4 is modeled exactly: distinct (timeslot, fach_id) cells per day, same
    as course_daily_cap.n_ary_constraint, via per-lecture per-timeslot
    "covers" reification. Applied to every (curriculum, course) group, not
    just 3+-lecture ones -- slightly stricter than build_problem's own
    2-lecture pairwise exemption for parallel sections, but never produces
    a false violation (validated below).
  - H8 is intentionally NOT modeled as a hard constraint (see note at its
    call site) -- it's the one rule solve.py's own validate() doesn't check
    either, so dropping it keeps "hard-feasible" judged by the same bar as
    solve.py's MinConflicts results.
  - The objective only optimizes S3, S4 and S6 (the ones with a clean closed
    form). S2/S5/S7/S8 are NOT steered by the solver, only measured
    afterwards via the real soft_score() -- so CP-SAT is at a structural
    disadvantage on total soft score versus what it could achieve with a
    complete objective. Reported numbers are still real, just not CP-SAT's
    ceiling.

Every returned solution is re-checked with solve.py's real validate() --
never trust the model's own fidelity notes over that.

Usage
-----
    uv run src/solve_cpsat.py --seconds 30
    uv run src/solve_cpsat.py --faculty --seconds 60
"""
from __future__ import annotations

import argparse
import collections
import time

from ortools.sat.python import cp_model

from constraints import grid, hard, limits
from instance import Instance
from solve import print_timetable, soft_score, to_records, validate

LATE_TIMESLOTS = limits.LATE_TIMESLOTS
MAX_PER_DAY = limits.MAX_PER_DAY


def _covers_bool(model, start_var, length, t, cache, key_prefix):
    """Reified 'does this lecture, wherever start_var places it, cover
    timeslot t' -- i.e. start_var in [t-length+1, t]. Cached per (lecture,
    timeslot) since it doesn't depend on which day, only the within-day
    position."""
    key = (key_prefix, t)
    if key in cache:
        return cache[key]
    lo = t - length + 1
    le = model.NewBoolVar(f"le_{key_prefix}_{t}")
    model.Add(start_var <= t).OnlyEnforceIf(le)
    model.Add(start_var > t).OnlyEnforceIf(le.Not())
    ge = model.NewBoolVar(f"ge_{key_prefix}_{t}")
    model.Add(start_var >= lo).OnlyEnforceIf(ge)
    model.Add(start_var < lo).OnlyEnforceIf(ge.Not())
    covers = model.NewBoolVar(f"covers_{key_prefix}_{t}")
    model.AddBoolAnd([le, ge]).OnlyEnforceIf(covers)
    model.AddBoolOr([le.Not(), ge.Not()]).OnlyEnforceIf(covers.Not())
    cache[key] = covers
    return covers


def build_model(inst: Instance, hard_long_day=True, hard_no_late_mandatory=True):
    model = cp_model.CpModel()
    lectures = inst.lectures
    n = len(lectures)
    n_days = len(inst.days)
    n_timeslots = len(inst.grid)
    day_index = {d: k for k, d in enumerate(inst.days)}

    day = [None] * n
    start = [None] * n
    absv = [None] * n
    interval = [None] * n

    for i, lec in enumerate(lectures):
        length = lec["length"]
        allowed = sorted(day_index[d] for d in inst.available_days(lec))     # H3
        day[i] = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(allowed), f"day{i}")

        max_start = n_timeslots - length
        if hard_no_late_mandatory and lec["required_by"]:                    # H7
            allowed_starts = [s for s in range(max_start + 1)
                              if not (set(range(s, s + length)) & LATE_TIMESLOTS)]
            if not allowed_starts:
                allowed_starts = list(range(max_start + 1))
            start[i] = model.NewIntVarFromDomain(
                cp_model.Domain.FromValues(allowed_starts), f"start{i}")
        else:
            start[i] = model.NewIntVar(0, max_start, f"start{i}")

        absv[i] = model.NewIntVar(0, n_days * n_timeslots - 1, f"abs{i}")
        model.Add(absv[i] == day[i] * n_timeslots + start[i])
        end = model.NewIntVar(0, n_days * n_timeslots, f"end{i}")
        model.Add(end == absv[i] + length)
        interval[i] = model.NewIntervalVar(absv[i], length, end, f"iv{i}")

    # H1/H2/H6: pairwise, reusing the exact same predicates build_problem() uses.
    for i, j, a, b in grid.lecture_pairs(lectures):
        if not grid.is_parallel(a, b):                                       # H5 exemption
            clash = (hard.curriculum_no_overlap.conflicts(a, b)
                     or hard.teacher_no_overlap.conflicts(a, b))              # H1 / H2
            if clash:
                model.AddNoOverlap([interval[i], interval[j]])

        if hard.contiguous_same_type.applies(a, b):                          # H6
            same_day = model.NewBoolVar(f"sameday{i}_{j}")
            model.Add(day[i] == day[j]).OnlyEnforceIf(same_day)
            model.Add(day[i] != day[j]).OnlyEnforceIf(same_day.Not())
            model.Add(start[i] + a["length"] >= start[j]).OnlyEnforceIf(same_day)
            model.Add(start[j] + b["length"] >= start[i]).OnlyEnforceIf(same_day)

    # Shared "is lecture i on day d" booleans -- feeds H4, H8, S3, S6.
    on = {}
    for i in range(n):
        for d in range(n_days):
            b = model.NewBoolVar(f"on{i}_{d}")
            model.Add(day[i] == d).OnlyEnforceIf(b)
            model.Add(day[i] != d).OnlyEnforceIf(b.Not())
            on[i, d] = b

    # H4: exact distinct-(timeslot, fach_id)-cell count per day <= cap, same
    # rule course_daily_cap.n_ary_constraint checks. Skips size-1 groups (a
    # single lecture can never exceed its own cap_for()).
    covers_cache = {}
    for (_g, _key), idx in hard.course_daily_cap.groups_by_course(inst).items():
        if len(idx) < 2:
            continue
        cap = hard.course_daily_cap.cap_for(*(lectures[i]["length"] for i in idx))
        by_fach = collections.defaultdict(list)
        for i in idx:
            by_fach[lectures[i]["fach_id"]].append(i)
        for d in range(n_days):
            cells = []
            for ids in by_fach.values():
                for t in range(n_timeslots):
                    at_list = []
                    for i in ids:
                        cov = _covers_bool(model, start[i], lectures[i]["length"], t, covers_cache, i)
                        at = model.NewBoolVar(f"at_{i}_{d}_{t}")
                        model.AddBoolAnd([on[i, d], cov]).OnlyEnforceIf(at)
                        model.AddBoolOr([on[i, d].Not(), cov.Not()]).OnlyEnforceIf(at.Not())
                        at_list.append(at)
                    if len(at_list) == 1:
                        cells.append(at_list[0])
                    else:
                        cell = model.NewBoolVar(f"cell_{ids[0]}_{t}_{d}")
                        model.AddMaxEquality(cell, at_list)
                        cells.append(cell)
            model.Add(sum(cells) <= cap)

    # H8 is intentionally NOT modeled as a hard constraint here. Its true
    # semantics dedupe by actual timeslot overlap (any lectures sharing a
    # slot count once, whatever their fach_id), unlike H4's fach-based
    # dedup -- exactly modeling that needs per-timeslot occupancy variables,
    # more machinery than this spike calls for. Notably, solve.py's own
    # validate() doesn't check H8 either (it's the one "optional, only
    # applied under MinConflicts" rule in the real system) -- so dropping it
    # here keeps hard-feasibility judged by the exact same criteria as
    # solve.py's MinConflicts results. S6 (long-day penalty) still steers
    # the objective below, just without a hard cap backing it up.
    _ = hard_long_day  # kept for CLI/API symmetry with solve.search()

    # --- Objective: S3 + S4 + S6 only (see module docstring) ---------------
    objective_terms = []

    # S4: +6 per lecture landing in the day's last timeslots, regardless of day.
    # A lecture [start, start+length) overlaps LATE_TIMESLOTS iff
    # start + length - 1 >= min(LATE_TIMESLOTS), i.e. start >= that threshold.
    for i, lec in enumerate(lectures):
        length = lec["length"]
        threshold = max(0, min(LATE_TIMESLOTS) - length + 1)
        late = model.NewBoolVar(f"late{i}")
        model.Add(start[i] >= threshold).OnlyEnforceIf(late)
        model.Add(start[i] < threshold).OnlyEnforceIf(late.Not())
        objective_terms.append(6 * late)

    # S3: +5 per lecture beyond a teacher's 2nd that day.
    by_teacher = {}
    for i, lec in enumerate(lectures):
        for p in lec["teachers"]:
            by_teacher.setdefault(p, []).append(i)
    for p, idx in by_teacher.items():
        for d in range(n_days):
            count = model.NewIntVar(0, len(idx), f"tcount_{p}_{d}")
            model.Add(count == sum(on[i, d] for i in idx))
            over = model.NewIntVar(0, len(idx), f"tover_{p}_{d}")
            model.Add(over >= count - 2)
            model.Add(over >= 0)
            objective_terms.append(5 * over)

    # S6: +6*2^over when a curriculum's day exceeds MAX_PER_DAY timeslots.
    # This is a soft *guidance* term (not a hard cap -- see the H8 note
    # above), so it uses a plain sum of lengths rather than exact per-
    # timeslot dedup: fine for steering the search, not for correctness.
    # `total_len` counts every OFFERED lecture (mandatory + elective) for a
    # curriculum across the whole week -- some curricula offer dozens of
    # electives a student would never all take, so this can be large enough
    # that 6*2^over overflows a 64-bit int. The exponential penalty is only
    # meant to make "obviously terrible" pile-ups unattractive to the
    # optimizer, so it's saturated at CAP_OVER: any actual over beyond that
    # is already such an enormous deterrent that its exact value is moot.
    CAP_OVER = 30
    penalty_table = [0] + [6 * (2 ** over) for over in range(1, CAP_OVER + 1)]
    for g in inst.curricula:
        idx = hard.curriculum_day_cap.curriculum_lectures(inst, g)
        if not idx:
            continue
        total_len = sum(lectures[i]["length"] for i in idx)
        for d in range(n_days):
            total = model.NewIntVar(0, total_len, f"total_{g}_{d}")
            model.Add(total == sum(lectures[i]["length"] * on[i, d] for i in idx))
            over = model.NewIntVar(0, total_len, f"over_{g}_{d}")
            model.Add(over >= total - MAX_PER_DAY)
            model.Add(over >= 0)
            capped_over = model.NewIntVar(0, CAP_OVER, f"capped_over_{g}_{d}")
            model.AddMinEquality(capped_over, [over, CAP_OVER])
            penalty = model.NewIntVar(0, penalty_table[-1], f"pen_{g}_{d}")
            model.AddElement(capped_over, penalty_table, penalty)
            objective_terms.append(penalty)

    model.Minimize(sum(objective_terms))
    return model, day, start


def solve_cpsat(inst: Instance, seconds, hard_long_day=True, hard_no_late_mandatory=True, seed=0):
    model, day, start = build_model(inst, hard_long_day, hard_no_late_mandatory)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = seconds
    solver.parameters.num_workers = 8
    solver.parameters.random_seed = seed
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None, status
    solution = {i: (inst.days[solver.Value(day[i])], solver.Value(start[i]))
                for i in range(len(inst.lectures))}
    return solution, status


def search_adaptive_cpsat(inst: Instance, seconds):
    """Mirrors solve.search_adaptive: strict model first, relaxed fallback."""
    sol, status = solve_cpsat(inst, seconds / 2, hard_no_late_mandatory=True)
    if sol is not None:
        return sol, "strict"
    sol, status = solve_cpsat(inst, seconds / 2, hard_no_late_mandatory=False)
    return sol, "relaxed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--program", default=None)
    ap.add_argument("--semester", type=int, default=2)
    ap.add_argument("--faculty", action="store_true")
    ap.add_argument("--seconds", type=float, default=30)
    args = ap.parse_args()

    if args.faculty:
        inst = Instance()
    else:
        inst = Instance(scope=args.program, semester=args.semester or None)
    faculties = "+".join(sorted({c["faculty"] for c in inst.curricula.values()}))
    label = (f"faculty {faculties}, all semesters" if args.faculty else
              f"{args.program or f'faculty {faculties}'}, semester {args.semester or 'all'}")

    n_mand = sum(1 for lec in inst.lectures if lec["required_by"])
    print(f"scope: {label}  [CP-SAT]")
    print(f"{len(inst.lectures)} lectures ({n_mand} mandatory, "
          f"{len(inst.lectures)-n_mand} elective), {len(inst.curricula)} curricula, "
          f"{len({p for lec in inst.lectures for p in lec['teachers']})} teachers")

    t0 = time.time()
    best, mode = search_adaptive_cpsat(inst, args.seconds)
    elapsed = time.time() - t0
    if best is None:
        print(f"\nNo timetable found in {elapsed:.1f}s (model proven infeasible or timed out).")
        return

    print_timetable(inst, best)
    score, pen = soft_score(inst, best)
    print(f"\nsolver=cp-sat ({mode})  {elapsed:.1f}s")
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
