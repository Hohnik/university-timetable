import extract_instance as ei


def test_block_of_start_snaps_within_tolerance():
    assert ei.block_of_start("08:45") == 0
    assert ei.block_of_start("08:50") == 0


def test_block_of_start_none_when_too_far_off():
    assert ei.block_of_start("23:00") is None


def test_block_of_end_snaps_to_nearest():
    assert ei.block_of_end("09:30") == 0
    assert ei.block_of_end("10:15") == 1


def test_block_span_absorbs_internal_breaks():
    # 08:45-12:00 crosses the 10:15-10:30 break but is still 4 consecutive blocks
    assert ei.block_span("08:45", "12:00") == (0, 4)


def test_dedupe_merges_same_lesson_across_groups():
    events = [
        {"lv_id": "1", "dtstart": "2026-03-16T08:45:00", "_stgru": "10"},
        {"lv_id": "1", "dtstart": "2026-03-16T08:45:00", "_stgru": "20"},
    ]
    merged = ei.dedupe(events)
    assert len(merged) == 1
    assert merged[0]["_groups"] == {"10", "20"}
    assert "_stgru" not in merged[0]


def test_lecturer_availability_orders_days_chronologically():
    sessions = [
        {"lecturers": ["Prof A"], "published": {"day": "Wed"}},
        {"lecturers": ["Prof A"], "published": {"day": "Mon"}},
    ]
    assert ei.lecturer_availability(sessions) == {"Prof A": ["Mon", "Wed"]}


def test_report_aggregates_hours_per_week_with_fortnightly_halved():
    sessions = [
        {"lecturers": ["Prof A"], "course": "Math", "length": 2, "rhythm": "1"},
        {"lecturers": ["Prof A"], "course": "Math", "length": 2, "rhythm": "14"},
    ]
    summary = ei.report(sessions)
    assert summary["professors"] == ["Prof A"]
    assert summary["courses"] == ["Math"]
    expected_hours = (2 + 2 * 0.5) * ei.BLOCK_HOURS
    assert summary["course_hours_per_week"]["Math"] == expected_hours
    assert summary["professor_hours_per_week"]["Prof A"] == expected_hours
