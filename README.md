# University Timetable

Generates conflict-free weekly timetables for HS Landshut degree programs from real [Primuss](https://www3.primuss.de) scheduling data, using constraint satisfaction.

## How it works

```
fetch → extract → solve / notebook
```

- **Fetch** — authenticate against Primuss (Shibboleth SSO) and scrape the raw timetable
- **Extract** — collapse raw events into a clean scheduling instance: sessions, professors, courses, hours/week — cross-referenced against each program's SPO to tell mandatory modules from electives
- **Solve** — model one CSP variable per weekly session (day + 45-minute block), search for the best assignment under a set of hard and soft rules ([full catalogue](constraints.md)), and validate the result independently of the solver
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
├── curriculum.py        # SPO mandatory-module data, per program
├── instance.py          # data/instance.json schema + curriculum tagging
├── solve.py             # CSP build, search, scoring, CLI
├── main.py              # marimo notebook
└── constraints/
    ├── hard/             # one file per hard rule (H1-H8)
    └── soft/             # one file per soft rule (S2-S8)
```
