"""Sandwich con cluster del ZINB completo (inflación, conteo y dispersión): `vcovCL(zeroinfl)`.

Paper: §4.2.3, p.11 (errores estándar agrupados por comuna)
Código de los autores: `sandwich::vcovCL(zinb_model, cluster = comuna)` y luego
    `sqrt(diag(vcov)[1:n_count])` en 02_estimation/summary_results_cluster.R
Hallazgos (AGENTS.md §7): H11, H21, H25
Estado: implementado (Fase 4A). Scores analíticos del ZINB con π constante, contrastados con la
    log-verosimilitud de `statsmodels`; el resultado se contrasta contra `vcovCL` de R/`pscl`.

POR QUÉ NO BASTA LA NB EQUIVALENTE (H25): con estos datos π̂ ≈ 0 y el ZINB colapsa en una
binomial negativa, pero el sandwich del ZINB NO colapsa exactamente con el de ella. El score de
la constante de la inflación y su información son ambos O(π); su cociente (la "influencia" de
ese parámetro sobre cada cluster) es O(1) aunque π → 0, y se transmite al bloque de conteo por
la covarianza cruzada. Efecto medido: SE del ZINB completo entre 17 % menores y 6 % mayores que
los de la NB (π = 0). Para reproducir lo que calcularon los autores se usa el del ZINB completo.

Contraste con R: `vcovCL(zeroinfl)` coincide con este sandwich a ≤ 1,5 % (`tests/validation/
test_cluster_se_oracle.py`), tanto evaluado en los parámetros de `pscl` (inflación −11,7) como en
los nuestros (−21,1): no depende de dónde se detenga el optimizador.

Parámetros (orden de `statsmodels` / `ZinbResult.params`): [inflate_const, const, regresores…,
alpha], con π = logística(inflate_const), log μ = const + x'β y Var = μ + α·μ² (α = 1/θ).
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.special import digamma, gammaln
from statsmodels.tools.numdiff import approx_fprime

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors
from lastmile_exposure.inference.cluster import (
    Inference,
    cluster_groups,
    cluster_vcov,
    count_clusters,
    inference_from_vcov,
)
from lastmile_exposure.models.zinb import ALPHA, CONST, INFLATE, ZinbResult

PARAM_ORDER = (INFLATE, CONST, *config.REGRESSORS, ALPHA)


def zinb_design(df: pd.DataFrame, outcome: str = "vehicles") -> tuple[np.ndarray, np.ndarray]:
    """(y entero, matriz de diseño con constante) del marco de modelación de conteos."""
    y = np.round(df[outcome].to_numpy(dtype=float)).astype(float)
    x = sm.add_constant(regressors(df), has_constant="add").to_numpy(dtype=float)
    return y, x


def zinb_scores(y: np.ndarray, x: np.ndarray, params: np.ndarray) -> np.ndarray:
    """Score analítico por observación del ZINB con π constante (n × (k + 2)).

    `params` en el orden de `PARAM_ORDER`. Derivadas de la log-verosimilitud
    ℓ_i = log(π + (1−π) f0_i) si y = 0 y log(1−π) + log f(y_i) si y > 0:

    - γ (inflación):  y = 0 → π(1−π)(1−f0)/q0 con q0 = π + (1−π)f0;  y > 0 → −π.
    - β (log μ):      y = 0 → w·(−μ/(1+αμ))·x;  y > 0 → (y−μ)/(1+αμ)·x,  con w = (1−π)f0/q0.
    - α (dispersión): derivada de log f respecto de α (ver código), multiplicada por w si y = 0.
    """
    gamma, beta, alpha = params[0], params[1:-1], params[-1]
    pi = 1.0 / (1.0 + np.exp(-gamma))
    r = 1.0 / alpha
    mu = np.exp(x @ beta)
    one_plus = 1.0 + alpha * mu
    zero = y == 0

    log_f0 = -r * np.log1p(alpha * mu)
    f0 = np.exp(log_f0)
    q0 = pi + (1.0 - pi) * f0
    w = np.where(zero, (1.0 - pi) * f0 / q0, 1.0)  # peso de la parte NB en cada fila

    d_beta = np.where(zero, -mu / one_plus, (y - mu) / one_plus)  # d log f / d(x'β)
    d_alpha = (digamma(r) - digamma(y + r) + np.log(one_plus)) / alpha**2 + (y - mu) / (
        alpha * one_plus
    )
    d_gamma = np.where(zero, pi * (1.0 - pi) * (1.0 - f0) / q0, -pi)

    scores = np.empty((len(y), len(params)))
    scores[:, 0] = d_gamma
    scores[:, 1:-1] = (w * d_beta)[:, None] * x
    scores[:, -1] = w * d_alpha
    return scores


def zinb_loglike(y: np.ndarray, x: np.ndarray, params: np.ndarray) -> float:
    """Log-verosimilitud del ZINB (para verificar los scores; no se usa en la estimación)."""
    gamma, beta, alpha = params[0], params[1:-1], params[-1]
    pi = 1.0 / (1.0 + np.exp(-gamma))
    r = 1.0 / alpha
    mu = np.exp(x @ beta)
    log_f = (
        gammaln(y + r) - gammaln(r) - gammaln(y + 1.0) + r * np.log(r / (r + mu))
        + y * np.log(mu / (r + mu))
    )  # fmt: skip
    zero_part = np.log(pi + (1.0 - pi) * np.exp(log_f))
    return float(np.where(y == 0, zero_part, np.log1p(-pi) + log_f).sum())


def zinb_information(y: np.ndarray, x: np.ndarray, params: np.ndarray) -> np.ndarray:
    """Información observada −H del ZINB: Jacobiano numérico (centrado) del score analítico."""
    hess = approx_fprime(params, lambda q: zinb_scores(y, x, q).sum(axis=0), centered=True)
    return -(hess + hess.T) / 2


def _scaled_inverse(info: np.ndarray) -> np.ndarray:
    """Inversa con preacondicionamiento por la diagonal.

    La información de la constante de inflación es O(π) (≈ 1e-5 con π ≈ 1e-10) mientras la del
    conteo es O(1e5): sin escalar, la inversión pierde cifras. Con D = diag(√|I_jj|) se invierte
    D⁻¹ I D⁻¹ (bien condicionada) y se devuelve D⁻¹ (·)⁻¹ D⁻¹.
    """
    d = np.sqrt(np.abs(np.diag(info)))
    scaled = info / np.outer(d, d)
    return np.linalg.inv(scaled) / np.outer(d, d)


def zinb_inference(
    fit: ZinbResult | pd.Series,
    df: pd.DataFrame,
    *,
    cluster: str | None = "comuna",
    correction: str = "cr1",
    outcome: str = "vehicles",
) -> Inference:
    """Errores estándar del bloque de conteo del sandwich del ZINB completo.

    Replica `sqrt(diag(vcovCL(zeroinfl, cluster = comuna))[1:n_count])` del código de los
    autores. `fit` es el `ZinbResult` ajustado o directamente una serie de parámetros (índice de
    `ZinbResult.params`), p. ej. los de `pscl` (`validation.paper_tables.load_pscl_oracle`) para
    contrastar con R; `df` es el marco de modelación de conteos (`panel.count_frame`).
    Con `cluster=None` devuelve los errores basados en el modelo (la inversa de la información),
    como el `vcov(model)$cond` de `glmmTMB` de `summary_results.R`.
    """
    point = (fit.params if isinstance(fit, ZinbResult) else fit).loc[list(PARAM_ORDER)]
    y, x = zinb_design(df, outcome)
    theta = point.to_numpy(dtype=float)
    bread = _scaled_inverse(zinb_information(y, x, theta))
    if cluster is None:
        vcov, n_clusters = bread, None
    else:
        scores = zinb_scores(y, x, theta)
        vcov = cluster_vcov(scores, bread, cluster_groups(df, cluster), correction=correction)
        n_clusters = count_clusters(df, cluster)
    return inference_from_vcov(point, vcov, list(PARAM_ORDER), n_clusters)
