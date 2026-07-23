"""The one place that knows data/instance.json's schema.

Scope matters: "curriculum" is only a meaningful unit where the SPO makes
attendance compulsory. IF6 offers 22 courses totalling 52 timeslots a week
and no student attends all of them, so treating it as one curriculum
produces phantom conflicts.
"""
from __future__ import annotations

import collections
import functools
import json
import pathlib
import re

import curriculum as CU
from constraints.hard import teacher_availability

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "instance.json"


class Instance:
    def __init__(self, path=DEFAULT_PATH, scope=None, semester=None):
        raw = json.loads(path.read_text())
        self.days = raw["meta"]["days"]
        self.grid = raw["meta"]["grid"]
        self.curricula = raw["curricula"]
        self.teacher_days = raw["teacher_days"]

        keep = set(self.curricula)
        if scope:
            keep &= {g for g, c in self.curricula.items() if scope in c["program"]}
        if semester:
            keep &= {g for g, c in self.curricula.items()
                     if c["label"].rstrip().endswith(str(semester))}

        lectures = []
        for lec in raw["lectures"]:
            curricula = [g for g in lec["curricula"] if g in keep]
            if curricula:
                lectures.append(dict(lec, curricula=curricula))
        self.lectures = lectures
        self.curricula = {g: c for g, c in self.curricula.items() if g in keep}
        self._tag_curriculum()

    # -- curriculum ------------------------------------------------------
    @staticmethod
    def _norm(text):
        text = text.lower()
        text = re.sub(r"^(prakt\.?|praktikum|übung|ue\.?|ln)\s+", "", text)
        for a, b in (("ä", "a"), ("ö", "o"), ("ü", "u"), ("ß", "ss")):
            text = text.replace(a, b)
        return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text)).strip()

    def _tag_curriculum(self):
        """Per lecture: which curricula MUST attend, and the course family.

        `course_key` collapses "Mathematik II", "Prakt. Mathematik II" and
        "Übung Mathematik II" onto one key. Primuss files them as separate
        fach_ids, but to a student they are one course, which is the level
        at which daily-load rules have to apply.
        """
        plan = {}
        for g, c in self.curricula.items():
            m = re.search(r"(\d)", c["label"])
            sem = int(m.group(1)) if m else None
            plan[g] = [self._norm(n) for n in CU.mandatory_names(c["program"], sem)]

        for lec in self.lectures:
            name = self._norm(lec["course"])
            required = []
            for g in lec["curricula"]:
                for mod in plan.get(g, []):
                    if (name == mod or name.startswith(mod) or mod.startswith(name)
                            or (len(set(name.split()) & set(mod.split())) >= 2
                                and abs(len(name) - len(mod)) < 25)):
                        required.append(g)
                        break
            lec["required_by"] = required
            lec["elective"] = not required
            lec["course_key"] = name
            # A course's LECTURE must not be split across a day, but a
            # lecture and its practical legitimately can be (see H6/S7).
            lec["practical"] = bool(re.match(
                r"^(prakt\.?|praktikum|übung|ue\.?|ln)\b", lec["course"].strip().lower()))

    @functools.cached_property
    def teach_count(self):
        return collections.Counter(p for lec in self.lectures for p in lec["teachers"])

    def available_days(self, lecture):
        return teacher_availability.available_days(self, lecture)

    def label(self, curriculum):
        return self.curricula[curriculum]["label"]
