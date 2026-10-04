"""Tabla 2: estadística descriptiva de la población flotante.

Paper: Tabla 2, p.7
Código de los autores: (no está en el paquete; reconstruida por nosotros y contrastada con la tabla)
Hallazgos (AGENTS.md §7): H15, H24
Estado: implementado (Fase 3). Mean, Std, Mean (%) y Std (%) se reproducen exactamente. Las
    columnas de movilidad (Wasserstein normalizada y ranking) se calculan con el método descrito
    en el paper a partir de las distancias que se le pasen (`demographics/mobility.py`), pero NO
    reproducen los valores publicados (H24); sin distancias quedan en NaN.
"""

import numpy as np
import pandas as pd

from lastmile_exposure.config import TABLE2_GROUPS
from lastmile_exposure.demographics.mobility import mobility_rank, normalize_by_median


def _weighted_std(values: pd.Series, weights: pd.Series) -> float:
    mu = np.average(values, weights=weights)
    return float(np.sqrt(np.average((values - mu) ** 2, weights=weights)))


def table2(panel: pd.DataFrame, mobility_raw: pd.Series | None = None) -> pd.DataFrame:
    """Calcula la Tabla 2 a partir del panel hexágono-hora (`io.panel.load_panel`).

    Definiciones (verificadas contra la tabla publicada, H15):
    - `mean`, `std`: media y desviación estándar (ddof=1) sobre TODAS las filas de la población
      del grupo, es decir `share × poblacion_flotante`.
    - `mean_pct`: `mean` del grupo ÷ población media × 100.
    - `std_pct`: desviación estándar del share, PONDERADA por población, sobre las filas con
      población > 0, × 100.

    `mobility_raw` (opcional) son las distancias de Wasserstein en metros por grupo
    (`demographics.mobility.mobility_distances`); con ellas se llenan `wasserstein` (normalizada
    por la mediana de su dimensión, como la tabla publicada) y `mobility_rank`. Calcularlas es
    lento (~10 min), por eso no se hace aquí.
    """
    pop = panel["poblacion_flotante"]
    rows = [
        {
            "variable": "Avg Population",
            "group": "total",
            "mean": pop.mean(),
            "std": pop.std(),
            "mean_pct": np.nan,
            "std_pct": np.nan,
        }
    ]
    positive = panel[pop > 0]
    for label, col, group in TABLE2_GROUPS:
        count = panel[col] * pop
        rows.append(
            {
                "variable": label,
                "group": group,
                "mean": count.mean(),
                "std": count.std(),
                "mean_pct": 100 * count.mean() / pop.mean(),
                "std_pct": 100 * _weighted_std(positive[col], positive["poblacion_flotante"]),
            }
        )
    out = pd.DataFrame(rows)
    out["wasserstein"] = np.nan
    out["mobility_rank"] = np.nan
    if mobility_raw is not None:
        labels = [label for label, _, _ in TABLE2_GROUPS]
        normalized = normalize_by_median(mobility_raw.reindex(labels))
        out["wasserstein"] = out["variable"].map(normalized)
        out["mobility_rank"] = out["variable"].map(mobility_rank(normalized))
    return out
