"""Agregación entre días: mediana solo sobre días presentes vs. sobre todos los días.

Paper: §4.1.1 y §4.1.2 ("se toma la mediana entre días para cada hexágono y hora")
Código de los autores: 04_modeling_wedenesday.R (`median(vehicles)` por `hex, hour`, con
    `count_wednesdays = .N`)
Hallazgos (AGENTS.md §7): H2, D4
Estado: implementado (Fase 3). Réplica fiel (días presentes) y variante con días ausentes = 0.

Entrada: marco largo `hex, hour, date, vehicles` (de `io/daily_counts.py`), donde un día ausente
para un (hex, hour) significa que ese día no hubo ningún vehículo.

- Código de los autores (`include_absent_days=False`, réplica): la mediana se calcula SOLO sobre
  los días en que el hexágono-hora tuvo ≥1 vehículo. Un hexágono-hora con un vehículo un solo
  miércoles queda con esa cifra como "mediana" (sesgo al alza, H2).
- Texto del paper (`include_absent_days=True`): la mediana sobre TODOS los días de la muestra,
  contando los días sin vehículos como 0. Es la variante "corregida", que se ejecuta además de
  la réplica y no en lugar de ella.
"""

import pandas as pd

COLUMNS = ["hex", "hour", "median_vehicles", "count_wednesdays"]


def median_over_days(daily: pd.DataFrame, *, include_absent_days: bool = False) -> pd.DataFrame:
    """Mediana por (hex, hour) entre los miércoles de `daily`.

    Devuelve `hex, hour, median_vehicles, count_wednesdays`, con una fila por cada (hex, hour)
    que tuvo algún vehículo en algún día. `count_wednesdays` es siempre el número de días en que
    hubo ≥1 vehículo (igual que `.N` del código de los autores), también en el modo
    `include_absent_days=True`.
    """
    if include_absent_days:
        wide = daily.pivot(index=["hex", "hour"], columns="date", values="vehicles")
        out = pd.DataFrame(
            {
                "median_vehicles": wide.fillna(0).median(axis=1),
                "count_wednesdays": wide.notna().sum(axis=1),
            }
        )
    else:
        out = daily.groupby(["hex", "hour"])["vehicles"].agg(
            median_vehicles="median", count_wednesdays="size"
        )
    return out.reset_index()[COLUMNS]
