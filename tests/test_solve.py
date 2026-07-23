"""Integration/regression tests: real Instance + solve.py working together
against a small fixed fixture, independent of live HS Landshut data."""
from pathlib import Path

import pytest

import curriculum as CU
from instance import Instance
from solve import build_problem, soft_score, to_records, validate

FIXTURE = Path(__file__).parent / "fixtures" / "instance.json"


@pytest.fixture
def inst(monkeypatch):
    monkeypatch.setitem(CU.MANDATORY, "Test Program", {
        2: [("T1", "Mathematik", 5, 4), ("T2", "Programmieren", 5, 4)],
    })
    return Instance(path=FIXTURE, semester=2)


def test_instance_tags_mandatory_vs_elective_from_curriculum(inst):
    by_course = {s["course"]: s for s in inst.sessions}
    assert by_course["Mathematik"]["required_by"] == ["g1"]
    assert by_course["Programmieren"]["required_by"] == ["g1"]
    assert by_course["Wahlfach"]["required_by"] == []
    assert by_course["Wahlfach"]["elective"] is True


def test_validate_flags_mandatory_clash(inst):
    # Mathematik and Programmieren are both mandatory for g1 -- can't overlap
    solution = {0: ("Mon", 0), 1: ("Mon", 0), 2: ("Tue", 0)}
    errors = validate(inst, solution)
    assert any("H1 mandatory clash" in e for e in errors)


def test_validate_ok_for_conflict_free_solution(inst):
    solution = {0: ("Mon", 0), 1: ("Tue", 2), 2: ("Wed", 4)}
    assert validate(inst, solution) == []


def test_soft_score_penalizes_late_slot(inst):
    solution = {0: ("Mon", 0), 1: ("Tue", 2), 2: ("Wed", 10)}
    score, pen = soft_score(inst, solution)
    assert score > 0
    assert any(msg.startswith("S4 late slot") for _, msg in pen)


def test_build_problem_produces_a_valid_solution(inst):
    solution = build_problem(inst).getSolution()
    assert solution is not None
    assert validate(inst, solution) == []


def test_to_records_produces_uniform_format(inst):
    solution = {0: ("Mon", 0), 1: ("Tue", 2), 2: ("Wed", 4)}
    records = to_records(inst, solution)
    assert {r["course"] for r in records} == {"Mathematik", "Programmieren", "Wahlfach"}
    assert all({"cohort", "day", "start", "end", "course", "lecturer", "kind"} <= r.keys()
               for r in records)
