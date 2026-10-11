"""Reconstruye la mediana de distancia y tiempo desde los archivos diarios y la compara.

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/11_median_distance.py     # ~1 minuto

Entradas (datos confidenciales, no versionados), en data/replication_package_v2/:
    00_out/alternative_metrics/DD-MM-2024_metrics.csv   (41 miércoles; hora y fecha en UTC)
    00_data/miercoles_rm.csv                            (grilla de 11.144 hex x 16 horas)
    00_data/hexagon_model_median_wednesday_alternative_metrics_RM.csv  (base del paper)
Código:  src/lastmile_exposure/io/daily_metrics.py y exposure/vehicles_distance.py
         (ver docs/paper_map.md)

Réplica (mediana sobre los días con tránsito, como el código de los autores): debe coincidir
EXACTAMENTE con `median_distance`, `median_time` y `count_wednesdays` de la base del paper; si no,
sale con código 1. Además informa cuánto cambian los resultados con la variante documentada de
contar los días sin tránsito como 0 (texto del paper). Solo variante `as_published` (hora UTC).
"""

import sys

import numpy as np

from lastmile_exposure.exposure.vehicles_counts import count_outside_grid
from lastmile_exposure.exposure.vehicles_distance import median_distance
from lastmile_exposure.io.daily_metrics import load_daily_metrics
from lastmile_exposure.io.panel import load_distance_dataset, load_panel

CHECKED = ("median_distance", "median_time", "count_wednesdays")


def main() -> int:
    grid = load_panel()[["hex", "hour"]]
    daily = load_daily_metrics()
    print(
        f"Metricas diarias: {daily['date'].nunique()} miercoles, {len(daily):,} filas "
        f"(horas 7-22), {daily['hex'].nunique():,} hexagonos con transito; "
        f"{count_outside_grid(daily, grid):,} fuera de la grilla (se descartan)."
    )

    rebuilt = median_distance(daily, grid)
    paper = load_distance_dataset()[["hex", "hour", *CHECKED]]
    merged = rebuilt.merge(paper, on=["hex", "hour"], suffixes=("_rebuilt", "_paper"))
    print(f"Filas comparadas con la base del paper: {len(merged):,} de {len(grid):,}")
    identical = {}
    for column in CHECKED:
        a, b = merged[f"{column}_rebuilt"], merged[f"{column}_paper"]
        identical[column] = bool(np.isclose(a, b, rtol=0.0, atol=1e-6).all())
        print(
            f"  {column:<16} identico: {identical[column]}  (max|dif| = {(a - b).abs().max():.2e})"
        )
    positive = rebuilt["median_distance"] > 0
    print(
        f"  ceros en median_distance: {(~positive).mean():.4f} "
        f"| positivos: {int(positive.sum()):,} "
        f"| hexagono-horas con datos: {int((rebuilt['count_wednesdays'] > 0).sum()):,} "
        f"| max count_wednesdays: {rebuilt['count_wednesdays'].max()}"
    )

    absent_as_zero = median_distance(daily, grid, include_absent_days=True)
    different = ~np.isclose(rebuilt["median_distance"], absent_as_zero["median_distance"])
    print(f"Variante dias ausentes = 0: filas distintas a la replica: {different.mean():.3f}")
    ok = all(identical.values()) and len(merged) == len(grid)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
