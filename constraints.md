# Constraints

The solver (`src/solve.py`) builds one CSP variable per weekly *session* —
value = `(day, first 45-minute block)`. A day has 12 blocks; the 15-minute
breaks and the 50-minute lunch sit between adjacent block indices, so a
session spanning one costs no block and never registers as an idle gap.
Rooms are deliberately out of scope — see `src/solve.py`'s module docstring.

Every rule below lives in its own file under `src/constraints/hard/` or
`src/constraints/soft/`, named to match the section headers here.

## Hard constraints

Hard constraints are never violated. The solver either finds an assignment
that satisfies all of them, or reports no solution — there is no partial
credit, which is why each one is kept as small and as clearly justified as
possible.

### `cohort_no_overlap` (H1)

A cohort cannot attend two sessions that are both mandatory for it at the
same time. This is the only unbreakable cohort rule: two *mandatory* classes
overlapping would make it impossible for a student to complete their degree
on schedule. Overlapping *electives* are allowed — see `elective_vs_mandatory`
(S8) below, which discourages but does not forbid that.

### `lecturer_no_overlap` (H2)

A lecturer cannot teach two sessions at once. Unconditional — nobody can be
in two rooms simultaneously.

### `lecturer_availability` (H3)

A session may only be placed on a day its lecturer is actually known to
teach. Availability is inferred from the published timetable ("this lecturer
is never seen on a Friday"), which makes it self-fulfilling for anyone with
too little data — a lecturer who teaches only one session a week would
otherwise look "available" on exactly one day. So this only applies to
lecturers with enough observed sessions (`MIN_AVAILABILITY_EVIDENCE`) to make
an absence meaningful, and if intersecting multiple co-teachers' known days
would empty the set entirely, the restriction is dropped rather than making
the whole instance unsolvable.

### `module_daily_cap` (H4)

At most `MAX_MODULE_BLOCKS_PER_DAY` blocks (~3 hours) of one subject may land
on a single day, applied per `(cohort, module)` pair — not by course name
alone, since identical module names (e.g. "Programmieren II") recur
independently across five different programs, and capping by name alone
would merge them into one shared, instantly-infeasible cap. A single session
already longer than the cap is allowed to stand alone; the cap then only
stops anything *else* joining it that day.

### `contiguous_same_type` (H6)

A subject's same-teaching-type sessions sharing a day must be contiguous —
no maths lecture at 08:45, unrelated classes in between, then maths again at
16:10. A lecture and its practical *may* legitimately sit apart on the same
day (see `keep_lecture_practical_together`, S7); this rule only fires when
both sessions are of the same type (two lectures, or two practicals).

### `no_late_mandatory` (H7, optional)

Keeps compulsory teaching out of the day's last block. This measurably
improves the soft score when it's feasible, but it also removes a fifth of
the week's capacity, so it isn't applied unconditionally — `search_adaptive`
tries it first and falls back to the relaxed model only if no solution
exists under it.

### `cohort_day_cap` (H8, optional)

Caps a cohort's total teaching load on one day at `MAX_PER_DAY` blocks
(~7.5 hours). It's `n`-ary over every session of a cohort at once, which is
exactly the shape that makes exhaustive backtracking degenerate into
generate-and-test — so this is only applied when using the local-search
solver (MinConflicts), which copes with it fine.

### A note on parallel groups (not a numbered rule)

Parallel lab groups of one module (same subject, different session — e.g.
two lab sections of the same practical) are *meant* to run simultaneously.
This isn't a constraint of its own; it's an exemption (`grid.is_parallel`)
that H1, H2, H4, and H6 all consult before applying. It doesn't get its own
file, because there is no rule to put in one.

## Soft constraints

Soft constraints are never enforced — python-constraint has no built-in
optimizer, so the solver instead generates many valid schedules (via random
restarts) and scores each one, keeping the best. Lower is better. A schedule
that violates zero soft constraints is not guaranteed to exist; the search
just gets as close as the time budget allows.

### `avoid_late_slot` (S4)

+6 points per session that lands in the day's last block. Late slots are
unpopular, but not forbidden the way H7 forbids them for mandatory classes.

### `minimize_daily_gaps` (S2)

+2^gaps points per idle block within a cohort's day. Priced exponentially on
purpose: one dead block between classes is a minor nuisance, but several in a
row means going home and coming back, which is disproportionately worse than
the block count alone suggests.

### `lecturer_daily_load` (S3)

+5 points per session beyond a lecturer's 2nd that day. Nothing stops a
lecturer teaching 3+ sessions in one day (H2/H3 already prevent conflicts and
bad days), but it's discouraged.

### `reward_free_day` (S5)

+14 points for a day holding exactly one session for a cohort — the worst
possible use of a student's week, since they commute in for 90 minutes and
many simply skip it. +20 points if a cohort has *no* free day across the
whole week. Consolidating single-session days into busier days is what
actually frees up a full day off, which is the outcome this rule rewards.

### `avoid_long_days` (S6)

+6 × 2^over points when a cohort's day exceeds `MAX_PER_DAY` blocks, `over`
being how many blocks past the cap. Progressive pricing for the same reason
as S2: a slightly long day is tolerable, a very long one isn't proportionally
worse — it's much worse.

### `keep_lecture_practical_together` (S7)

+5 points when a lecture and its practical (same subject, different teaching
type) share a day but don't sit adjacent to each other. H6 forbids splitting
the *same* teaching type outright; this only prices the milder mixed case.

### `elective_vs_mandatory` (S8)

+7 points per cohort for which an elective session overlaps a mandatory
session it could otherwise have taken. Not forbidden — HS Landshut's SPOs
explicitly state there's no guarantee electives are clash-free — but a
student picking that elective would lose a mandatory class, so the search is
pushed toward giving every elective a mandatory-free window where possible.
