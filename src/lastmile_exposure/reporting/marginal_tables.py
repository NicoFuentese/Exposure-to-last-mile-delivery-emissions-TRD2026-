"""Tablas 4 y 5: efectos marginales de las cuatro columnas.

Paper: Tablas 4 (dinámico, p.12) y 5 (estático, p.15)
Código de los autores: `wide_effects` en 02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H7, H8, H10, H12
Estado: implementado (Fase 3): las tres columnas de distancia (`ols_k`, `ols_kpos`, `ols_logk`)
    con `distance_marginal_table` y la columna ZINB con `zinb_marginal_column`. Las estrellas de
    significancia quedan para la inferencia (Fase 4).
"""

import numpy as np
import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.models.marginal_effects import ols_marginal_effects, zinb_marginal_effects
from lastmile_exposure.models.ols import fit_ols
from lastmile_exposure.models.two_part import fit_two_part
from lastmile_exposure.models.zinb import ZinbResult

REFERENCE_VARIABLES = ("edad_mayor_65", "gse_ab")  # categorías omitidas: efecto 0 por definición


def _column(effects: pd.Series) -> list[float]:
    return [
        0.0 if var in REFERENCE_VARIABLES else float(effects[var])
        for var, _, _ in config.TABLE_ROWS
    ]


def distance_marginal_table(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas de distancia de la Tabla 4 (`df` con demografía dinámica) o 5 (estática).

    Devuelve las columnas de `reference/paper_tables/table4_dynamic.csv`, sin estrellas:
    `variable`, `label`, `group`, `zinb` (NaN), `ols_k`, `ols_kpos`, `ols_logk`.
    - `ols_k`: OLS de `K̃` con todas las filas; efecto marginal = coeficiente.
    - `ols_kpos`: AME del modelo de dos partes (logit + OLS sobre `K̃>0`), H7.
    - `ols_logk`: coeficiente crudo del OLS de `log K̃` sobre `K̃>0`.
    """
    ols_k = ols_marginal_effects(fit_ols(df).params)
    ols_kpos = fit_two_part(df).ame
    ols_logk = ols_marginal_effects(fit_ols(df, log_positive=True).params)
    return pd.DataFrame(
        {
            "variable": [v for v, _, _ in config.TABLE_ROWS],
            "label": [lab for _, lab, _ in config.TABLE_ROWS],
            "group": [g for _, _, g in config.TABLE_ROWS],
            "zinb": np.nan,
            "ols_k": _column(ols_k),
            "ols_kpos": _column(ols_kpos),
            "ols_logk": _column(ols_logk),
        }
    )


def zinb_marginal_column(result: ZinbResult, formula: str = "authors") -> list[float]:
    """Columna ZINB de las Tablas 4 y 5 (en el orden de `config.TABLE_ROWS`).

    `formula` elige el efecto marginal (`"authors"`, `"eq4"`, `"eq4_at_means"`; ver
    `models.marginal_effects.zinb_marginal_effects`). Se usa con
    `table.assign(zinb=zinb_marginal_column(result))` sobre la tabla de distancia.
    """
    return _column(zinb_marginal_effects(result, formula))
