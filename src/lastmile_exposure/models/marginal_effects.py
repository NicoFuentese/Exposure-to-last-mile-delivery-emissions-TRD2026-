"""Efectos marginales promedio (AME).

Paper: Ec. (4) (ZINB) y Ec. (6) (OLS)
Código de los autores: `get_marginal_effects` en 02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H7, H10, D2
Estado: implementado para OLS y dos partes (Fase 3). ZINB (Ec. 4): pendiente.
"""

import pandas as pd


def ols_marginal_effects(params: pd.Series) -> pd.Series:
    """Ec. (6): en el OLS el efecto marginal de cada regresor es su coeficiente."""
    return params.drop("const", errors="ignore")


def two_part_ame(
    beta_logit: pd.Series, beta_ols: pd.Series, pr_nonzero: float, mean_nonzero: float
) -> pd.Series:
    """AME del modelo de dos partes (logit de `K̃>0` + OLS sobre `K̃>0`).

    Es la fórmula del código de los autores (`ziols`), que produce la columna "OLS K̃>0" de las
    Tablas 4 y 5 (H7):

        AME_k = pr·(1−pr)·β^logit_k·m + β^OLS_k·pr

    con `pr` = media de las probabilidades ajustadas del logit sobre TODAS las filas y `m` =
    media de los valores ajustados del OLS sobre las filas con `K̃>0`.
    """
    pr = pr_nonzero
    return pr * (1 - pr) * beta_logit * mean_nonzero + beta_ols * pr
