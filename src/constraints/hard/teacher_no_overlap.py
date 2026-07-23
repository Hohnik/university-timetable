"""H2: a teacher cannot teach two lectures at once."""


def conflicts(a, b):
    return set(a["teachers"]) & set(b["teachers"])
