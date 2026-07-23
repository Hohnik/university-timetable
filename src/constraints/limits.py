"""Tunable constants shared across constraint rules.

Grid blocks are 45 minutes, indexed 0-11 across a teaching day:
  0  08:45-09:30    4  12:50-13:35     8  16:10-16:55
  1  09:30-10:15    5  13:35-14:20     9  16:55-17:40
  -- break --       -- break --        -- break --
  2  10:30-11:15    6  14:30-15:15    10  17:50-18:35
  3  11:15-12:00    7  15:15-16:00    11  18:35-19:20
  -- lunch 12:00-12:50 --
The 15-minute breaks and the lunch sit between adjacent block indices, so a
session spanning one costs no block and never registers as an idle gap.
"""

# H3: a lecturer must have taught at least this many sessions before their
# observed teaching days are trusted enough to restrict their availability.
MIN_AVAILABILITY_EVIDENCE = 6

# H4: at most this many 45-minute blocks (~3h) of one subject per cohort per day.
MAX_MODULE_BLOCKS_PER_DAY = 4

# H8 / S6: at most this many 45-minute blocks (~7.5h) of teaching per cohort per day.
MAX_PER_DAY = 10

# H7 / S4: the day's last teaching slot (17:50-19:20) — unpopular, avoided where possible.
LATE_BLOCKS = {10, 11}
