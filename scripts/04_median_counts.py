"""Reconstruye la mediana de conteos (`median_vehicles`) desde los archivos diarios y la compara.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/04_median_counts.py       # ~1 minuto

Entradas (datos confidenciales, no versionados), en data/replication_package_v2/:
    00_out/hexagon_count/hexagon_count_*_cleaned.csv   (42 miércoles; hora y fecha en UTC)
    00_data/miercoles_rm.csv                            (grilla de 11.144 hex x 16 horas)
    00_data/hexagon_model_median_wednesdays_RM.csv      (base del paper, para comparar)
Código:  src/lastmile_exposure/io/daily_counts.py, exposure/aggregate.py,
         exposure/vehicles_counts.py (ver docs/paper_map.md)

Réplica (mediana sobre los días con >=1 vehículo, como el código de los autores): debe coincidir
EXACTAMENTE con `median_vehicles` y `count_wednesdays` de la base del paper; si no, sale con
código 1. Además informa cuánto cambian los resultados con las dos variantes documentadas:
(a) mediana sobre todos los días contando los ausentes como 0 (texto del paper) y (b) excluyendo
el feriado 2024-05-01 (41 miércoles, D4). Solo variante `as_published` (hora UTC).
"""

import sys

import numpy as np

from lastmile_exposure.exposure.vehicles_counts import count_outside_grid, median_vehicles
from lastmile_exposure.io.daily_counts import load_daily_counts
from lastmile_exposure.io.panel import load_counts_dataset, load_panel

HOLIDAY = "2024-05-01"


def _share_different(a, b) -> float:
    return float((~np.isclose(a["median_vehicles"], b["median_vehicles"])).mean())


def main() -> int:
    grid = load_panel()[["hex", "hour"]]
    daily = load_daily_counts()
    n_days = daily["date"].nunique()
    print(
        f"Conteos diarios: {n_days} miercoles, {len(daily):,} filas (horas 7-22), "
        f"{daily['hex'].nunique():,} hexagonos con vehiculos; "
        f"{count_outside_grid(daily, grid):,} fuera de la grilla (se descartan)."
    )

    rebuilt = median_vehicles(daily, grid)
    paper = load_counts_dataset()[["hex", "hour", "median_vehicles", "count_wednesdays"]]
    merged = rebuilt.merge(paper, on=["hex", "hour"], suffixes=("_rebuilt", "_paper"))
    same_median = bool((merged["median_vehicles_rebuilt"] == merged["median_vehicles_paper"]).all())
    same_count = bool(
        (merged["count_wednesdays_rebuilt"] == merged["count_wednesdays_paper"]).all()
    )
    print(f"Filas comparadas con la base del paper: {len(merged):,} de {len(grid):,}")
    print(f"  median_vehicles identico: {same_median}")
    print(f"  count_wednesdays identico: {same_count}")
    print(
        f"  ceros: {(rebuilt['median_vehicles'] == 0).mean():.4f} | "
        f"medianas x,5: {int((rebuilt['median_vehicles'] % 1 == 0.5).sum()):,} | "
        f"max count_wednesdays: {rebuilt['count_wednesdays'].max()}"
    )

    absent_as_zero = median_vehicles(daily, grid, include_absent_days=True)
    print(
        "Variante (a) dias ausentes = 0: filas distintas a la replica: "
        f"{_share_different(rebuilt, absent_as_zero):.3f}"
    )
    daily_41 = load_daily_counts(exclude_dates=(HOLIDAY,))
    rebuilt_41 = median_vehicles(daily_41, grid)
    print(
        f"Variante (b) sin {HOLIDAY} ({daily_41['date'].nunique()} miercoles): "
        f"filas distintas a la replica: {_share_different(rebuilt, rebuilt_41):.3f}"
    )
    return 0 if (same_median and same_count and len(merged) == len(grid)) else 1


if __name__ == "__main__":
    sys.exit(main())
