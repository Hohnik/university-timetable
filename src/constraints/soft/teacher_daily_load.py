"""S3: a teacher teaching more than 2 lectures a day is penalized progressively."""
import collections


def penalties(inst, solution):
    per = collections.Counter()
    for i, lec in enumerate(inst.lectures):
        for p in lec["teachers"]:
            per[(p, solution[i][0])] += 1
    return [(5 * (n - 2), f"S3 overload: {p} {n} lectures {day}")
            for (p, day), n in per.items() if n > 2]
