"""Ejecutor de la réplica: corre los scripts en orden y registra cada paso.

Paper: —
Código de los autores: (no aplica)
Hallazgos (AGENTS.md §7): H26 (el diagnóstico con `data_base` queda aislado), §12 (memoria)
Estado: implementado (ejecutor final). Orquesta los scripts de `scripts/`, que siguen siendo la
    fuente de verdad, como subprocesos y de a uno (sin paralelismo: la memoria alcanza justo,
    AGENTS.md §12). Anota duración y código de salida de cada paso en `run_log.json`; el informe lo
    arma `validation/reproduction.py` con lo que dejaron los scripts.

Modos (qué pasos corren, en este orden de dependencia):
- `quick` (~4 min medidos): tablas, medianas, Cameron–Trivedi, Moran, sensibilidad en hora local y
  figuras.
- `standard` (~9 min medidos, por defecto): `quick` más errores por comuna y estrellas (06), π (10)
  y el Wasserstein con las semillas guardadas (05 y 12 con `--use-reference`).
- `full` (~1 h; no se midió de punta a punta): como `standard`, pero recalculando el Wasserstein
  (05, y 12 con 200 semillas y 8 procesos).
El diagnóstico con `data_base` (07) NO es una réplica y solo corre con `with_diagnostics=True`
(regla 8 de AGENTS.md §2.1): este módulo lo nombra solo como una ruta, nunca lo importa.

Un paso que falla no detiene a los demás; solo se omite un paso si le falta la salida de otro que
necesita (p. ej. las figuras necesitan las tablas del paso 03) o si faltan los datos.
"""

import json
import os
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from importlib import metadata
from pathlib import Path

from lastmile_exposure import config

MODES = ("quick", "standard", "full")
REPRODUCTION_DIRNAME = "reproduction"
RUN_LOG_NAME = "run_log.json"
DEFAULT_TIMEOUT_MINUTES = 180
TABLES = "as_published/tables"


@dataclass(frozen=True)
class Step:
    """Un paso de la ejecución: un script con sus argumentos según el modo."""

    id: str
    script: str
    description: str
    seconds: int  # duración orientativa en los modos quick y standard
    seconds_full: int | None = None  # si es distinta en el modo full
    modes: tuple[str, ...] = MODES
    args: dict = field(default_factory=dict)  # modo -> argumentos extra
    requires: tuple[str, ...] = ()  # salidas (relativas a outputs/) que deben existir antes
    publishes: bool = False  # el script acepta `--publish`
    needs_data: bool = True
    diagnostic: bool = False

    def args_for(self, mode: str) -> tuple[str, ...]:
        return tuple(self.args.get(mode, ()))

    def estimate(self, mode: str) -> int:
        return self.seconds_full if mode == "full" and self.seconds_full else self.seconds


# El orden es el de dependencia: las figuras (14) van después de las tablas (03).
STEPS: tuple[Step, ...] = (
    Step("01", "scripts/01_table2.py", "Tabla 2", 20),
    Step("02", "scripts/02_distance_tables.py", "Columnas OLS de distancia (Tablas 4 y 5)", 15),
    Step("03", "scripts/03_zinb_tables.py", "Columna ZINB y tablas 4 y 5 completas", 60),
    Step("04", "scripts/04_median_counts.py", "Mediana de conteos (42 miércoles)", 40),
    Step("11", "scripts/11_median_distance.py", "Mediana de distancia y tiempo (41 miércoles)", 35),
    Step(
        "05",
        "scripts/05_mobility.py",
        "Wasserstein según el texto del paper",
        10,
        600,
        modes=("standard", "full"),
        args={"standard": ("--use-reference",)},
    ),
    Step(
        "06",
        "scripts/06_inference.py",
        "Errores por comuna y estrellas",
        90,
        modes=("standard", "full"),
    ),
    Step("08", "scripts/08_dispersion_test.py", "Test de Cameron–Trivedi", 15),
    Step("09", "scripts/09_moran.py", "I de Moran", 10),
    Step(
        "10",
        "scripts/10_zero_inflation.py",
        "π del ZINB (diagnóstico)",
        240,
        modes=("standard", "full"),
    ),
    Step(
        "12",
        "scripts/12_mobility_seeds.py",
        "Wasserstein con el método de los autores y 200 semillas",
        10,
        2400,
        modes=("standard", "full"),
        args={"standard": ("--use-reference",), "full": ("--workers", "8")},
    ),
    Step("13", "scripts/13_local_time_sensitivity.py", "Sensibilidad en hora local", 120),
    Step(
        "14",
        "scripts/14_figures.py",
        "Figs. 6 a 10",
        10,
        requires=(
            f"{TABLES}/table4_complete_no_stars.csv",
            f"{TABLES}/table5_complete_no_stars.csv",
        ),
        publishes=True,
        needs_data=False,
    ),
    Step("15", "scripts/15_maps.py", "Fig. 1 y sustituto de la Fig. 2", 30, publishes=True),
    Step(
        "07",
        "scripts/07_stars_diagnosis.py",
        "DIAGNÓSTICO con data_base (no es una réplica)",
        300,
        diagnostic=True,
    ),
)


# ------------------------------------------------------------------ selección de pasos
def steps_for(
    mode: str = "standard",
    *,
    only: Iterable[str] | None = None,
    skip: Iterable[str] | None = None,
    with_diagnostics: bool = False,
) -> list[Step]:
    """Pasos a ejecutar, en orden de dependencia.

    `only` elige pasos por id sin mirar el modo; `skip` los descarta. El diagnóstico (07) solo
    entra con `with_diagnostics=True`, también si se pide en `only`.
    """
    if mode not in MODES:
        raise ValueError(f"`mode` debe ser uno de {MODES}, no {mode!r}")
    only_ids, skip_ids = set(only or ()), set(skip or ())
    known = {step.id for step in STEPS}
    unknown = (only_ids | skip_ids) - known
    if unknown:
        raise ValueError(f"Pasos desconocidos: {sorted(unknown)}; los válidos son {sorted(known)}")
    diagnostic_ids = {step.id for step in STEPS if step.diagnostic}
    if only_ids & diagnostic_ids and not with_diagnostics:
        raise ValueError("El paso 07 es un diagnóstico (no es una réplica): usa with_diagnostics")

    def wanted(step: Step) -> bool:
        if step.id in skip_ids:
            return False
        if only_ids:
            return step.id in only_ids
        if step.diagnostic:
            return with_diagnostics
        return mode in step.modes

    return [step for step in STEPS if wanted(step)]


def build_command(
    step: Step, mode: str, *, python: str = sys.executable, publish: bool = False
) -> list[str]:
    """Comando de un paso: intérprete, script, argumentos del modo y, si se pide, `--publish`."""
    command = [python, step.script, *step.args_for(mode)]
    if publish and step.publishes:
        command.append("--publish")
    return command


def estimate_seconds(steps: Iterable[Step], mode: str) -> int:
    return sum(step.estimate(mode) for step in steps)


def data_available() -> bool:
    """True si el paquete de los autores (datos confidenciales) está en `data/`."""
    return (config.PACKAGE_DIR / "00_data" / "miercoles_rm.csv").exists()


# ------------------------------------------------------------------ ejecución
def _last_line(path: Path) -> str:
    if not path.exists():
        return ""
    lines = [
        line.strip() for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
    ]
    lines = [line for line in lines if line]
    return lines[-1][:160] if lines else ""


def run_step(
    step: Step,
    mode: str,
    *,
    root: Path,
    outputs_dir: Path,
    python: str = sys.executable,
    publish: bool = False,
    timeout_minutes: float | None = DEFAULT_TIMEOUT_MINUTES,
    run: Callable = subprocess.run,
    data_ok: bool = True,
) -> dict:
    """Ejecuta un paso y devuelve su registro (`status`: ok, failed, error o skipped)."""
    log_dir = outputs_dir / REPRODUCTION_DIRNAME / "logs"
    log_path = log_dir / f"{Path(step.script).stem}.log"
    record = {
        "id": step.id,
        "script": step.script,
        "args": list(step.args_for(mode)) + (["--publish"] if publish and step.publishes else []),
        "description": step.description,
        "status": "skipped",
        "returncode": None,
        "seconds": None,
        "started": datetime.now().isoformat(timespec="seconds"),
        "reason": "",
        "diagnostic": step.diagnostic,
    }
    missing = [name for name in step.requires if not (outputs_dir / name).exists()]
    if missing:
        record["reason"] = f"falta {missing[0]} (ejecuta antes el paso que la genera)"
        return record
    if step.needs_data and not data_ok:
        record["reason"] = "faltan los datos confidenciales en data/"
        return record
    log_dir.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    command = build_command(step, mode, python=python, publish=publish)
    started = datetime.now()
    try:
        with log_path.open("w", encoding="utf-8") as handle:
            completed = run(
                command,
                cwd=root,
                env=env,
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=None if timeout_minutes is None else timeout_minutes * 60,
            )
        code = completed.returncode
    except subprocess.TimeoutExpired:
        record.update(status="error", reason=f"superó el tiempo máximo ({timeout_minutes:g} min)")
    except OSError as error:
        record.update(status="error", reason=f"no se pudo ejecutar: {error}")
    else:
        record["returncode"] = code
        record["status"] = "ok" if code == 0 else "failed" if code == 1 else "error"
        if code != 0:
            record["reason"] = _last_line(log_path)
    record["seconds"] = round((datetime.now() - started).total_seconds(), 1)
    return record


def write_run_log(path: Path, log: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


def read_run_log(path: Path) -> dict | None:
    """El registro de la última ejecución, o `None` si no hay."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def run_all(
    steps: list[Step],
    mode: str = "standard",
    *,
    root: Path | None = None,
    outputs_dir: Path | None = None,
    python: str = sys.executable,
    publish: bool = False,
    timeout_minutes: float | None = DEFAULT_TIMEOUT_MINUTES,
    run: Callable = subprocess.run,
    data_ok: bool | None = None,
    progress: Callable[[dict], None] | None = None,
) -> dict:
    """Ejecuta los pasos en orden, sin detenerse ante un fallo, y escribe `run_log.json`.

    El registro se reescribe después de cada paso, de modo que una interrupción no pierde lo
    avanzado. Devuelve el registro: `started`, `finished`, `mode`, `publish` y `steps`.
    """
    root = root or Path(config.ROOT)
    outputs_dir = outputs_dir or config.OUTPUTS_DIR
    data_ok = data_available() if data_ok is None else data_ok
    log = {
        "started": datetime.now().isoformat(timespec="seconds"),
        "mode": mode,
        "publish": publish,
        "steps": [],
    }
    path = outputs_dir / REPRODUCTION_DIRNAME / RUN_LOG_NAME
    for step in steps:
        record = run_step(
            step,
            mode,
            root=root,
            outputs_dir=outputs_dir,
            python=python,
            publish=publish,
            timeout_minutes=timeout_minutes,
            run=run,
            data_ok=data_ok,
        )
        log["steps"].append(record)
        write_run_log(path, log)
        if progress is not None:
            progress(record)
    log["finished"] = datetime.now().isoformat(timespec="seconds")
    write_run_log(path, log)
    return log


# ------------------------------------------------------------------ metadatos del informe
LIBRARIES = ("numpy", "pandas", "scipy", "statsmodels", "h3", "matplotlib")


def package_versions() -> str:
    """`Python 3.12.x · numpy 2.5.3 · …` para el encabezado del informe."""
    parts = [f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"]
    for name in LIBRARIES:
        try:
            parts.append(f"{name} {metadata.version(name)}")
        except metadata.PackageNotFoundError:
            continue
    return " · ".join(parts)


def git_commit(root: Path | None = None) -> str | None:
    """Versión corta del código (`abc1234`, con aviso si hay cambios sin subir); `None` sin git."""
    root = root or Path(config.ROOT)
    try:
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    return f"{head} (con cambios sin subir)" if dirty else head
