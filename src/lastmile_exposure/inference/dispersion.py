"""Test de sobredispersión de Cameron–Trivedi sobre el Poisson (7,73).

Paper: §4.2.1, pp.10–11 ("the Cameron and Trivedi test revealed a dispersion parameter of 7.73,
    significantly greater than 1, with a p-value below 0.001")
Código de los autores: (no incluido en el paquete; el test se aplicó antes de adoptar el ZINB)
Hallazgos (AGENTS.md §7): H27
Estado: implementado (Fase 4B). Reproduce el orden de magnitud y la conclusión del paper; el
    valor numérico queda a ~0,3 % del 7,73 (ver H27).

Test (Cameron y Trivedi, 1990; es el `AER::dispersiontest` por defecto). Bajo la hipótesis nula
de equidispersión, Var(y) = μ; la alternativa es Var(y) = (1 + α)·μ (en el paper, "dispersión"
= 1 + α, "significativamente mayor que 1"). Con la media μ̂ ajustada por el Poisson:

    aux_i = ((y_i − μ̂_i)² − y_i) / μ̂_i,   E[aux_i] = α bajo la alternativa
    α̂ = media(aux),   se = sd(aux) / √n,   estadístico = α̂ / se  (≈ N(0,1) bajo H0)

Es la regresión de `aux` sobre una constante (el t de `lm(aux ~ 1)`). El p-valor es normal,
de una cola ("greater") por defecto, como en `AER`.

La "dispersión" de Pearson (χ² de Pearson / (n − k), la que imprime un quasi-Poisson) se ofrece
como cifra secundaria y aparte: no es el test del paper.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

from lastmile_exposure.demographics.shares import regressors

ALTERNATIVES = ("greater", "less", "two-sided")


@dataclass(frozen=True)
class DispersionTest:
    """Resultado del test de Cameron–Trivedi."""

    alpha: float  # estimador de α en Var(y) = (1 + α)·μ
    dispersion: float  # 1 + α: el "dispersion parameter" del paper
    se: float  # error estándar de α̂
    statistic: float  # α̂ / se
    pvalue: float
    alternative: str
    nobs: int


@dataclass(frozen=True)
class DispersionReport:
    """El test sobre un Poisson ajustado, con la dispersión de Pearson como cifra secundaria."""

    test: DispersionTest
    pearson: float  # χ² de Pearson / (n − k); NO es el test del paper
    n_params: int


def auxiliary_variable(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    """Variable de la regresión auxiliar `((y − μ)² − y) / μ`, con media α bajo Var = (1 + α)μ."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    if y.shape != mu.shape or y.ndim != 1:
        raise ValueError("`y` y `mu` deben ser vectores de la misma longitud")
    if len(y) < 2:
        raise ValueError("Se necesitan al menos 2 observaciones")
    if not (np.isfinite(y).all() and np.isfinite(mu).all()) or (mu <= 0).any():
        raise ValueError("`y` y `mu` deben ser finitos y `mu` estrictamente positivo")
    return ((y - mu) ** 2 - y) / mu


def cameron_trivedi(
    y: np.ndarray, mu: np.ndarray, *, alternative: str = "greater"
) -> DispersionTest:
    """Test de Cameron–Trivedi de equidispersión a partir de `y` y la media ajustada `mu`.

    `alternative`: `"greater"` (sobredispersión, la del paper), `"less"` o `"two-sided"`.
    """
    if alternative not in ALTERNATIVES:
        raise ValueError(f"`alternative` debe ser una de {ALTERNATIVES}, no {alternative!r}")
    aux = auxiliary_variable(y, mu)
    n = len(aux)
    alpha = float(aux.mean())
    se = float(aux.std(ddof=1) / np.sqrt(n))
    statistic = alpha / se
    if alternative == "greater":
        pvalue = float(stats.norm.sf(statistic))
    elif alternative == "less":
        pvalue = float(stats.norm.cdf(statistic))
    else:
        pvalue = float(2 * stats.norm.sf(abs(statistic)))
    return DispersionTest(alpha, 1.0 + alpha, se, statistic, pvalue, alternative, n)


def pearson_dispersion(y: np.ndarray, mu: np.ndarray, n_params: int) -> float:
    """χ² de Pearson / (n − k) del Poisson: la "dispersión" del quasi-Poisson (secundaria)."""
    y, mu = np.asarray(y, dtype=float), np.asarray(mu, dtype=float)
    return float(((y - mu) ** 2 / mu).sum() / (len(y) - n_params))


def poisson_fit(df: pd.DataFrame, outcome: str = "vehicles") -> tuple[np.ndarray, np.ndarray, int]:
    """Poisson (GLM, IRLS) de `outcome` sobre los 11 regresores: `(y, μ̂, nº de parámetros)`.

    Es el modelo que el paper consideró "inicialmente": la misma especificación del ZINB sin la
    inflación ni la dispersión. `df` es el marco de `panel.count_frame` (dinámico o estático).
    """
    y = df[outcome].to_numpy(dtype=float)
    x = sm.add_constant(regressors(df), has_constant="add")
    result = sm.GLM(y, x, family=sm.families.Poisson()).fit()
    if not result.converged:
        raise RuntimeError("El Poisson (IRLS) no convergió")
    return y, np.asarray(result.predict(x)), x.shape[1]


def dispersion_report(
    df: pd.DataFrame, outcome: str = "vehicles", *, alternative: str = "greater"
) -> DispersionReport:
    """Test de Cameron–Trivedi sobre el Poisson de `df` y la dispersión de Pearson (secundaria)."""
    y, mu, n_params = poisson_fit(df, outcome)
    return DispersionReport(
        test=cameron_trivedi(y, mu, alternative=alternative),
        pearson=pearson_dispersion(y, mu, n_params),
        n_params=n_params,
    )
