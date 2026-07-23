"""Tunable constants shared across constraint rules.

Grid timeslots are 45 minutes, indexed 0-11 across a teaching day:
  0  08:45-09:30    4  12:50-13:35     8  16:10-16:55
  1  09:30-10:15    5  13:35-14:20     9  16:55-17:40
  -- break --       -- break --        -- break --
  2  10:30-11:15    6  14:30-15:15    10  17:50-18:35
  3  11:15-12:00    7  15:15-16:00    11  18:35-19:20
  -- lunch 12:00-12:50 --
The 15-minute breaks and the lunch sit between adjacent timeslot indices, so a
lecture spanning one costs no timeslot and never registers as an idle gap.
"""

# H3: a teacher must have taught at least this many lectures before their
# observed teaching days are trusted enough to restrict their availability.
MIN_AVAILABILITY_EVIDENCE = 6

# H4: at most this many 45-minute timeslots (~3h) of one course per curriculum per day.
MAX_COURSE_TIMESLOTS_PER_DAY = 4

# H8 / S6: at most this many 45-minute timeslots (~7.5h) of teaching per curriculum per day.
MAX_PER_DAY = 10

# H7 / S4: the day's last teaching timeslot (17:50-19:20) — unpopular, avoided where possible.
LATE_TIMESLOTS = {10, 11}
