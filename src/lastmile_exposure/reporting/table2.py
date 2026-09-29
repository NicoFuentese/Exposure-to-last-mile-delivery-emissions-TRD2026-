"""Tabla 2: estadística descriptiva de la población flotante.

Paper: Tabla 2, p.7
Código de los autores: (no está en el paquete; reconstruida por nosotros y contrastada con la tabla)
Hallazgos (AGENTS.md §7): H15
Estado: implementado (Fase 3). Reproduce exactamente Mean, Std, Mean (%) y Std (%). La distancia
    de Wasserstein y el ranking de movilidad NO están implementados: quedan en NaN (D10).
"""

import numpy as np
import pandas as pd

# (etiqueta del paper, columna del panel, grupo) en el orden de la Tabla 2
TABLE2_GROUPS = (
    ("Male", "genero_masc", "sex"),
    ("Female", "genero_fem", "sex"),
    ("Under 25", "edad_menor_25", "age"),
    ("25-34", "edad_25_34", "age"),
    ("35-44", "edad_35_44", "age"),
    ("45-54", "edad_45_54", "age"),
    ("55-64", "edad_55_64", "age"),
    ("65+", "edad_mayor_65", "age"),
    ("AB", "gse_ab", "seg"),
    ("C1a", "gse_c1a", "seg"),
    ("C1b", "gse_c1b", "seg"),
    ("C2", "gse_c2", "seg"),
    ("C3", "gse_c3", "seg"),
    ("D", "gse_d", "seg"),
    ("E", "gse_e", "seg"),
)


def _weighted_std(values: pd.Series, weights: pd.Series) -> float:
    mu = np.average(values, weights=weights)
    return float(np.sqrt(np.average((values - mu) ** 2, weights=weights)))


def table2(panel: pd.DataFrame) -> pd.DataFrame:
    """Calcula la Tabla 2 a partir del panel hexágono-hora (`io.panel.load_panel`).

    Definiciones (verificadas contra la tabla publicada, H15):
    - `mean`, `std`: media y desviación estándar (ddof=1) sobre TODAS las filas de la población
      del grupo, es decir `share × poblacion_flotante`.
    - `mean_pct`: `mean` del grupo ÷ población media × 100.
    - `std_pct`: desviación estándar del share, PONDERADA por población, sobre las filas con
      población > 0, × 100.
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
    out["wasserstein"] = np.nan  # pendiente (D10)
    out["mobility_rank"] = np.nan  # pendiente (D10)
    return out
