"""Conteo de vehículos Y_hi y su mediana Ỹ_hi sobre la grilla completa del paper.

Paper: §4.1.1 y Fig. 4 (`Y_hi` por día) y mediana entre días `Ỹ_hi` (variable del ZINB)
Código de los autores: 03_gps_hexagon_count.R (`Y_hi` por día), 04_modeling_wedenesday.R
    (mediana y `merge` con el panel; los NA pasan a 0)
Hallazgos (AGENTS.md §7): H2, H3, H14
Estado: implementado (Fase 3) desde los conteos diarios del paquete. `Y_hi` por día, a partir del
    GPS crudo, no se reconstruye (no lo tenemos): ver `io/daily_counts.py`.

Con `include_absent_days=False` (réplica) reproduce EXACTAMENTE `median_vehicles` y
`count_wednesdays` de `00_data/hexagon_model_median_wednesdays_RM.csv`.
"""

import pandas as pd

from lastmile_exposure.exposure.aggregate import median_over_days
from lastmile_exposure.io.panel import load_panel


def count_outside_grid(daily: pd.DataFrame, grid: pd.DataFrame) -> int:
    """Nº de hexágonos con vehículos que no están en la grilla (se descartan, H14)."""
    return len(set(daily["hex"]) - set(grid["hex"]))


def median_vehicles(
    daily: pd.DataFrame,
    grid: pd.DataFrame | None = None,
    *,
    include_absent_days: bool = False,
) -> pd.DataFrame:
    """Mediana de vehículos por hexágono-hora sobre la grilla completa.

    `grid` trae `hex` y `hour` (por defecto, las 178.304 filas del panel). El resultado tiene una
    fila por fila de `grid`, en su mismo orden, con `median_vehicles` y `count_wednesdays`:
    los hexágono-horas sin ningún vehículo en ningún día quedan en 0, y los hexágonos de los
    conteos que no están en la grilla se descartan (H14), como en el código de los autores.

    `include_absent_days` elige entre la réplica (False, mediana sobre los días con ≥1 vehículo)
    y la mediana sobre todos los días contando los ausentes como 0 (True); ver
    `exposure.aggregate`.
    """
    if grid is None:
        grid = load_panel()[["hex", "hour"]]
    medians = median_over_days(daily, include_absent_days=include_absent_days)
    out = grid[["hex", "hour"]].merge(medians, on=["hex", "hour"], how="left")
    out["median_vehicles"] = out["median_vehicles"].fillna(0.0)
    out["count_wednesdays"] = out["count_wednesdays"].fillna(0).astype(int)
    return out
