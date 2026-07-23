"""H2: a lecturer cannot teach two sessions at once."""


def conflicts(a, b):
    return set(a["lecturers"]) & set(b["lecturers"])
