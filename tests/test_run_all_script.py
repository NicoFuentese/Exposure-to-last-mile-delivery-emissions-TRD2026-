"""`scripts/16_run_all.py`: pruebas de humo que no ejecutan ningún paso de la réplica."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from lastmile_exposure import config

SCRIPT = Path(config.ROOT) / "scripts" / "16_run_all.py"


def _run(*args, env=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=600,
        env={**os.environ, **(env or {}), "PYTHONUTF8": "1"},
    )


def test_dry_run_prints_the_plan_without_running_anything():
    result = _run("--mode", "quick", "--dry-run")
    assert result.returncode == 0
    assert "Modo quick: 10 pasos" in result.stdout
    assert (
        "scripts/03_zinb_tables.py" in result.stdout
        and "scripts/06_inference.py" not in result.stdout
    )


def test_dry_run_standard_mode_uses_the_saved_seeds_and_never_writes_the_reference():
    result = _run("--dry-run")
    assert result.returncode == 0 and "Modo standard: 14 pasos" in result.stdout
    assert "scripts/12_mobility_seeds.py --use-reference" in result.stdout
    assert "--write-reference" not in result.stdout


def test_the_diagnostic_needs_an_explicit_flag():
    refused = _run("--only", "07", "--dry-run")
    assert refused.returncode == 2 and "diagnostico" in refused.stdout
    allowed = _run("--only", "07", "--with-diagnostics", "--dry-run")
    assert allowed.returncode == 0 and "07_stars_diagnosis.py" in allowed.stdout


def test_unknown_steps_are_rejected_with_exit_code_2():
    result = _run("--only", "99", "--dry-run")
    assert result.returncode == 2 and "desconocidos" in result.stdout


@pytest.mark.slow
def test_a_real_run_of_two_fast_steps_writes_the_log_and_the_report(panel, tmp_path):
    """Con datos reales: ejecuta los pasos 01 y 02 (~15 s) en una carpeta de salidas temporal.

    `LASTMILE_OUTPUTS_DIR` redirige `outputs/`, así la prueba no pisa el informe ni los resultados
    reales de la última ejecución.
    """
    result = _run("--only", "01,02", env={"LASTMILE_OUTPUTS_DIR": str(tmp_path)})
    assert result.returncode == 0, result.stdout[-600:]
    out = tmp_path / "reproduction"
    assert (out / "report.md").exists() and (out / "report.csv").exists()
    log = json.loads((out / "run_log.json").read_text(encoding="utf-8"))
    assert [s["id"] for s in log["steps"]] == ["01", "02"]
    assert all(s["status"] == "ok" for s in log["steps"])
    assert (out / "logs" / "01_table2.log").exists()
    assert (
        tmp_path / "as_published" / "tables" / "table2.csv"
    ).exists()  # los scripts escribieron ahí
    assert "Tabla 2" in (out / "report.md").read_text(encoding="utf-8")
