"""Efectos marginales promedio (AME).

Paper: Ec. (4) (ZINB) y Ec. (6) (OLS)
Código de los autores: `get_marginal_effects` en 02_estimation/summary_results*.R
Hallazgos (AGENTS.md §7): H7, H10, D2
Estado: implementado (Fase 3): OLS, dos partes y ZINB (tres fórmulas: `zinb_marginal_effects`).
"""

import numpy as np
import pandas as pd

from lastmile_exposure.models.zinb import ALPHA, CONST, INFLATE, ZinbResult

ZINB_FORMULAS = ("authors", "eq4", "eq4_at_means")


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


def zinb_marginal_effects(result: ZinbResult, formula: str = "authors") -> pd.Series:
    """Efecto marginal de cada regresor sobre E[Ỹ] = (1−π)·μ en el ZINB con π constante.

    Tres fórmulas (todas con β_k = coeficiente del regresor en log μ):

    - `"authors"` (réplica): `β_k · mean(E[Ỹ]) · (1−π)`, lo que hace el código de los autores
      (`avg_fitted <- mean(predict(type = "response"))` multiplicado por `(1 − zero_prob)`).
      Como `predict(type = "response")` ya incluye el factor (1−π), equivale a
      `β_k · (1−π)² · mean(μ)` (H10).
    - `"eq4"`: Ec. (4) del paper promediada sobre las observaciones: `(1−π)·β_k·mean(μ)`.
      Es el efecto marginal promedio correcto. `authors = eq4 · (1−π)`.
    - `"eq4_at_means"`: Ec. (4) evaluada en las medias de los regresores: `(1−π)·β_k·μ(x̄)`.

    Con π ≈ 0 las dos primeras coinciden; con π > 0 difieren en el factor (1−π).
    """
    beta, pi = result.beta, result.pi
    if formula == "authors":
        return beta * float(result.expected_count().mean()) * (1 - pi)
    if formula == "eq4":
        return beta * (1 - pi) * float(result.mu().mean())
    if formula == "eq4_at_means":
        main = result.params.drop([INFLATE, ALPHA])  # const + regresores, en el orden de `exog`
        x_bar = np.asarray(result.model.exog, dtype=float).mean(axis=0)
        mu_bar = float(np.exp(x_bar @ main.loc[[CONST, *beta.index]].to_numpy()))
        return beta * (1 - pi) * mu_bar
    raise ValueError(f"`formula` debe ser una de {ZINB_FORMULAS}, no {formula!r}")
