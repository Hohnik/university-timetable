"""Shared fixtures. Most constraint files only need duck-typed lectures/instances,
not a real Instance loaded from JSON + curriculum -- these keep unit tests fast
and independent of real HS Landshut data."""
from types import SimpleNamespace

import pytest


def _lecture(**over):
    base = dict(
        id="s", lv_id="1", fach_id="1", course="Course", short="C",
        teachers=["Prof A"], curricula=["g1"], length=2, rhythm="1",
        occurrences=10, published={"day": "Mon", "timeslot": 0},
        required_by=[], elective=True, course_key="course", practical=False,
    )
    base.update(over)
    return base


@pytest.fixture
def make_lecture():
    return _lecture


@pytest.fixture
def make_inst():
    def _make(lectures, curricula=None, days=None, teacher_days=None, teach_count=None):
        curricula = curricula or {}
        return SimpleNamespace(
            lectures=lectures,
            curricula=curricula,
            days=days or ["Mon", "Tue", "Wed", "Thu", "Fri"],
            teacher_days=teacher_days or {},
            teach_count=teach_count or {},
            label=lambda g: curricula.get(g, {}).get("label", g),
        )
    return _make
