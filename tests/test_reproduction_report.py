"""Informe de reproducción (`validation/reproduction.py`) con salidas sintéticas.

No necesita los datos confidenciales: las "salidas" de los scripts se construyen a partir de las
propias tablas impresas del paper (`reference/paper_tables/`), de modo que el informe completo sale
en ✅ y cada prueba rompe UNA cosa para ver que el informe la detecta.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.figures.marginal_effects import FIGURES, figure_data
from lastmile_exposure.validation.paper_tables import (
    TABLE2_TOLERANCES,
    column_summary,
    compare_columns,
    load_fig7_bars,
    load_table2,
    load_table4,
    load_table5,
)
from lastmile_exposure.validation.reproduction import (
    Context,
    Item,
    Report,
    Status,
    build_report,
    is_stale,
)

MARGINAL = {c: 6e-5 for c in ("zinb", "ols_k", "ols_kpos", "ols_logk")}
STAR_TABLES = {"dynamic": load_table4, "static": load_table5}


def _write(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _inference_like(printed: pd.DataFrame) -> pd.DataFrame:
    out = printed.copy()
    for col in ("zinb", "ols_k", "ols_kpos", "ols_logk"):
        out[f"{col}_p"] = 0.5
    return out


@pytest.fixture
def ctx(tmp_path):
    """Salidas completas y perfectas: el informe debe salir sin fallas."""
    tables, figures, local = tmp_path / "tables", tmp_path / "figures", tmp_path / "local"
    _write(
        tables / "comparison_table2.csv",
        column_summary(compare_columns(load_table2(), load_table2(), TABLE2_TOLERANCES)),
    )
    for number, loader in ((4, load_table4), (5, load_table5)):
        _write(
            tables / f"comparison_table{number}.csv",
            column_summary(compare_columns(loader(), loader(), MARGINAL)),
        )
    for name in ("median_counts_check", "median_distance_check"):
        _write(
            tables / f"{name}.csv",
            pd.DataFrame(
                {
                    "check": ["a", "b"],
                    "identical": [True, True],
                    "n_rows": 178304,
                    "n_expected": 178304,
                    "max_abs_diff": [0.0, 3e-11],
                }
            ),
        )
    for tag, variant in (("dynamic", "paper_text"), ("static", "authors_script")):
        _write(tables / f"inference_{tag}_{variant}.csv", _inference_like(STAR_TABLES[tag]()))
        ok = [True] * (23 if tag == "dynamic" else 38) + [False] * (
            44 - (23 if tag == "dynamic" else 38)
        )
        _write(tables / f"stars_{tag}_{variant}.csv", pd.DataFrame({"ok": ok}))
    _write(
        tables / "cameron_trivedi.csv",
        pd.DataFrame(
            {
                "tabla": ["dynamic", "static"],
                "dispersion": [7.75, 7.49],
                "paper": [7.73, float("nan")],
                "abs_diff": [0.02, float("nan")],
                "limit": [0.0773, float("nan")],
            }
        ),
    )
    _write(
        tables / "moran.csv",
        pd.DataFrame(
            {
                "rol": ["principal", "principal", "alternativa"],
                "variable": ["distancia", "vehiculos", "distancia"],
                "moran_i": [0.41901, 0.42966, 0.466],
            }
        ),
    )
    groups = [label for label, _, _ in config.TABLE2_GROUPS]
    _write(
        tables / "table2_mobility_seeds.csv",
        pd.DataFrame({"group": groups, "inside_band": [g not in ("D", "E") for g in groups]}),
    )
    _write(
        tables / "zero_inflation.csv",
        pd.DataFrame(
            {
                "tabla": ["dynamic", "static"],
                "pi_hat": [0.0, 0.0],
                "en_frontera": [True, True],
                "ic_superior": [7.7e-5, 4.4e-5],
            }
        ),
    )
    _write(
        local / "robustness.csv",
        pd.DataFrame({"check": list("abcd"), "robusta": [True] * 4}),
    )
    printed = {"dynamic": load_table4(), "static": load_table5()}
    for name, (tag, group) in FIGURES.items():
        _write(figures / f"{name}_data.csv", figure_data(printed[tag], group))
    _write(figures / "fig7_emissions_seg_data.csv", load_fig7_bars())
    _write(
        tables / "fig1_scales.csv",
        pd.DataFrame(
            {
                "group": ["AB", "C1b"],
                "ours_max": [1511.29, 7073.24],
                "paper_max": [1600.0, 7000.0],
                "ratio": [0.9446, 1.0105],
            }
        ),
    )
    return Context(tables, figures, local, authors_reference=lambda tag: STAR_TABLES[tag]())


def _status(report: Report) -> dict[str, Status]:
    return {item.id: item.status for item in report.items}


# ------------------------------------------------------------------ el caso perfecto
def test_perfect_outputs_give_a_report_without_failures(ctx):
    report = build_report(ctx)
    assert report.ok and report.counts[Status.FAILED] == 0 and report.counts[Status.SKIPPED] == 0
    status = _status(report)
    assert status["median_counts"] is Status.EXACT and status["median_distance"] is Status.EXACT
    assert status["stars_dynamic"] is Status.EXACT and status["stars_static"] is Status.EXACT
    assert status["table4"] is Status.WITHIN and status["fig7"] is Status.WITHIN
    assert status["moran"] is Status.DOCUMENTED and status["wasserstein"] is Status.DOCUMENTED
    assert status["fig1_scales"] is Status.DOCUMENTED
    assert status["pi"] is Status.INFO and status["local_time"] is Status.INFO
    assert status["stars_printed"] is Status.INFO


def test_status_symbols_and_labels():
    assert [s.symbol for s in Status] == ["✅", "✅", "🟡", "ℹ️", "❌", "⏭️"]
    assert Status.DOCUMENTED.label == "desviación documentada"


# ------------------------------------------------------------------ cosas que deben fallar
def test_a_table_cell_outside_tolerance_fails(ctx):
    path = ctx.tables_dir / "comparison_table4.csv"
    frame = pd.read_csv(path)
    frame.loc[frame["column"] == "zinb", "ok_cells"] = 12
    frame.to_csv(path, index=False)
    assert _status(build_report(ctx))["table4"] is Status.FAILED


@pytest.mark.parametrize("name", ["median_counts_check", "median_distance_check"])
def test_medians_that_are_not_identical_or_incomplete_fail(ctx, name):
    path = ctx.tables_dir / f"{name}.csv"
    frame = pd.read_csv(path)
    frame.loc[0, "identical"] = False
    frame.to_csv(path, index=False)
    item_id = "median_counts" if "counts" in name else "median_distance"
    assert _status(build_report(ctx))[item_id] is Status.FAILED
    frame["identical"], frame["n_rows"] = True, 178303  # una fila de menos
    frame.to_csv(path, index=False)
    assert _status(build_report(ctx))[item_id] is Status.FAILED


def test_one_wrong_star_fails_the_comparison_with_the_authors_tables(ctx):
    path = ctx.tables_dir / "inference_dynamic_paper_text.csv"
    frame = pd.read_csv(path, keep_default_na=False)
    row = frame["variable"] == "genero_masc"
    frame.loc[row, "zinb_sig"] = ""  # el paper tiene `***`
    frame.to_csv(path, index=False)
    report = build_report(ctx)
    item = next(i for i in report.items if i.id == "stars_dynamic")
    assert item.status is Status.FAILED and item.result.startswith("43/44")


def test_documented_values_that_change_turn_into_failures(ctx):
    def change(path, column, value, row=0):
        frame = pd.read_csv(path)
        frame.loc[row, column] = value
        frame.to_csv(path, index=False)

    change(ctx.tables_dir / "moran.csv", "moran_i", 0.4690)  # ahora "se parece" al paper
    change(ctx.tables_dir / "fig1_scales.csv", "ratio", 1.0)
    frame = pd.read_csv(ctx.tables_dir / "table2_mobility_seeds.csv")
    frame["inside_band"] = True  # 15/15 en la banda: cambió
    frame.to_csv(ctx.tables_dir / "table2_mobility_seeds.csv", index=False)
    change(ctx.tables_dir / "zero_inflation.csv", "en_frontera", False)
    change(ctx.local_dir / "robustness.csv", "robusta", False)
    status = _status(build_report(ctx))
    assert [status[k] for k in ("moran", "fig1_scales", "wasserstein", "pi", "local_time")] == [
        Status.FAILED
    ] * 5


def test_cameron_trivedi_outside_its_limit_fails(ctx):
    path = ctx.tables_dir / "cameron_trivedi.csv"
    frame = pd.read_csv(path)
    frame.loc[0, ["dispersion", "abs_diff"]] = [8.3, 0.57]
    frame.to_csv(path, index=False)
    assert _status(build_report(ctx))["dispersion"] is Status.FAILED


def test_figure_points_that_differ_from_the_printed_tables_fail(ctx):
    path = ctx.figures_dir / "fig6_seg_dynamic_data.csv"
    frame = pd.read_csv(path)
    frame.loc[0, "zinb"] += 0.001
    frame.to_csv(path, index=False)
    assert _status(build_report(ctx))["figures_effects"] is Status.FAILED


def test_fig7_with_a_wrong_label_fails(ctx):
    path = ctx.figures_dir / "fig7_emissions_seg_data.csv"
    frame = pd.read_csv(path)
    frame.loc[3, "nox_g"] = 71.4
    frame.to_csv(path, index=False)
    item = next(i for i in build_report(ctx).items if i.id == "fig7")
    assert item.status is Status.FAILED and item.result.startswith("11/12")


# ------------------------------------------------------------------ omitidos y estados de ejecución
def test_missing_outputs_are_skipped_not_failed(ctx):
    (ctx.tables_dir / "moran.csv").unlink()
    (ctx.figures_dir / "fig8_age_dynamic_data.csv").unlink()
    report = build_report(ctx)
    status = _status(report)
    assert status["moran"] is Status.SKIPPED and status["figures_effects"] is Status.SKIPPED
    assert report.ok and report.counts[Status.SKIPPED] == 2


def test_stars_are_skipped_without_the_authors_package(ctx):
    ctx.authors_reference = None
    status = _status(build_report(ctx))
    assert status["stars_dynamic"] is Status.SKIPPED and status["stars_static"] is Status.SKIPPED


def test_a_failed_step_is_reported_as_a_failure(ctx):
    ctx.run_log = {
        "started": "2026-10-11T10:00:00",
        "mode": "quick",
        "steps": [
            {
                "id": "03",
                "script": "scripts/03_zinb_tables.py",
                "args": [],
                "status": "failed",
                "returncode": 1,
                "seconds": 5.0,
            },
            {
                "id": "01",
                "script": "scripts/01_table2.py",
                "args": [],
                "status": "ok",
                "returncode": 0,
                "seconds": 2.0,
            },
        ],
    }
    report = build_report(ctx)
    assert not report.ok and _status(report)["step_03"] is Status.FAILED
    assert "step_01" not in _status(report)
    assert report.meta["mode"] == "quick" and report.steps[0]["id"] == "03"


def test_items_older_than_the_run_are_marked_as_from_a_previous_run(ctx):
    report = build_report(ctx)
    item = next(i for i in report.items if i.id == "moran")
    assert item.source_date is not None
    before = item.source_date - timedelta(hours=1)
    after = item.source_date + timedelta(hours=1)
    assert not is_stale(item, before) and is_stale(item, after)
    assert not is_stale(Item("x", "a", "n", "t", "r", Status.INFO), after)  # sin fecha: no se marca
    report.meta["run_started"] = after
    assert "de una corrida anterior" in report.to_markdown()


# ------------------------------------------------------------------ salida
def test_markdown_and_frame_have_the_expected_shape(ctx):
    ctx.run_log = {
        "started": datetime(2000, 1, 1).isoformat(),
        "mode": "standard",
        "steps": [
            {
                "id": "01",
                "script": "scripts/01_table2.py",
                "args": [],
                "status": "ok",
                "returncode": 0,
                "seconds": 3.2,
            }
        ],
    }
    report = build_report(ctx, meta={"generated_at": "2026-10-11 10:00", "commit": "abc1234"})
    text = report.to_markdown()
    assert text.startswith("# Informe de reproducción")
    assert "**Resultado:** sin fallas" in text and "abc1234" in text and "standard" in text
    assert "## Pasos de la ejecución" in text and "scripts/01_table2.py" in text
    # cada fila de cada tabla tiene el mismo número de barras que su encabezado
    for block in text.split("\n\n"):
        rows = [line for line in block.splitlines() if line.startswith("|")]
        if rows:
            assert len({line.count("|") for line in rows}) == 1, block[:80]
    frame = report.to_frame()
    assert list(frame.columns) == [
        "id",
        "area",
        "name",
        "target",
        "result",
        "status",
        "ref",
        "source",
        "source_date",
        "note",
    ]
    assert len(frame) == len(report.items) and set(frame["status"]) <= {s.value for s in Status}
    json.dumps(frame.to_dict(orient="records"))  # serializable


def test_summary_line_counts_each_status(ctx):
    line = build_report(ctx).summary_line()
    assert all(symbol in line for symbol in ("✅", "🟡", "ℹ️", "❌", "⏭️"))


# ------------------------------------------------------------------ archivos del informe
def test_write_report_writes_markdown_csv_and_an_optional_published_copy(ctx, tmp_path):
    from lastmile_exposure.validation.reproduction import write_report

    report = build_report(ctx)
    paths = write_report(report, tmp_path / "out")
    assert [p.name for p in paths] == ["report.md", "report.csv"]
    assert paths[0].read_text(encoding="utf-8") == report.to_markdown()
    assert len(pd.read_csv(paths[1])) == len(report.items)
    published = tmp_path / "docs" / "reproduction_report.md"
    paths = write_report(report, tmp_path / "out", publish_to=published)
    assert paths[-1] == published and published.read_text(encoding="utf-8") == report.to_markdown()


def test_the_steps_table_shows_the_reason_and_marks_the_diagnostic(ctx):
    ctx.run_log = {
        "started": "2026-10-11T10:00:00",
        "mode": "quick",
        "steps": [
            {
                "id": "14",
                "script": "scripts/14_figures.py",
                "args": [],
                "status": "skipped",
                "returncode": None,
                "seconds": None,
                "reason": "falta la tabla | del 03",
            },
            {
                "id": "07",
                "script": "scripts/07_stars_diagnosis.py",
                "args": [],
                "status": "ok",
                "returncode": 0,
                "seconds": 9.0,
                "reason": "",
                "diagnostic": True,
            },
        ],
    }
    text = build_report(ctx).to_markdown()
    assert "| Paso | Script | Estado | Duración | Salida | Motivo |" in text
    assert "falta la tabla / del 03" in text  # las barras del motivo no rompen la tabla
    assert "DIAGNÓSTICO, no es una réplica" in text


def test_plain_summary_is_ascii_safe_for_the_windows_console(ctx):
    line = build_report(ctx).summary_plain()
    assert line.isascii() and "0 fallas" in line and "ok" in line
