# University Timetable

Generates conflict-free weekly timetables for HS Landshut degree programs from real [Primuss](https://www3.primuss.de) scheduling data, using constraint satisfaction. Modeled as Curriculum-Based Course Timetabling (CB-CTT, Di Gaspero & Schaerf 2003 / ITC-2007): courses made of lectures taught by teachers, curricula grouping the courses that share students and therefore conflict.

## How it works

```
fetch → extract → solve / notebook
```

- **Fetch** — authenticate against Primuss (Shibboleth SSO) and scrape the raw timetable
- **Extract** — collapse raw events into a clean scheduling instance: lectures, teachers, courses, hours/week — cross-referenced against each program's SPO to tell mandatory courses from electives. Scoped to the IF (Informatik) and SA (Soziale Arbeit) faculties via `FACULTIES` in `src/extract_instance.py`, the two `src/curriculum.py` has SPO data for; other fetched faculties sit in `raw/` unextracted until their SPOs are transcribed too
- **Solve** — model one CSP variable per weekly lecture (day + 45-minute timeslot), search for the best assignment under a set of hard and soft rules ([full catalogue](constraints.md)), and validate the result independently of the solver
- **Notebook** — a [marimo](https://marimo.io) app to pick a program/semester and see the generated timetable instantly, no restart needed

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```sh
uv sync
cp .env.example .env   # USERNAME, PASSWORD, TOTP_SECRET — only needed for `just fetch`
```

## Usage

| command | what it does |
|---|---|
| `just fetch` | scrape raw timetable data from Primuss into `raw/` |
| `just extract` | turn `raw/` into `data/instance.json` |
| `just solve <semester>` | solve and print a timetable from the CLI |
| `just notebook` | open the interactive marimo notebook |
| `just test` | run the test suite |

## Project structure

```
src/
├── fetch_primuss.py     # Primuss auth + scrape
├── extract_instance.py  # raw events -> data/instance.json
├── curriculum.py        # SPO mandatory-course data, per program
├── instance.py          # data/instance.json schema + curriculum tagging
├── solve.py             # CSP build, search, scoring, CLI
├── main.py              # marimo notebook
└── constraints/
    ├── hard/             # one file per hard rule (H1-H8)
    │   ├── curriculum_no_overlap.py    # H1
    │   ├── teacher_no_overlap.py       # H2
    │   ├── teacher_availability.py     # H3
    │   ├── course_daily_cap.py         # H4
    │   ├── contiguous_same_type.py     # H6
    │   ├── no_late_mandatory.py        # H7
    │   └── curriculum_day_cap.py       # H8
    └── soft/             # one file per soft rule (S2-S8)
        ├── minimize_daily_gaps.py
        ├── teacher_daily_load.py
        ├── avoid_late_slot.py
        ├── reward_free_day.py
        ├── avoid_long_days.py
        ├── keep_lecture_practical_together.py
        └── elective_vs_mandatory.py
```
