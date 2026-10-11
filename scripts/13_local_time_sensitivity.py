"""Sensibilidad en hora local: Tablas 4 y 5 con la hora corregida a America/Santiago (Fase 5).

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/13_local_time_sensitivity.py     # ~10 min (4 ajustes de la NB + errores)

Entrada: data/replication_package_v2/00_data/ y 00_out/{hexagon_count,alternative_metrics}/
         (datos confidenciales, no versionados)
Salida:  outputs/local_time/tables/
           results_<version>_<tabla>_<variante>.csv   efectos, p-valores y estrellas por celda
           comparison_<tabla>_<variante>.csv          celda a celda: publicada 7-19 frente a local
           comparison_summary_<tabla>_<variante>.csv  cambios de signo, de estrellas y de magnitud
           robustness_<tabla>.csv                     las cuatro conclusiones del paper
           fit_summary.csv                            π̂, θ̂, frontera y fórmulas del ZINB por versión
Código:  src/lastmile_exposure/timeutils/local_time.py, panel.py y reporting/sensitivity.py

Compara DOS versiones con las MISMAS horas (7-19), para aislar el efecto de la etiqueta horaria:
- `published_7_19`: la base publicada (camiones en hora UTC, población en hora local) restringida a
  las horas 7-19.
- `local_7_19`: camiones convertidos a hora y miércoles de America/Santiago (AGENTS.md D1, H1,
  H19); población sin cambios. Conteos de 42 miércoles y distancia de 41.
Ambas pierden las horas 20-22, así que ninguna de las dos se compara con el paper completo.

ZINB: efecto marginal con la Ec. (4) del paper, (1-π)·β·mean(μ) (la correcta). El código de los
autores aplica (1-π) dos veces (H10); se guarda aparte. Errores estándar con cluster por comuna
(`paper_text`); en la tabla estática se añade `authors_script` (ZINB sin agrupar, error de su
script, H26). No hay objetivo del paper para esta variante, así que termina SIEMPRE con código 0.
"""

import sys
import time

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.io.daily_counts import load_daily_counts
from lastmile_exposure.io.daily_metrics import load_daily_metrics
from lastmile_exposure.panel import (
    count_frame,
    distance_frame,
    local_count_frame,
    local_distance_frame,
    restrict_hours,
)
from lastmile_exposure.reporting.sensitivity import (
    compare_tables,
    comparison_summary,
    estimate_version,
    robustness_checks,
)
from lastmile_exposure.validation.paper_tables import load_table4, load_table5

HOURS = config.LOCAL_COMPLETE_HOURS
BASE, ALT = "published_7_19", "local_7_19"
TABLES = (("dynamic", False, load_table4), ("static", True, load_table5))
SHOWN = ("zinb", "ols_kpos")  # las dos columnas de las Figs. 6-10


def build_frames(version, static, daily_counts, daily_metrics):
    if version == BASE:
        return (
            restrict_hours(count_frame(static=static), HOURS),
            restrict_hours(distance_frame(static=static), HOURS),
        )
    return (
        local_count_frame(static=static, daily=daily_counts),
        local_distance_frame(static=static, daily=daily_metrics),
    )


def main() -> int:
    out_dir = config.OUTPUTS_DIR / config.Variant.LOCAL_TIME.value / "tables"
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    daily_counts = load_daily_counts(hours=None)
    daily_metrics = load_daily_metrics(hours=None)
    print(f"Archivos diarios leidos ({time.time() - started:.0f} s)", flush=True)

    versions, fits = {}, []
    for tag, static, _ in TABLES:
        for name in (BASE, ALT):
            counts, distance = build_frames(name, static, daily_counts, daily_metrics)
            version = estimate_version(counts, distance, static=static)
            versions[(name, tag)] = version
            fits.append({"version": name, "table": tag, **version.fit})
            for variant, table in version.tables.items():
                table.round(6).to_csv(out_dir / f"results_{name}_{tag}_{variant}.csv", index=False)
            print(
                f"  {name:15s} {tag:8s} filas={version.fit['n_rows']} "
                f"pi={version.fit['pi']:.2e} frontera={version.fit['boundary']} "
                f"ceros={version.fit['zero_share']:.1%} ({time.time() - started:.0f} s)",
                flush=True,
            )
    fit_summary = pd.DataFrame(fits)
    fit_summary.to_csv(out_dir / "fit_summary.csv", index=False)
    print("\nAjuste del ZINB por version:")
    print(fit_summary.round(6).to_string(index=False))

    pd.set_option("display.width", 200)
    for tag, _static, _ in TABLES:
        for variant in versions[(BASE, tag)].tables:
            comparison = compare_tables(
                versions[(BASE, tag)].tables[variant], versions[(ALT, tag)].tables[variant]
            )
            comparison.round(6).to_csv(out_dir / f"comparison_{tag}_{variant}.csv", index=False)
            summary = comparison_summary(comparison)
            summary.round(4).to_csv(out_dir / f"comparison_summary_{tag}_{variant}.csv")
            print(f"\n== {tag} / {variant}: publicada 7-19 -> local 7-19 ==")
            print(summary.round(3).to_string())
            if variant != "paper_text":
                continue
            shown = comparison[comparison["column"].isin(SHOWN)]
            for col in SHOWN:
                part = shown[shown["column"] == col][
                    ["label", "base", "base_sig", "alt", "alt_sig"]
                ]
                print(f"\n  columna {col}:")
                print(part.round(3).to_string(index=False))

    print("\n== Conclusiones del paper (estrellas con cluster por comuna) ==")
    dyn = {
        "paper": load_table4(),
        BASE: versions[(BASE, "dynamic")].tables["paper_text"],
        ALT: versions[(ALT, "dynamic")].tables["paper_text"],
    }
    sta = {
        "paper": load_table5(),
        BASE: versions[(BASE, "static")].tables["paper_text"],
        ALT: versions[(ALT, "static")].tables["paper_text"],
    }
    checks = {name: robustness_checks(dyn[name], sta[name]) for name in dyn}
    table = pd.DataFrame(
        {
            "check": checks["paper"]["check"],
            "paper (impresa)": checks["paper"]["holds"],
            BASE: checks[BASE]["holds"],
            ALT: checks[ALT]["holds"],
        }
    )
    table["robusta"] = table[BASE] & table[ALT]
    table.to_csv(out_dir / "robustness.csv", index=False)
    print(table.to_string(index=False))
    for name in (BASE, ALT):
        print(f"\n  detalle {name}:")
        for _, row in checks[name].iterrows():
            print(f"    {row['check']:15s} {row['holds']!s:5s} {row['detail']}")

    print(f"\n-> {out_dir}  ({time.time() - started:.0f} s)")
    print("Sensibilidad: no hay objetivo del paper para la hora local; no se compara con el paper.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
