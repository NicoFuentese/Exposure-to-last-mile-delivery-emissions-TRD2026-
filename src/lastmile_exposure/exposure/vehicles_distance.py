"""Distancia `K_hi` y tiempo: su mediana entre días `K̃_hi` sobre la grilla completa del paper.

Paper: §4.1.2 y Fig. 5 (`K_hi` por día) y mediana entre días `K̃_hi` (variable de los OLS)
Código de los autores: 03_alternative_metrics.R (`K_hi` por día), 04_modeling_wednesday_alternative_
    metrics.R (mediana y `merge` con el panel; los NA pasan a 0)
Hallazgos (AGENTS.md §7): H2, H3, H4, H30, D4, D7
Estado: implementado (2026-10-10) desde los 41 archivos diarios del paquete v2. `K_hi` por día, a
    partir del GPS crudo, no se reconstruye (no lo tenemos): ver `io/daily_metrics.py`.

Con `include_absent_days=False` (réplica) reproduce EXACTAMENTE `median_distance`, `median_time` y
`count_wednesdays` de `00_data/hexagon_model_median_wednesday_alternative_metrics_RM.csv` (H30).

OJO con la definición de `K_hi` (H4, D7): el paper dice que cuenta los metros recorridos
estrictamente dentro del hexágono (Fig. 5), pero el código de los autores (y su README) solo suma
los pares de pings consecutivos del mismo camión que quedan en el mismo hexágono y la misma hora.
La mediana de este módulo es la de los datos publicados, es decir, la del código.
"""

import pandas as pd

from lastmile_exposure.io.panel import load_panel

KEYS = ["hex", "hour"]
METRICS = {"total_distance_m": "median_distance", "total_time_sec": "median_time"}
COLUMNS = [*KEYS, "median_distance", "median_time", "count_wednesdays"]


def median_over_days(daily: pd.DataFrame, *, include_absent_days: bool = False) -> pd.DataFrame:
    """Mediana de distancia y tiempo por (hex, hour) entre los miércoles de `daily`.

    `daily` es el marco largo de `io.daily_metrics.load_daily_metrics`. Devuelve `hex, hour,
    median_distance, median_time, count_wednesdays`, con una fila por cada (hex, hour) que tuvo
    algún dato en algún día. `count_wednesdays` es siempre el número de días con dato (el `.N` del
    código de los autores), también en el modo `include_absent_days=True`.

    - Código de los autores (`include_absent_days=False`, réplica): la mediana se calcula SOLO
      sobre los días en que el hexágono-hora tuvo tránsito. Un hexágono-hora con datos un solo
      miércoles queda con esa cifra como "mediana" (sesgo al alza, igual que en los conteos, H2).
    - Texto del paper (`include_absent_days=True`): la mediana sobre TODOS los días de la muestra,
      contando los días sin tránsito como 0. Variante "corregida" que se ejecuta además.
    """
    if include_absent_days:
        out = pd.DataFrame()
        for column, name in METRICS.items():
            wide = daily.pivot(index=KEYS, columns="date", values=column)
            out[name] = wide.fillna(0).median(axis=1)
        out["count_wednesdays"] = wide.notna().sum(axis=1)  # igual para ambas métricas
        return out.reset_index()[COLUMNS]
    grouped = daily.groupby(KEYS)
    out = grouped.agg(
        median_distance=("total_distance_m", "median"),
        median_time=("total_time_sec", "median"),
        count_wednesdays=("date", "size"),
    )
    return out.reset_index()[COLUMNS]


def median_distance(
    daily: pd.DataFrame,
    grid: pd.DataFrame | None = None,
    *,
    include_absent_days: bool = False,
) -> pd.DataFrame:
    """Mediana de distancia y tiempo por hexágono-hora sobre la grilla completa.

    `grid` trae `hex` y `hour` (por defecto, las 178.304 filas del panel). El resultado tiene una
    fila por fila de `grid`, en su mismo orden, con `median_distance`, `median_time` y
    `count_wednesdays`: los hexágono-horas sin datos en ningún día quedan en 0, y los hexágonos de
    los archivos diarios que no están en la grilla se descartan (H14), como en el código de los
    autores (`merge(..., all.x = TRUE)` y NA → 0).

    `include_absent_days` elige entre la réplica (False) y la mediana contando los días sin
    tránsito como 0 (True); ver `median_over_days`.
    """
    if grid is None:
        grid = load_panel()[KEYS]
    medians = median_over_days(daily, include_absent_days=include_absent_days)
    out = grid[KEYS].merge(medians, on=KEYS, how="left")
    out[["median_distance", "median_time"]] = out[["median_distance", "median_time"]].fillna(0.0)
    out["count_wednesdays"] = out["count_wednesdays"].fillna(0).astype(int)
    return out
