from constraints.hard import (
    cohort_day_cap,
    cohort_no_overlap,
    contiguous_same_type,
    lecturer_availability,
    lecturer_no_overlap,
    module_daily_cap,
    no_late_mandatory,
)


# H1 -----------------------------------------------------------------------

def test_cohort_no_overlap_conflicts_only_where_both_mandatory(make_session):
    a = make_session(required_by=["g1", "g2"])
    b = make_session(required_by=["g2", "g3"])
    assert cohort_no_overlap.conflicts(a, b) == {"g2"}


def test_cohort_no_overlap_ignores_electives(make_session):
    a = make_session(required_by=["g1"])
    b = make_session(required_by=[])
    assert cohort_no_overlap.conflicts(a, b) == set()


# H2 -----------------------------------------------------------------------

def test_lecturer_no_overlap_conflicts(make_session):
    a = make_session(lecturers=["Prof A", "Prof B"])
    b = make_session(lecturers=["Prof B"])
    assert lecturer_no_overlap.conflicts(a, b) == {"Prof B"}


# H3 -----------------------------------------------------------------------

def test_lecturer_availability_restricts_with_enough_evidence(make_inst, make_session):
    inst = make_inst([], lecturer_days={"Prof A": ["Mon", "Tue"]}, teach_count={"Prof A": 10})
    s = make_session(lecturers=["Prof A"])
    assert lecturer_availability.available_days(inst, s) == {"Mon", "Tue"}


def test_lecturer_availability_ignores_thin_evidence(make_inst, make_session):
    inst = make_inst([], lecturer_days={"Prof A": ["Mon"]}, teach_count={"Prof A": 1})
    s = make_session(lecturers=["Prof A"])
    assert lecturer_availability.available_days(inst, s) == set(inst.days)


def test_lecturer_availability_drops_restriction_rather_than_empty(make_inst, make_session):
    inst = make_inst(
        [], lecturer_days={"Prof A": ["Mon"], "Prof B": ["Fri"]},
        teach_count={"Prof A": 10, "Prof B": 10},
    )
    s = make_session(lecturers=["Prof A", "Prof B"])
    assert lecturer_availability.available_days(inst, s) == set(inst.days)


# H4 -----------------------------------------------------------------------

def test_module_daily_cap_applies_needs_shared_group_and_module(make_session):
    # applies() returns a set (the shared groups) or a falsy value, not a strict bool
    a = make_session(module_key="math", groups=["g1"])
    b = make_session(module_key="math", groups=["g1"])
    c = make_session(module_key="math", groups=["g2"])
    assert module_daily_cap.applies(a, b)
    assert not module_daily_cap.applies(a, c)


def test_module_daily_cap_pairwise_respects_cap():
    cap = module_daily_cap.cap_for(2, 2)
    assert cap == 4  # MAX_MODULE_BLOCKS_PER_DAY
    assert module_daily_cap.pairwise(("Mon", 0), ("Mon", 5), 2, 2, cap) is True
    assert module_daily_cap.pairwise(("Mon", 0), ("Mon", 5), 3, 2, cap) is False
    assert module_daily_cap.pairwise(("Mon", 0), ("Tue", 0), 3, 3, cap) is True


def test_module_daily_cap_violations_detects_overload(make_inst, make_session):
    sessions = [make_session(groups=["g1"], module_key="math", fach_id=str(i), length=2)
                for i in range(3)]
    inst = make_inst(sessions)
    solution = {0: ("Mon", 0), 1: ("Mon", 2), 2: ("Mon", 4)}  # 6 slots > cap of 4
    assert module_daily_cap.violations(inst, [0, 1, 2], solution) == [("Mon", 6)]


# H6 -----------------------------------------------------------------------

def test_contiguous_same_type_applies_only_to_same_teaching_type(make_session):
    # same lv_id/fach_id: two weekly meetings of one lecture series -- not a parallel group
    a = make_session(module_key="math", practical=False, groups=["g1"])
    b = make_session(module_key="math", practical=False, groups=["g1"])
    c = make_session(module_key="math", practical=True, groups=["g1"])
    assert contiguous_same_type.applies(a, b)
    assert not contiguous_same_type.applies(a, c)


def test_contiguous_same_type_touching():
    assert contiguous_same_type.touching(("Mon", 0), ("Mon", 2), 2, 2) is True   # adjacent
    assert contiguous_same_type.touching(("Mon", 0), ("Mon", 1), 2, 2) is True   # overlapping
    assert contiguous_same_type.touching(("Mon", 0), ("Mon", 3), 2, 2) is False  # gap
    assert contiguous_same_type.touching(("Mon", 0), ("Tue", 0), 2, 2) is True   # different day


# H7 -----------------------------------------------------------------------

def test_no_late_mandatory_filters_late_slots():
    domain = [("Mon", 8), ("Mon", 9), ("Mon", 10), ("Mon", 11)]
    assert no_late_mandatory.filter_domain(domain, length=1) == [("Mon", 8), ("Mon", 9)]


def test_no_late_mandatory_falls_back_when_all_late():
    domain = [("Mon", 10), ("Mon", 11)]
    assert no_late_mandatory.filter_domain(domain, length=1) == domain


# H8 -----------------------------------------------------------------------

def test_cohort_day_cap_cohort_sessions(make_inst, make_session):
    inst = make_inst([make_session(groups=["g1"]), make_session(groups=["g2"])])
    assert cohort_day_cap.cohort_sessions(inst, "g1") == [0]


def test_cohort_day_cap_build_constraint(make_inst, make_session):
    sessions = [make_session(groups=["g1"], length=4) for _ in range(3)]
    inst = make_inst(sessions)
    check = cohort_day_cap.build_constraint(inst, [0, 1, 2])
    assert check(("Mon", 0), ("Mon", 4), ("Mon", 8)) is False  # 12 slots > MAX_PER_DAY (10)
    assert check(("Mon", 0), ("Tue", 0), ("Wed", 0)) is True   # spread across days
