"""H1: a cohort cannot attend two sessions mandatory for it at the same time."""


def conflicts(a, b):
    """Cohorts for which both sessions are mandatory — the only unbreakable
    cohort rule; overlapping electives are allowed (see soft.elective_vs_mandatory)."""
    return set(a["required_by"]) & set(b["required_by"])
