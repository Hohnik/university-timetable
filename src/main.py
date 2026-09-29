import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # HS Landshut Timetable

    Pick a program and semester (or solve the whole faculty at once), choose a
    solver, and generate a conflict-free weekly timetable. See
    [constraints.md](../constraints.md) for the full hard/soft rule catalogue.
    """)
    return


@app.cell
def _():
    import curriculum as CU
    from instance import Instance
    from solve import published_solution, search_adaptive, soft_score, to_records, validate
    from solve_cpsat import search_adaptive_cpsat

    return (
        CU,
        Instance,
        published_solution,
        search_adaptive,
        search_adaptive_cpsat,
        soft_score,
        to_records,
        validate,
    )


@app.cell
def _(CU, mo):
    program = mo.ui.dropdown(options=sorted(CU.MANDATORY), value="Bachelor Informatik", label="Program")
    all_scope = mo.ui.checkbox(value=False, label="Whole faculty (ignore program/semester)")
    solver_choice = mo.ui.radio(
        options=["MinConflicts", "CP-SAT"], value="MinConflicts", label="Solver",
        inline=True,
    )
    seconds = mo.ui.number(start=5, stop=120, step=5, value=15, label="Search seconds")
    mo.hstack([program, all_scope, solver_choice, seconds])
    return all_scope, program, seconds, solver_choice


@app.cell
def _(CU, mo, program):
    semester_options = sorted(CU.MANDATORY[program.value])
    semester = mo.ui.dropdown(
        options=semester_options, value=semester_options[0], label="Semester")
    show_published = mo.ui.checkbox(value=False, label="Compare to the real published timetable")
    mo.hstack([semester, show_published])
    return semester, show_published


@app.cell
def _(Instance, all_scope, program, semester):
    inst = Instance() if all_scope.value else Instance(scope=program.value, semester=semester.value)
    return (inst,)


@app.cell
def _():
    def records_to_md(rows, columns):
        header = "| " + " | ".join(columns) + " |\n" + "|" + "|".join(["---"] * len(columns)) + "|"
        body = "\n".join(
            "| " + " | ".join(str(r.get(c, "")) for c in columns) + " |" for r in rows
        )
        return header + "\n" + body if rows else header

    return (records_to_md,)


@app.cell
def _(inst, mo):
    n_mand = sum(1 for lec in inst.lectures if lec["required_by"])
    faculties = "+".join(sorted({c["faculty"] for c in inst.curricula.values()}))
    mo.md(f"""
    **Scope:** faculty {faculties} · {len(inst.curricula)} curricula

    {len(inst.lectures)} lectures ({n_mand} mandatory, {len(inst.lectures) - n_mand} elective) ·
    {len({p for lec in inst.lectures for p in lec['teachers']})} teachers
    """)
    return


@app.cell
def _(
    inst,
    search_adaptive,
    search_adaptive_cpsat,
    seconds,
    soft_score,
    solver_choice,
):
    if solver_choice.value == "CP-SAT":
        best, mode = search_adaptive_cpsat(inst, seconds.value)
        seen = restarts = None
    else:
        best, _score, _pen, seen, restarts, mode = search_adaptive(inst, seconds.value)
    score, pen = soft_score(inst, best) if best is not None else (0, [])
    return best, mode, pen, restarts, score, seen


@app.cell
def _(best, inst, mo, records_to_md, to_records, validate):
    if best is None:
        mo.md("**No timetable found** — try increasing the search time or widening the scope.")
    else:
        records = to_records(inst, best)
        errors = validate(inst, best)
        sections = []
        for curriculum in dict.fromkeys(r["curriculum"] for r in records):
            rows = [r for r in records if r["curriculum"] == curriculum]
            _table_md = records_to_md(rows, ["day", "start", "end", "course", "teacher", "kind"])
            sections.append(mo.md(f"### {curriculum}\n\n{_table_md}"))
        if errors:
            status = mo.vstack(
                [mo.md(f"---\n**{len(errors)} hard violation(s):**")]
                + [mo.md(f"- {e}") for e in errors[:20]]
            )
        else:
            status = mo.md("---\n**Hard validation: OK** — no violations")
        mo.vstack(sections + [status])
    return


@app.cell
def _(best, mo, pen, records_to_md, score):
    if best is None:
        mo.md("")
    else:
        top = sorted(pen, reverse=True)[:15]
        _table_md = records_to_md(
            [{"points": p, "reason": text} for p, text in top], ["points", "reason"])
        mo.md(f"### Soft penalty: {score}\n\n{_table_md}")
    return


@app.cell
def _(best, mo, mode, restarts, seen):
    if best is None:
        mo.md("")
    else:
        detail = f"{seen} timetables seen · {restarts} restarts · " if seen is not None else ""
        mo.md(f"solver: {mode} · {detail}")
    return


@app.cell
def _(inst, mo, published_solution, show_published, soft_score, validate):
    if not show_published.value:
        mo.md("")
    else:
        pub_sol = published_solution(inst)
        pub_errors = validate(inst, pub_sol)
        pub_score, _pub_pen = soft_score(inst, pub_sol)
        mo.md(f"""
        ---
        **Published (real) timetable, for comparison:** {len(pub_errors)} hard violation(s),
        soft penalty {pub_score}
        """)
    return


if __name__ == "__main__":
    app.run()
