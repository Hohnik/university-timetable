from constraints import grid


def test_occupies_spans_consecutive_timeslots():
    assert grid.occupies(("Mon", 2), 3) == {("Mon", 2), ("Mon", 3), ("Mon", 4)}


def test_blocks_false_for_different_days():
    assert grid.blocks(("Mon", 2), ("Tue", 2), 2, 2) is False


def test_blocks_true_for_overlapping_same_day():
    assert grid.blocks(("Mon", 0), ("Mon", 1), 2, 2) is True


def test_blocks_false_when_adjacent_not_overlapping():
    assert grid.blocks(("Mon", 0), ("Mon", 2), 2, 2) is False


def test_is_parallel_same_course_different_lecture():
    a = {"fach_id": "1", "lv_id": "a"}
    b = {"fach_id": "1", "lv_id": "b"}
    assert grid.is_parallel(a, b) is True


def test_is_parallel_false_for_different_course():
    a = {"fach_id": "1", "lv_id": "a"}
    b = {"fach_id": "2", "lv_id": "b"}
    assert grid.is_parallel(a, b) is False


def test_lecture_pairs_yields_every_unordered_pair():
    lectures = [{"id": 0}, {"id": 1}, {"id": 2}]
    assert [(i, j) for i, j, _, _ in grid.lecture_pairs(lectures)] == [(0, 1), (0, 2), (1, 2)]


def test_curriculum_day_timeslots_only_counts_that_curriculum_and_day(make_inst, make_lecture):
    s0 = make_lecture(curricula=["g1"], length=2)
    s1 = make_lecture(curricula=["g1"], length=1)
    s2 = make_lecture(curricula=["g2"], length=1)  # different curriculum, ignored
    inst = make_inst([s0, s1, s2])
    solution = {0: ("Mon", 0), 1: ("Mon", 5), 2: ("Mon", 1)}
    assert grid.curriculum_day_timeslots(inst, solution, "g1", "Mon") == [0, 1, 5]
