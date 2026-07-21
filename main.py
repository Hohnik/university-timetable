"""
University Scheduler - Proof of Concept (v2)
=============================================
Constraint-satisfaction scheduler using `python-constraint`.

Model (borrowed from Timefold's school-timetabling quickstart):
  - A LESSON is one weekly session of a course, taught by a professor
    to a cohort (all students of one semester).
  - The solver assigns each lesson a (timeslot, room) pair.

HARD constraints (never violated):
  1. A professor teaches at most one lesson per timeslot.
  2. A cohort attends at most one lesson per timeslot.
  3. A room holds at most one lesson per timeslot.
  4. Room capacity >= number of enrolled students.    (encoded in domains)
  5. Professors are only scheduled when available.    (encoded in domains)
  6. Lessons of the same course are >= 2 days apart
     (so never twice on one day, and never on consecutive days).
  7. A cohort has at most 3 lessons per day.

SOFT constraints ("almost mandatory" - python-constraint cannot optimize,
so we iterate over valid schedules for a few seconds, score each, and
keep the best one found):
  S1. Keep the 12:00 slot free (lunch break).           10 points/violation
  S2. No idle gaps between a cohort's lessons on a day.  4 points/gap-slot
  S3. A professor teaches at most 2 lessons per day.     5 points/extra
  S4. Nothing on Friday 15:45.                           3 points/lesson

Install:  pip install python-constraint
Run:      python scheduler_poc.py
"""

import random
import time
from constraint import Problem

# ---------------------------------------------------------------------------
# 1. Entities / sample data  (~2.5x the v1 dataset)
# ---------------------------------------------------------------------------

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
HOURS = ["08:30", "10:15", "12:00", "14:00", "15:45"]

TIMESLOTS = [(day, hour) for day in DAYS for hour in HOURS]

# name -> capacity
ROOMS = {
    "Room A": 40,
    "Room B": 60,
    "Room C": 60,
    "Seminar Room": 30,
    "Auditorium": 200,
}

# professor -> days they are NOT available
PROFESSOR_UNAVAILABLE = {
    "Prof. Turing": {"Fri"},
    "Prof. Curie": set(),
    "Prof. Noether": {"Mon", "Tue"},
    "Prof. Dijkstra": set(),
    "Prof. Hopper": {"Wed"},
    "Prof. Lovelace": set(),
    "Prof. Gauss": {"Fri"},
    "Prof. Hamilton": set(),
}

# cohort -> number of students
COHORTS = {
    "Semester 1": 170,
    "Semester 3": 55,
    "Semester 5": 28,
}

# (course, professor, lessons_per_week)  grouped by cohort
CURRICULUM = {
    "Semester 1": [
        ("Math I", "Prof. Noether", 2),
        ("Intro Programming", "Prof. Dijkstra", 2),
        ("Physics I", "Prof. Curie", 2),
        ("Digital Systems", "Prof. Hamilton", 1),
        ("Academic Skills", "Prof. Lovelace", 1),
    ],
    "Semester 3": [
        ("Algorithms", "Prof. Dijkstra", 2),
        ("Theoretical CS", "Prof. Turing", 2),
        ("Databases", "Prof. Turing", 1),
        ("Statistics", "Prof. Gauss", 2),
        ("Operating Systems", "Prof. Hopper", 2),
    ],
    "Semester 5": [
        ("Machine Learning", "Prof. Lovelace", 2),
        ("Compilers", "Prof. Hopper", 2),
        ("Numerical Methods", "Prof. Gauss", 2),
        ("Software Eng.", "Prof. Hamilton", 1),
        ("Cryptography", "Prof. Turing", 1),
    ],
}

# Flatten to one entry per lesson: (course, professor, cohort, students)
LESSONS = [
    (course, prof, cohort, COHORTS[cohort])
    for cohort, courses in CURRICULUM.items()
    for course, prof, per_week in courses
    for _ in range(per_week)
]

MAX_LESSONS_PER_DAY = 3  # hard constraint 7
SEARCH_SECONDS = 10  # time budget for the soft-constraint search


# ---------------------------------------------------------------------------
# 2. Build the constraint problem (hard constraints only)
# ---------------------------------------------------------------------------


def build_problem(rng=None):
    problem = Problem()

    # One variable per lesson; value = (timeslot, room).
    # Constraints 4 + 5 are enforced by leaving invalid pairs out of the domain.
    # Shuffling the domain (per restart) makes the solver explore a genuinely
    # different corner of the search space each time.
    for i, (course, prof, cohort, students) in enumerate(LESSONS):
        domain = [
            (slot, room)
            for slot in TIMESLOTS
            for room, capacity in ROOMS.items()
            if capacity >= students  # constraint 4
            and slot[0] not in PROFESSOR_UNAVAILABLE[prof]  # constraint 5
        ]
        if rng is not None:
            rng.shuffle(domain)
        problem.addVariable(i, domain)

    day_index = {day: n for n, day in enumerate(DAYS)}

    # Pairwise constraints between every two lessons.
    for i in range(len(LESSONS)):
        for j in range(i + 1, len(LESSONS)):
            course_i, prof_i, cohort_i, _ = LESSONS[i]
            course_j, prof_j, cohort_j, _ = LESSONS[j]

            # Constraint 3: no two lessons in the same room at the same time.
            problem.addConstraint(lambda a, b: a != b, (i, j))

            # Constraint 1: same professor -> different timeslots.
            if prof_i == prof_j:
                problem.addConstraint(lambda a, b: a[0] != b[0], (i, j))

            # Constraint 2: same cohort -> different timeslots.
            if cohort_i == cohort_j:
                problem.addConstraint(lambda a, b: a[0] != b[0], (i, j))

            # Constraint 6: same course -> at least 2 days apart.
            if course_i == course_j:
                problem.addConstraint(
                    lambda a, b: abs(day_index[a[0][0]] - day_index[b[0][0]]) >= 2,
                    (i, j),
                )

    # Constraint 7: a cohort has at most MAX_LESSONS_PER_DAY lessons per day.
    def at_most_n_per_day(*assignments):
        counts = {}
        for (day, _hour), _room in assignments:
            counts[day] = counts.get(day, 0) + 1
        return all(c <= MAX_LESSONS_PER_DAY for c in counts.values())

    for cohort in COHORTS:
        cohort_vars = [i for i, l in enumerate(LESSONS) if l[2] == cohort]
        problem.addConstraint(at_most_n_per_day, cohort_vars)

    return problem


# ---------------------------------------------------------------------------
# 3. Soft constraints: score a valid schedule (lower = better)
# ---------------------------------------------------------------------------


def soft_score(solution):
    """Returns (total_penalty, list of human-readable violations)."""
    penalties = []
    hour_index = {h: n for n, h in enumerate(HOURS)}

    # S4: Friday 15:45 is unpopular.
    for i, (course, *_) in enumerate(LESSONS):
        (day, hour), _room = solution[i]
        if (day, hour) == ("Fri", "15:45"):
            penalties.append((3, f"S4 late Friday: {course}"))

    # S2: no gaps within a cohort's day.
    for cohort in COHORTS:
        for day in DAYS:
            hours_used = sorted(
                hour_index[solution[i][0][1]]
                for i, l in enumerate(LESSONS)
                if l[2] == cohort and solution[i][0][0] == day
            )
            if hours_used:
                gaps = (hours_used[-1] - hours_used[0] + 1) - len(hours_used)
                if gaps:
                    penalties.append(
                        (4 * gaps, f"S2 gap: {cohort} has {gaps} idle slot(s) on {day}")
                    )

    # S3: professor teaches at most 2 lessons per day.
    # for prof in PROFESSOR_UNAVAILABLE:
    #     for day in DAYS:
    #         n = sum(
    #             1
    #             for i, l in enumerate(LESSONS)
    #             if l[1] == prof and solution[i][0][0] == day
    #         )
    #         if n > 2:
    #             penalties.append(
    #                 (5 * (n - 2), f"S3 overload: {prof} has {n} lessons on {day}")
    #             )

    return sum(p for p, _ in penalties), penalties


# ---------------------------------------------------------------------------
# 4. Independent validator for the HARD constraints (does not trust solver)
# ---------------------------------------------------------------------------


def validate(solution):
    errors = []
    day_index = {day: n for n, day in enumerate(DAYS)}
    for i, (course, prof, cohort, students) in enumerate(LESSONS):
        (day, _hour), room = solution[i]
        if ROOMS[room] < students:
            errors.append(f"{course}: room {room} too small")
        if day in PROFESSOR_UNAVAILABLE[prof]:
            errors.append(f"{course}: {prof} unavailable on {day}")
    for i in range(len(LESSONS)):
        for j in range(i + 1, len(LESSONS)):
            (slot_i, room_i), (slot_j, room_j) = solution[i], solution[j]
            ci, pi, coi, _ = LESSONS[i]
            cj, pj, coj, _ = LESSONS[j]
            if slot_i == slot_j and room_i == room_j:
                errors.append(f"Room clash: {ci} / {cj}")
            if slot_i == slot_j and pi == pj:
                errors.append(f"Professor clash: {ci} / {cj}")
            if slot_i == slot_j and coi == coj:
                errors.append(f"Cohort clash: {ci} / {cj}")
            if ci == cj and abs(day_index[slot_i[0]] - day_index[slot_j[0]]) < 2:
                errors.append(f"Lessons too close together: {ci}")
    for cohort in COHORTS:
        for day in DAYS:
            n = sum(
                1
                for i, l in enumerate(LESSONS)
                if l[2] == cohort and solution[i][0][0] == day
            )
            if n > MAX_LESSONS_PER_DAY:
                errors.append(f"{cohort}: {n} lessons on {day}")
    return errors


# ---------------------------------------------------------------------------
# 5. Search: iterate valid schedules, keep the best-scored one
# ---------------------------------------------------------------------------

SOLUTIONS_PER_RESTART = 50  # consecutive solutions are near-identical, so
# take a few per restart and reshuffle instead


def find_best_schedule():
    best, best_score, best_penalties = None, None, None
    n_seen = n_restarts = 0
    deadline = time.time() + SEARCH_SECONDS

    while time.time() < deadline:
        n_restarts += 1
        problem = build_problem(rng=random.Random(n_restarts))
        for solution in problem.getSolutionIter():
            n_seen += 1
            score, pens = soft_score(solution)
            if best_score is None or score < best_score:
                best, best_score, best_penalties = solution, score, pens
            if (
                best_score == 0
                or time.time() > deadline
                or n_seen % SOLUTIONS_PER_RESTART == 0
            ):
                break
        if best_score == 0:
            break

    return best, best_score, best_penalties, n_seen, n_restarts


def print_timetable(solution):
    for cohort in COHORTS:
        print(f"\n=== {cohort} ({COHORTS[cohort]} students) ===")
        rows = []
        for i, (course, prof, _cohort, _) in enumerate(LESSONS):
            if _cohort != cohort:
                continue
            (day, hour), room = solution[i]
            rows.append((DAYS.index(day), hour, day, course, prof, room))
        for _, hour, day, course, prof, room in sorted(rows):
            print(f"  {day} {hour}  {course:<18} {prof:<15} {room}")


def main():
    t0 = time.time()
    best, score, penalties, n_seen, n_restarts = find_best_schedule()

    if best is None:
        print("No valid schedule exists for the given hard constraints.")
        return

    print_timetable(best)

    print(
        f"\nSearched {n_seen} valid schedules "
        f"({n_restarts} random restarts) in {time.time() - t0:.1f}s."
    )
    print(f"Soft-constraint penalty of best schedule: {score}")
    for p, text in penalties:
        print(f"  -{p:>3}  {text}")

    errors = validate(best)
    print(
        "\nHard-constraint validation:",
        "OK - no violations" if not errors else f"{len(errors)} VIOLATIONS!",
    )
    for e in errors:
        print("  -", e)


if __name__ == "__main__":
    main()
