"""Ejecutor final: regenera las tablas y figuras de la réplica y deja un informe de reproducción.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/16_run_all.py                     # modo estándar (~9 min)
    python scripts/16_run_all.py --mode quick        # ~4 min: sin 05, 06, 10 y 12
    python scripts/16_run_all.py --mode full         # ~1 h: recalcula el Wasserstein
    python scripts/16_run_all.py --dry-run           # muestra el plan y la duración, sin ejecutar
    python scripts/16_run_all.py --report-only       # solo el informe, con lo que haya en outputs/
    python scripts/16_run_all.py --only 03,14        # solo esos pasos
    python scripts/16_run_all.py --skip 06           # todo salvo esos pasos
    python scripts/16_run_all.py --with-diagnostics  # agrega el diagnóstico 07 (NO es una réplica)
    python scripts/16_run_all.py --publish           # además publica las figuras y el informe

Salida (outputs/reproduction/, ignorado por git): report.md y report.csv (el informe), run_log.json
(duración y código de salida de cada paso) y un log por script en logs/. Con --publish, el informe
también va a docs/reproduction_report.md y los scripts 14 y 15 reciben --publish (copian a
docs/figures/ solo lo autorizado: AGENTS.md, regla 3). El informe solo contiene agregados.
Código:  src/lastmile_exposure/runner.py (ejecución) y validation/reproduction.py (informe)

Los pasos corren de a uno (no hay paralelismo: la memoria alcanza justo) y un paso que falla no
detiene a los demás. No ejecutes `pytest` al mismo tiempo (AGENTS.md §12). El diagnóstico con
`data_base` (07) no es una réplica: solo corre con --with-diagnostics y queda rotulado.

La consola recibe solo ASCII (convención de los scripts, por la consola cp1252 de Windows); el
informe en archivo es UTF-8 con tildes y emojis.

Código de salida: 0 si el informe no tiene fallas (❌); 1 si alguna falla; 2 si faltan los datos
confidenciales o los argumentos no son válidos.
"""

import argparse
import sys
import unicodedata
from datetime import datetime

from lastmile_exposure import config
from lastmile_exposure.runner import (
    DEFAULT_TIMEOUT_MINUTES,
    MODES,
    REPRODUCTION_DIRNAME,
    RUN_LOG_NAME,
    data_available,
    estimate_seconds,
    git_commit,
    package_versions,
    read_run_log,
    run_all,
    steps_for,
)
from lastmile_exposure.validation.reproduction import Context, Status, build_report, write_report

PUBLISHED_REPORT = config.ROOT / "docs" / "reproduction_report.md"


def _ascii(text: str) -> str:
    """Texto apto para la consola de Windows (cp1252): sin tildes, letras griegas ni emojis."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()


def _ids(text: str | None) -> list[str] | None:
    return [part.strip() for part in text.split(",") if part.strip()] if text else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--mode", choices=MODES, default="standard", help="que pasos corren")
    parser.add_argument("--only", help="ids de los pasos a ejecutar, separados por comas")
    parser.add_argument("--skip", help="ids de los pasos a omitir, separados por comas")
    parser.add_argument("--with-diagnostics", action="store_true", help="agrega el diagnostico 07")
    parser.add_argument("--dry-run", action="store_true", help="muestra el plan y no ejecuta")
    parser.add_argument("--report-only", action="store_true", help="solo arma el informe")
    parser.add_argument("--publish", action="store_true", help="publica figuras e informe")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_MINUTES, help="minutos maximos por paso"
    )
    args = parser.parse_args()

    try:
        steps = steps_for(
            args.mode,
            only=_ids(args.only),
            skip=_ids(args.skip),
            with_diagnostics=args.with_diagnostics,
        )
    except ValueError as error:
        print(_ascii(f"Argumentos no validos: {error}"))
        return 2

    if args.dry_run or not args.report_only:
        minutes = estimate_seconds(steps, args.mode) / 60
        print(f"Modo {args.mode}: {len(steps)} pasos, ~{minutes:.0f} min")
        for step in steps:
            extra = " ".join(step.args_for(args.mode))
            seconds = step.estimate(args.mode)
            print(f"  {step.id}  {step.script} {extra}".rstrip() + f"  (~{seconds} s)")
    if args.dry_run:
        return 0

    out_dir = config.OUTPUTS_DIR / REPRODUCTION_DIRNAME
    if args.report_only:
        log = read_run_log(out_dir / RUN_LOG_NAME)
        if log is None:
            print("No hay registro de una ejecucion previa: el informe usa outputs/ tal cual.")
    else:
        if not data_available():
            print("Faltan los datos confidenciales en data/ (paquete de los autores).")
            return 2
        print()

        def progress(record: dict) -> None:
            seconds = record["seconds"]
            took = f"{seconds:.0f} s" if seconds is not None else "-"
            extra = _ascii(f" ({record['reason']})") if record["reason"] else ""
            print(f"  [{record['id']}] {record['status']:<8} {took:>7}{extra}", flush=True)

        log = run_all(
            steps, args.mode, publish=args.publish, timeout_minutes=args.timeout, progress=progress
        )

    report = build_report(
        Context.default(log),
        meta={
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "commit": git_commit(),
            "versions": package_versions(),
        },
    )
    paths = write_report(report, out_dir, publish_to=PUBLISHED_REPORT if args.publish else None)
    verdict = "sin fallas" if report.ok else "HAY FALLAS"
    print(f"\nInforme de reproduccion: {verdict}: {report.summary_plain()}")
    for item in report.items:
        if item.status is Status.FAILED:
            print(_ascii(f"  FALLA  {item.name}: {item.result}"))
    for path in paths:
        print(f"-> {path}")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
