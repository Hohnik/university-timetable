from constraints.soft import (
    avoid_late_slot,
    avoid_long_days,
    elective_vs_mandatory,
    keep_lecture_practical_together,
    minimize_daily_gaps,
    reward_free_day,
    teacher_daily_load,
)


# S4 -------------------------------------------------------------------

def test_avoid_late_slot_penalizes_last_timeslot(make_inst, make_lecture):
    inst = make_inst([make_lecture(length=1)])
    assert avoid_late_slot.penalties(inst, {0: ("Mon", 10)}) == [(6, "S4 late timeslot: C (Mon)")]


def test_avoid_late_slot_no_penalty_earlier(make_inst, make_lecture):
    inst = make_inst([make_lecture(length=1)])
    assert avoid_late_slot.penalties(inst, {0: ("Mon", 0)}) == []


# S2 -------------------------------------------------------------------

def test_minimize_daily_gaps_prices_gaps_exponentially(make_inst, make_lecture):
    lectures = [make_lecture(curricula=["g1"], length=1), make_lecture(curricula=["g1"], length=1)]
    inst = make_inst(lectures, curricula={"g1": {"label": "G1"}})
    pen = minimize_daily_gaps.penalties(inst, {0: ("Mon", 0), 1: ("Mon", 2)})
    assert pen == [(2, "S2 gap: G1 1 idle timeslot(s) Mon")]


# S3 -------------------------------------------------------------------

def test_teacher_daily_load_penalizes_beyond_two_lectures(make_inst, make_lecture):
    lectures = [make_lecture(teachers=["Prof A"]) for _ in range(3)]
    inst = make_inst(lectures)
    solution = {0: ("Mon", 0), 1: ("Mon", 2), 2: ("Mon", 4)}
    assert teacher_daily_load.penalties(inst, solution) == [(5, "S3 overload: Prof A 3 lectures Mon")]


# S5 -------------------------------------------------------------------

def test_reward_free_day_penalizes_near_empty_day(make_inst, make_lecture):
    inst = make_inst([make_lecture(curricula=["g1"], length=1)], curricula={"g1": {"label": "G1"}})
    pen = reward_free_day.penalties(inst, {0: ("Mon", 0)})
    assert (14, "S5 near-empty day: G1 1 timeslot on Mon") in pen


def test_reward_free_day_penalizes_zero_free_days(make_inst, make_lecture):
    lectures = [make_lecture(curricula=["g1"], length=1) for _ in range(5)]
    inst = make_inst(lectures, curricula={"g1": {"label": "G1"}})
    solution = {i: (day, 0) for i, day in enumerate(inst.days)}
    pen = reward_free_day.penalties(inst, solution)
    assert (20, "S5 no free day: G1 teaches 5/5 days") in pen


# S6 -------------------------------------------------------------------

def test_avoid_long_days_prices_overage_progressively(make_inst, make_lecture):
    inst = make_inst([make_lecture(curricula=["g1"], length=12)], curricula={"g1": {"label": "G1"}})
    pen = avoid_long_days.penalties(inst, {0: ("Mon", 0)})
    assert pen == [(24, "S6 long day: G1 12 timeslots Mon")]  # MAX_PER_DAY=10, over=2 -> 6*2**2


# S7 -------------------------------------------------------------------

def test_keep_lecture_practical_together_penalizes_apart(make_inst, make_lecture):
    lecture = make_lecture(course_key="math", practical=False, length=1, course="Mathematik II")
    practical = make_lecture(course_key="math", practical=True, length=1, course="Mathematik II")
    inst = make_inst([lecture, practical])
    solution = {0: ("Mon", 0), 1: ("Mon", 5)}
    pen = keep_lecture_practical_together.penalties(inst, solution)
    assert pen == [(5, "S7 lecture/practical apart: Mathematik II on Mon")]


def test_keep_lecture_practical_together_no_penalty_when_adjacent(make_inst, make_lecture):
    lecture = make_lecture(course_key="math", practical=False, length=2)
    practical = make_lecture(course_key="math", practical=True, length=2)
    inst = make_inst([lecture, practical])
    assert keep_lecture_practical_together.penalties(inst, {0: ("Mon", 0), 1: ("Mon", 2)}) == []


# S8 -------------------------------------------------------------------

def test_elective_vs_mandatory_penalizes_overlap(make_inst, make_lecture):
    mandatory = make_lecture(required_by=["g1"], curricula=["g1"], length=2, short="Mand")
    elective = make_lecture(required_by=[], curricula=["g1"], length=2, short="Elec")
    inst = make_inst([mandatory, elective])
    pen = elective_vs_mandatory.penalties(inst, {0: ("Mon", 0), 1: ("Mon", 1)})
    assert pen == [(7, "S8 elective vs mandatory: g1 Mand/Elec")]


def test_elective_vs_mandatory_no_penalty_without_overlap(make_inst, make_lecture):
    mandatory = make_lecture(required_by=["g1"], curricula=["g1"], length=1, short="Mand")
    elective = make_lecture(required_by=[], curricula=["g1"], length=1, short="Elec")
    inst = make_inst([mandatory, elective])
    assert elective_vs_mandatory.penalties(inst, {0: ("Mon", 0), 1: ("Mon", 5)}) == []
