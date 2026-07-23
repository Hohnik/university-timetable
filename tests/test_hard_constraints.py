from constraints.hard import (
    contiguous_same_type,
    course_daily_cap,
    curriculum_day_cap,
    curriculum_no_overlap,
    no_late_mandatory,
    teacher_availability,
    teacher_no_overlap,
)


# H1 -----------------------------------------------------------------------

def test_curriculum_no_overlap_conflicts_only_where_both_mandatory(make_lecture):
    a = make_lecture(required_by=["g1", "g2"])
    b = make_lecture(required_by=["g2", "g3"])
    assert curriculum_no_overlap.conflicts(a, b) == {"g2"}


def test_curriculum_no_overlap_ignores_electives(make_lecture):
    a = make_lecture(required_by=["g1"])
    b = make_lecture(required_by=[])
    assert curriculum_no_overlap.conflicts(a, b) == set()


# H2 -----------------------------------------------------------------------

def test_teacher_no_overlap_conflicts(make_lecture):
    a = make_lecture(teachers=["Prof A", "Prof B"])
    b = make_lecture(teachers=["Prof B"])
    assert teacher_no_overlap.conflicts(a, b) == {"Prof B"}


# H3 -----------------------------------------------------------------------

def test_teacher_availability_restricts_with_enough_evidence(make_inst, make_lecture):
    inst = make_inst([], teacher_days={"Prof A": ["Mon", "Tue"]}, teach_count={"Prof A": 10})
    lec = make_lecture(teachers=["Prof A"])
    assert teacher_availability.available_days(inst, lec) == {"Mon", "Tue"}


def test_teacher_availability_ignores_thin_evidence(make_inst, make_lecture):
    inst = make_inst([], teacher_days={"Prof A": ["Mon"]}, teach_count={"Prof A": 1})
    lec = make_lecture(teachers=["Prof A"])
    assert teacher_availability.available_days(inst, lec) == set(inst.days)


def test_teacher_availability_drops_restriction_rather_than_empty(make_inst, make_lecture):
    inst = make_inst(
        [], teacher_days={"Prof A": ["Mon"], "Prof B": ["Fri"]},
        teach_count={"Prof A": 10, "Prof B": 10},
    )
    lec = make_lecture(teachers=["Prof A", "Prof B"])
    assert teacher_availability.available_days(inst, lec) == set(inst.days)


# H4 -----------------------------------------------------------------------

def test_course_daily_cap_applies_needs_shared_curriculum_and_course(make_lecture):
    # applies() returns a set (the shared curricula) or a falsy value, not a strict bool
    a = make_lecture(course_key="math", curricula=["g1"])
    b = make_lecture(course_key="math", curricula=["g1"])
    c = make_lecture(course_key="math", curricula=["g2"])
    assert course_daily_cap.applies(a, b)
    assert not course_daily_cap.applies(a, c)


def test_course_daily_cap_pairwise_respects_cap():
    cap = course_daily_cap.cap_for(2, 2)
    assert cap == 4  # MAX_COURSE_TIMESLOTS_PER_DAY
    assert course_daily_cap.pairwise(("Mon", 0), ("Mon", 5), 2, 2, cap) is True
    assert course_daily_cap.pairwise(("Mon", 0), ("Mon", 5), 3, 2, cap) is False
    assert course_daily_cap.pairwise(("Mon", 0), ("Tue", 0), 3, 3, cap) is True


def test_course_daily_cap_violations_detects_overload(make_inst, make_lecture):
    lectures = [make_lecture(curricula=["g1"], course_key="math", fach_id=str(i), length=2)
                for i in range(3)]
    inst = make_inst(lectures)
    solution = {0: ("Mon", 0), 1: ("Mon", 2), 2: ("Mon", 4)}  # 6 timeslots > cap of 4
    assert course_daily_cap.violations(inst, [0, 1, 2], solution) == [("Mon", 6)]


# H6 -----------------------------------------------------------------------

def test_contiguous_same_type_applies_only_to_same_teaching_type(make_lecture):
    # same lv_id/fach_id: two weekly meetings of one lecture series -- not a parallel group
    a = make_lecture(course_key="math", practical=False, curricula=["g1"])
    b = make_lecture(course_key="math", practical=False, curricula=["g1"])
    c = make_lecture(course_key="math", practical=True, curricula=["g1"])
    assert contiguous_same_type.applies(a, b)
    assert not contiguous_same_type.applies(a, c)


def test_contiguous_same_type_touching():
    assert contiguous_same_type.touching(("Mon", 0), ("Mon", 2), 2, 2) is True   # adjacent
    assert contiguous_same_type.touching(("Mon", 0), ("Mon", 1), 2, 2) is True   # overlapping
    assert contiguous_same_type.touching(("Mon", 0), ("Mon", 3), 2, 2) is False  # gap
    assert contiguous_same_type.touching(("Mon", 0), ("Tue", 0), 2, 2) is True   # different day


# H7 -----------------------------------------------------------------------

def test_no_late_mandatory_filters_late_timeslots():
    domain = [("Mon", 8), ("Mon", 9), ("Mon", 10), ("Mon", 11)]
    assert no_late_mandatory.filter_domain(domain, length=1) == [("Mon", 8), ("Mon", 9)]


def test_no_late_mandatory_falls_back_when_all_late():
    domain = [("Mon", 10), ("Mon", 11)]
    assert no_late_mandatory.filter_domain(domain, length=1) == domain


# H8 -----------------------------------------------------------------------

def test_curriculum_day_cap_curriculum_lectures(make_inst, make_lecture):
    inst = make_inst([make_lecture(curricula=["g1"]), make_lecture(curricula=["g2"])])
    assert curriculum_day_cap.curriculum_lectures(inst, "g1") == [0]


def test_curriculum_day_cap_build_constraint(make_inst, make_lecture):
    lectures = [make_lecture(curricula=["g1"], length=4) for _ in range(3)]
    inst = make_inst(lectures)
    check = curriculum_day_cap.build_constraint(inst, [0, 1, 2])
    assert check(("Mon", 0), ("Mon", 4), ("Mon", 8)) is False  # 12 timeslots > MAX_PER_DAY (10)
    assert check(("Mon", 0), ("Tue", 0), ("Wed", 0)) is True   # spread across days
