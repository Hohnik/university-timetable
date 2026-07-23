import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import curriculum as CU
    from instance import Instance
    from solve import search_adaptive, to_records, validate
    return CU, Instance, search_adaptive, to_records, validate


@app.cell
def _(CU, mo):
    program = mo.ui.dropdown(options=sorted(CU.MANDATORY), value="Bachelor Informatik", label="Program")
    semester = mo.ui.dropdown(options=[2, 4, 6], value=2, label="Semester")
    seconds = mo.ui.number(start=5, stop=60, step=5, value=15, label="Search seconds")
    mo.hstack([program, semester, seconds])
    return program, seconds, semester


@app.cell
def _(Instance, program, semester):
    inst = Instance(scope=program.value, semester=semester.value)
    return (inst,)


@app.cell
def _(inst, search_adaptive, seconds):
    best, score, pen, seen, restarts, mode = search_adaptive(inst, seconds.value)
    return best, mode, restarts, score, seen


@app.cell
def _(best, inst, mo, to_records, validate):
    if best is None:
        mo.md("**No timetable found** — try increasing the search time.")
    else:
        records = to_records(inst, best)
        errors = validate(inst, best)
        tables = [
            mo.vstack([mo.md(f"### {cohort}"),
                       mo.ui.table([r for r in records if r["cohort"] == cohort])])
            for cohort in dict.fromkeys(r["cohort"] for r in records)
        ]
        status = mo.md(f"---\n{len(errors)} hard violation(s)" if errors else "---\nhard validation OK")
        mo.vstack(tables + [status])
    return


@app.cell
def _(mo, mode, restarts, score, seen):
    mo.md(f"solver: {mode} · {seen} timetables seen · {restarts} restarts · soft penalty {score}")
    return


if __name__ == "__main__":
    app.run()
