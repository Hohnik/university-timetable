"""The one place that knows data/instance.json's schema.

Scope matters: "cohort" is only a meaningful unit where the SPO makes
attendance compulsory. IF6 offers 22 courses totalling 52 slots a week and no
student attends all of them, so treating it as one block produces phantom
conflicts.
"""
from __future__ import annotations

import collections
import functools
import json
import pathlib
import re

import curriculum as CU
from constraints.hard import lecturer_availability

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_PATH = ROOT / "data" / "instance.json"


class Instance:
    def __init__(self, path=DEFAULT_PATH, scope=None, semester=None):
        raw = json.loads(path.read_text())
        self.days = raw["meta"]["days"]
        self.grid = raw["meta"]["grid"]
        self.cohorts = raw["cohorts"]
        self.lecturer_days = raw["lecturer_days"]

        keep = set(self.cohorts)
        if scope:
            keep &= {g for g, c in self.cohorts.items() if scope in c["program"]}
        if semester:
            keep &= {g for g, c in self.cohorts.items()
                     if c["label"].rstrip().endswith(str(semester))}

        sessions = []
        for s in raw["sessions"]:
            groups = [g for g in s["groups"] if g in keep]
            if groups:
                sessions.append(dict(s, groups=groups))
        self.sessions = sessions
        self.cohorts = {g: c for g, c in self.cohorts.items() if g in keep}
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
        """Per session: which cohorts MUST attend, and the subject family.

        `module_key` collapses "Mathematik II", "Prakt. Mathematik II" and
        "Übung Mathematik II" onto one key. Primuss files them as separate
        fach_ids, but to a student they are one subject, which is the level
        at which daily-load rules have to apply.
        """
        plan = {}
        for g, c in self.cohorts.items():
            m = re.search(r"(\d)", c["label"])
            sem = int(m.group(1)) if m else None
            plan[g] = [self._norm(n) for n in CU.mandatory_names(c["program"], sem)]

        for s in self.sessions:
            name = self._norm(s["course"])
            required = []
            for g in s["groups"]:
                for mod in plan.get(g, []):
                    if (name == mod or name.startswith(mod) or mod.startswith(name)
                            or (len(set(name.split()) & set(mod.split())) >= 2
                                and abs(len(name) - len(mod)) < 25)):
                        required.append(g)
                        break
            s["required_by"] = required
            s["elective"] = not required
            s["module_key"] = name
            # A subject's LECTURE must not be split across a day, but a
            # lecture and its practical legitimately can be (see H6/S7).
            s["practical"] = bool(re.match(
                r"^(prakt\.?|praktikum|übung|ue\.?|ln)\b", s["course"].strip().lower()))

    @functools.cached_property
    def teach_count(self):
        return collections.Counter(p for s in self.sessions for p in s["lecturers"])

    def available_days(self, session):
        return lecturer_availability.available_days(self, session)

    def label(self, group):
        return self.cohorts[group]["label"]
