"""Shared fixtures. Most constraint files only need duck-typed sessions/instances,
not a real Instance loaded from JSON + curriculum -- these keep unit tests fast
and independent of real HS Landshut data."""
from types import SimpleNamespace

import pytest


def _session(**over):
    base = dict(
        id="s", lv_id="1", fach_id="1", course="Course", short="C",
        lecturers=["Prof A"], groups=["g1"], length=2, rhythm="1",
        occurrences=10, published={"day": "Mon", "slot": 0},
        required_by=[], elective=True, module_key="course", practical=False,
    )
    base.update(over)
    return base


@pytest.fixture
def make_session():
    return _session


@pytest.fixture
def make_inst():
    def _make(sessions, cohorts=None, days=None, lecturer_days=None, teach_count=None):
        cohorts = cohorts or {}
        return SimpleNamespace(
            sessions=sessions,
            cohorts=cohorts,
            days=days or ["Mon", "Tue", "Wed", "Thu", "Fri"],
            lecturer_days=lecturer_days or {},
            teach_count=teach_count or {},
            label=lambda g: cohorts.get(g, {}).get("label", g),
        )
    return _make
