"""S3: a lecturer teaching more than 2 sessions a day is penalized progressively."""
import collections


def penalties(inst, solution):
    per = collections.Counter()
    for i, s in enumerate(inst.sessions):
        for p in s["lecturers"]:
            per[(p, solution[i][0])] += 1
    return [(5 * (n - 2), f"S3 overload: {p} {n} sessions {day}")
            for (p, day), n in per.items() if n > 2]
