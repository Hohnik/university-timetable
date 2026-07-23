# Constraints

This is a Curriculum-Based Course Timetabling (CB-CTT) model, in the sense of
Di Gaspero & Schaerf (2003) / ITC-2007: **courses** consist of **lectures**
taught by **teachers**, **curricula** group the courses that share students
and therefore conflict, and the day is divided into **periods** (day +
timeslot). HS Landshut's real constraints go beyond the textbook 4 hard / 4
soft rules — the extras (elective vs. mandatory, lecture/practical pairing,
daily load caps, ...) are documented below alongside the core ones.

The solver (`src/solve.py`) builds one CSP variable per weekly *lecture* —
value = `(day, first 45-minute timeslot)`. A day has 12 timeslots; the
15-minute breaks and the 50-minute lunch sit between adjacent timeslot
indices, so a lecture spanning one costs no timeslot and never registers as
an idle gap. Rooms are deliberately out of scope — see `src/solve.py`'s
module docstring.

Every rule below lives in its own file under `src/constraints/hard/` or
`src/constraints/soft/`, named to match the section headers here.

## Hard constraints

Hard constraints are never violated. The solver either finds an assignment
that satisfies all of them, or reports no solution — there is no partial
credit, which is why each one is kept as small and as clearly justified as
possible.

### `curriculum_no_overlap` (H1)

A curriculum cannot attend two lectures that are both mandatory for it at the
same time. This is the only unbreakable curriculum rule: two *mandatory*
classes overlapping would make it impossible for a student to complete their
degree on schedule. Overlapping *electives* are allowed — see
`elective_vs_mandatory` (S8) below, which discourages but does not forbid
that.

### `teacher_no_overlap` (H2)

A teacher cannot teach two lectures at once. Unconditional — nobody can be in
two rooms simultaneously.

### `teacher_availability` (H3)

A lecture may only be placed on a day its teacher is actually known to teach.
Availability is inferred from the published timetable ("this teacher is
never seen on a Friday"), which makes it self-fulfilling for anyone with too
little data — a teacher who teaches only one lecture a week would otherwise
look "available" on exactly one day. So this only applies to teachers with
enough observed lectures (`MIN_AVAILABILITY_EVIDENCE`) to make an absence
meaningful, and if intersecting multiple co-teachers' known days would empty
the set entirely, the restriction is dropped rather than making the whole
instance unsolvable.

### `course_daily_cap` (H4)

At most `MAX_COURSE_TIMESLOTS_PER_DAY` timeslots (~3 hours) of one course may
land on a single day, applied per `(curriculum, course)` pair — not by course
name alone, since identical course names (e.g. "Programmieren II") recur
independently across five different programs, and capping by name alone
would merge them into one shared, instantly-infeasible cap. A single lecture
already longer than the cap is allowed to stand alone; the cap then only
stops anything *else* joining it that day.

### `contiguous_same_type` (H6)

A course's same-teaching-type lectures sharing a day must be contiguous — no
maths lecture at 08:45, unrelated classes in between, then maths again at
16:10. A lecture and its practical *may* legitimately sit apart on the same
day (see `keep_lecture_practical_together`, S7); this rule only fires when
both lectures are of the same type (two lectures, or two practicals).

### `no_late_mandatory` (H7, optional)

Keeps compulsory teaching out of the day's last timeslot. This measurably
improves the soft score when it's feasible, but it also removes a fifth of
the week's capacity, so it isn't applied unconditionally — `search_adaptive`
tries it first and falls back to the relaxed model only if no solution
exists under it.

### `curriculum_day_cap` (H8, optional)

Caps a curriculum's total teaching load on one day at `MAX_PER_DAY` timeslots
(~7.5 hours). It's `n`-ary over every lecture of a curriculum at once, which
is exactly the shape that makes exhaustive backtracking degenerate into
generate-and-test — so this is only applied when using the local-search
solver (MinConflicts), which copes with it fine.

### A note on parallel groups (not a numbered rule)

Parallel lab groups of one course (same subject, different lecture — e.g.
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

+6 points per lecture that lands in the day's last timeslot. Late timeslots
are unpopular, but not forbidden the way H7 forbids them for mandatory
classes.

### `minimize_daily_gaps` (S2)

+2^gaps points per idle timeslot within a curriculum's day. Priced
exponentially on purpose: one dead timeslot between classes is a minor
nuisance, but several in a row means going home and coming back, which is
disproportionately worse than the timeslot count alone suggests.

### `teacher_daily_load` (S3)

+5 points per lecture beyond a teacher's 2nd that day. Nothing stops a
teacher teaching 3+ lectures in one day (H2/H3 already prevent conflicts and
bad days), but it's discouraged.

### `reward_free_day` (S5)

+14 points for a day holding exactly one lecture for a curriculum — the
worst possible use of a student's week, since they commute in for 90 minutes
and many simply skip it. +20 points if a curriculum has *no* free day across
the whole week. Consolidating single-lecture days into busier days is what
actually frees up a full day off, which is the outcome this rule rewards.

### `avoid_long_days` (S6)

+6 × 2^over points when a curriculum's day exceeds `MAX_PER_DAY` timeslots,
`over` being how many timeslots past the cap. Progressive pricing for the
same reason as S2: a slightly long day is tolerable, a very long one isn't
proportionally worse — it's much worse.

### `keep_lecture_practical_together` (S7)

+5 points when a lecture and its practical (same course, different teaching
type) share a day but don't sit adjacent to each other. H6 forbids splitting
the *same* teaching type outright; this only prices the milder mixed case.

### `elective_vs_mandatory` (S8)

+7 points per curriculum for which an elective lecture overlaps a mandatory
lecture it could otherwise have taken. Not forbidden — HS Landshut's SPOs
explicitly state there's no guarantee electives are clash-free — but a
student picking that elective would lose a mandatory class, so the search is
pushed toward giving every elective a mandatory-free window where possible.
