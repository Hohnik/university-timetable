from . import (
    avoid_late_slot,
    minimize_daily_gaps,
    lecturer_daily_load,
    reward_free_day,
    avoid_long_days,
    keep_lecture_practical_together,
    elective_vs_mandatory,
)

RULES = [
    avoid_late_slot.penalties,
    minimize_daily_gaps.penalties,
    lecturer_daily_load.penalties,
    reward_free_day.penalties,
    avoid_long_days.penalties,
    keep_lecture_practical_together.penalties,
    elective_vs_mandatory.penalties,
]
