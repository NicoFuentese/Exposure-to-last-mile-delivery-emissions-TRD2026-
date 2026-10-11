"""Ejecutor de la réplica (`runner.py`): selección de pasos, comandos y manejo de fallos.

No ejecuta ningún script real: el "ejecutor" se reemplaza por una función falsa que simula el
código de salida de cada script y escribe una línea en el log.
"""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from lastmile_exposure import config, runner
from lastmile_exposure.runner import (
    STEPS,
    Step,
    build_command,
    estimate_seconds,
    git_commit,
    package_versions,
    read_run_log,
    run_all,
    run_step,
    steps_for,
)

QUICK = ["01", "02", "03", "04", "11", "08", "09", "13", "14", "15"]
STANDARD = ["01", "02", "03", "04", "11", "05", "06", "08", "09", "10", "12", "13", "14", "15"]


def _ids(steps):
    return [step.id for step in steps]


# ------------------------------------------------------------------ selección
def test_modes_select_the_agreed_steps_in_dependency_order():
    assert _ids(steps_for("quick")) == QUICK
    assert _ids(steps_for("standard")) == STANDARD
    assert _ids(steps_for("full")) == STANDARD  # mismos pasos; cambia cómo se corren 05 y 12
    assert _ids(steps_for()) == STANDARD  # el modo por defecto es `standard`


def test_figures_run_after_the_tables_they_read():
    order = _ids(steps_for("quick"))
    assert order.index("03") < order.index("14")
    figures = next(step for step in STEPS if step.id == "14")
    assert set(figures.requires) == {
        "as_published/tables/table4_complete_no_stars.csv",
        "as_published/tables/table5_complete_no_stars.csv",
    }


def test_every_step_points_to_an_existing_script_and_ids_are_unique():
    ids = [step.id for step in STEPS]
    assert len(ids) == len(set(ids))
    for step in STEPS:
        assert (Path(config.ROOT) / step.script).exists(), step.script
        assert step.script.startswith(f"scripts/{step.id}_")


def test_the_diagnostic_only_runs_when_asked_explicitly():
    assert "07" not in _ids(steps_for("full"))
    assert _ids(steps_for("quick", with_diagnostics=True))[-1] == "07"  # al final
    with pytest.raises(ValueError, match="diagnóstico"):
        steps_for("quick", only=["07"])
    assert _ids(steps_for("quick", only=["07"], with_diagnostics=True)) == ["07"]
    assert _ids(steps_for("quick", only=["03", "14"], with_diagnostics=True)) == ["03", "14"]


def test_only_and_skip_and_unknown_ids():
    assert _ids(steps_for("quick", only=["14", "03"])) == ["03", "14"]  # respeta el orden
    assert _ids(steps_for("standard", only=["06"])) == ["06"]  # `only` ignora el modo
    assert "06" not in _ids(steps_for("standard", skip=["06", "10"]))
    with pytest.raises(ValueError, match="desconocidos"):
        steps_for("quick", only=["99"])
    with pytest.raises(ValueError, match="`mode`"):
        steps_for("rapido")


# ------------------------------------------------------------------ comandos
def _command(step_id, mode="standard", publish=False):
    step = next(s for s in STEPS if s.id == step_id)
    return build_command(step, mode, python="py", publish=publish)


def test_commands_depend_on_the_mode():
    assert _command("05", "standard") == ["py", "scripts/05_mobility.py", "--use-reference"]
    assert _command("05", "full") == ["py", "scripts/05_mobility.py"]
    assert _command("12", "standard") == ["py", "scripts/12_mobility_seeds.py", "--use-reference"]
    assert _command("12", "full") == ["py", "scripts/12_mobility_seeds.py", "--workers", "8"]
    assert _command("03", "quick") == ["py", "scripts/03_zinb_tables.py"]


def test_the_runner_never_overwrites_the_versioned_seed_reference():
    """`--write-reference` reescribiría `reference/mobility/`: solo una persona debe decidirlo."""
    for step in STEPS:
        for mode in runner.MODES:
            assert "--write-reference" not in build_command(step, mode)


def test_publish_is_passed_only_to_the_scripts_that_accept_it():
    published = [s.id for s in STEPS if "--publish" in build_command(s, "quick", publish=True)]
    assert published == ["14", "15"]
    assert all("--publish" not in build_command(s, "quick", publish=False) for s in STEPS)


def test_estimated_durations_match_the_measured_runs():
    minutes = {m: estimate_seconds(steps_for(m), m) / 60 for m in runner.MODES}
    assert 4 <= minutes["quick"] <= 8
    assert 9 <= minutes["standard"] <= 15
    assert 55 <= minutes["full"] <= 70


# ------------------------------------------------------------------ ejecución de un paso
def _fake_run(codes=None, raises=None, writes=True):
    """Ejecutor falso: devuelve el código de salida pedido para cada script."""
    codes = codes or {}
    calls = []

    def fake(command, cwd, env, stdout, stderr, timeout):
        calls.append({"command": command, "cwd": cwd, "env": env, "timeout": timeout})
        script = command[1]
        if raises and script in raises:
            raise raises[script]
        if writes:
            stdout.write(f"salida de {script}\nultima linea de {script}\n")
        return SimpleNamespace(returncode=codes.get(script, 0))

    fake.calls = calls
    return fake


def _step(step_id):
    return next(step for step in STEPS if step.id == step_id)


def test_a_successful_step_is_recorded_with_its_log(tmp_path):
    fake = _fake_run()
    record = run_step(_step("01"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake)
    assert (record["status"], record["returncode"], record["reason"]) == ("ok", 0, "")
    assert record["seconds"] is not None and record["args"] == []
    log = tmp_path / "reproduction" / "logs" / "01_table2.log"
    assert "ultima linea" in log.read_text(encoding="utf-8")
    call = fake.calls[0]
    assert call["cwd"] == tmp_path and call["env"]["PYTHONUTF8"] == "1"
    assert call["env"]["PYTHONIOENCODING"] == "utf-8" and call["timeout"] == 180 * 60


@pytest.mark.parametrize(("code", "status"), [(1, "failed"), (2, "error"), (3, "error")])
def test_a_failing_step_keeps_the_last_log_line_as_the_reason(tmp_path, code, status):
    fake = _fake_run({"scripts/03_zinb_tables.py": code})
    record = run_step(_step("03"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake)
    assert record["status"] == status and record["returncode"] == code
    assert record["reason"] == "ultima linea de scripts/03_zinb_tables.py"


def test_timeouts_and_missing_interpreters_are_errors_not_crashes(tmp_path):
    timeout = _fake_run(raises={"scripts/03_zinb_tables.py": subprocess.TimeoutExpired("x", 1)})
    record = run_step(
        _step("03"), "quick", root=tmp_path, outputs_dir=tmp_path, run=timeout, timeout_minutes=2
    )
    assert record["status"] == "error" and "2 min" in record["reason"]
    broken = _fake_run(raises={"scripts/01_table2.py": FileNotFoundError("no hay python")})
    record = run_step(_step("01"), "quick", root=tmp_path, outputs_dir=tmp_path, run=broken)
    assert record["status"] == "error" and "no hay python" in record["reason"]


def test_a_step_is_skipped_when_an_input_from_another_step_is_missing(tmp_path):
    fake = _fake_run()
    record = run_step(_step("14"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake)
    assert record["status"] == "skipped" and "table4_complete_no_stars.csv" in record["reason"]
    assert not fake.calls
    tables = tmp_path / "as_published" / "tables"
    tables.mkdir(parents=True)
    for name in ("table4_complete_no_stars.csv", "table5_complete_no_stars.csv"):
        (tables / name).write_text("x", encoding="utf-8")
    record = run_step(_step("14"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake)
    assert record["status"] == "ok"


def test_steps_that_need_the_confidential_data_are_skipped_without_it(tmp_path):
    fake = _fake_run()
    record = run_step(
        _step("01"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake, data_ok=False
    )
    assert record["status"] == "skipped" and "datos" in record["reason"] and not fake.calls


def test_publish_is_recorded_and_passed_to_the_figure_scripts(tmp_path):
    fake = _fake_run()
    tables = tmp_path / "as_published" / "tables"
    tables.mkdir(parents=True)
    for name in ("table4_complete_no_stars.csv", "table5_complete_no_stars.csv"):
        (tables / name).write_text("x", encoding="utf-8")
    record = run_step(
        _step("14"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake, publish=True
    )
    assert record["args"] == ["--publish"] and fake.calls[0]["command"][-1] == "--publish"


# ------------------------------------------------------------------ ejecución completa
def test_run_all_continues_after_a_failure_and_writes_the_log_after_each_step(tmp_path):
    steps = [_step(i) for i in ("01", "03", "14", "08")]
    fake = _fake_run({"scripts/03_zinb_tables.py": 1})  # el 03 falla y no deja sus tablas
    seen = []

    def progress(record):
        seen.append(record["id"])
        saved = read_run_log(tmp_path / "reproduction" / "run_log.json")
        assert [s["id"] for s in saved["steps"]] == seen  # el registro ya incluye este paso
        assert "finished" not in saved  # y todavía no terminó

    log = run_all(
        steps,
        "quick",
        root=tmp_path,
        outputs_dir=tmp_path,
        run=fake,
        data_ok=True,
        progress=progress,
    )
    status = {s["id"]: s["status"] for s in log["steps"]}
    assert status == {"01": "ok", "03": "failed", "14": "skipped", "08": "ok"}
    assert log["mode"] == "quick" and log["publish"] is False and "finished" in log
    assert read_run_log(tmp_path / "reproduction" / "run_log.json") == log
    assert [call["command"][1] for call in fake.calls] == [
        "scripts/01_table2.py",
        "scripts/03_zinb_tables.py",
        "scripts/08_dispersion_test.py",
    ]  # el 14 no se ejecutó


def test_run_all_without_data_skips_everything_that_needs_it(tmp_path):
    fake = _fake_run()
    log = run_all(
        steps_for("quick"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake, data_ok=False
    )
    assert not fake.calls
    assert {s["status"] for s in log["steps"]} == {"skipped"}


def test_read_run_log_returns_none_when_there_is_no_log(tmp_path):
    assert read_run_log(tmp_path / "nada.json") is None


def test_the_step_record_marks_the_diagnostic(tmp_path):
    fake = _fake_run()
    record = run_step(_step("07"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake)
    assert record["diagnostic"] is True
    assert (
        run_step(_step("01"), "quick", root=tmp_path, outputs_dir=tmp_path, run=fake)["diagnostic"]
        is False
    )


# ------------------------------------------------------------------ metadatos
def test_metadata_for_the_report_header():
    versions = package_versions()
    assert versions.startswith("Python 3.12") and "numpy" in versions and "statsmodels" in versions
    commit = git_commit()
    assert commit is None or len(commit.split()[0]) >= 7


def test_step_dataclass_defaults():
    step = Step("99", "scripts/99_x.py", "prueba", 10)
    assert step.args_for("quick") == () and step.estimate("full") == 10
    assert Step("98", "s", "d", 10, 99).estimate("full") == 99
