"""H1: a curriculum cannot attend two lectures mandatory for it at the same time."""


def conflicts(a, b):
    """Curricula for which both lectures are mandatory — the only unbreakable
    curriculum rule; overlapping electives are allowed (see soft.elective_vs_mandatory)."""
    return set(a["required_by"]) & set(b["required_by"])
