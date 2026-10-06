"""Errores estándar agrupados por comuna (51 comunas) y p-valores normales.

Paper: §4.2.3, p.11 ("clusters a nivel comuna", Cameron & Miller 2015)
Código de los autores: `feols(cluster = ~comuna)` (OLS) y `sandwich::vcovCL(cluster = comuna)`
    sobre `pscl::zeroinfl` (ZINB) en 02_estimation/summary_results_cluster.R y
    summary_results_static_cluster.R; variante sin cluster en summary_results.R (glmmTMB)
Hallazgos (AGENTS.md §7): H11, H12, H21, H25, D3
Estado: implementado (Fase 4A). Sandwich de una vía con la corrección de muestra pequeña de
    `fixest`/`sandwich` (`G/(G−1)·(N−1)/(N−K)`), contrastado contra `statsmodels` y R.

Sandwich de una vía:  V = c · B · (Σ_g s_g s_gᵀ) · B,  con s_g = Σ_{i∈g} s_i (scores del
cluster g) y B = (−H)⁻¹ ("bread", la inversa de la información observada).

- **OLS** (`K̃` y `log K̃`): scores `x_i e_i`, B = (XᵀX)⁻¹.
- **ZINB** (el de los autores): `inference/zinb_sandwich.py` (sandwich del modelo completo).
- **NB equivalente** (`nb_inference`, solo sensibilidad): sandwich de la binomial negativa con
  π = 0. NO es lo que calcularon los autores: con π̂ ≈ 0 el ZINB colapsa en la NB, pero su
  sandwich difiere moderadamente (SE de −17 % a +6 %, H25).
- **`OBSERVATION`** (cada fila es su propio cluster): equivale al `cluster = NULL` de `vcovCL`
  en R, es decir errores robustos SIN agrupar (HC1). No es un cluster por comuna. Se incluye para
  reproducir el script estático de los autores, donde el cluster del ZINB queda NULL (H26).
- **Dos partes** ("OLS K̃>0"): réplica de la aproximación del código de los autores (SE del logit
  sin cluster, SE del OLS con cluster, combinados en cuadratura; H12). Es burda y se replica tal
  cual para reproducir las estrellas.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.discrete.discrete_model import NegativeBinomial
from statsmodels.tools.numdiff import approx_fprime

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors
from lastmile_exposure.models.two_part import TwoPartResult
from lastmile_exposure.models.zinb import ALPHA, CONST, ZinbResult

CORRECTIONS = ("cr1", "g", "none")

# `cluster=OBSERVATION`: cada fila es su propio cluster. Es el `cluster = NULL` de `vcovCL` en R
# ("every observation is assumed to be its own cluster"): errores robustos a heterocedasticidad
# (HC1 con la corrección `cr1`) SIN agrupar. NO es un cluster por comuna. Existe para reproducir
# el script estático de los autores, donde `cluster_var` queda NULL por un error (H26).
OBSERVATION = "observation"


@dataclass(frozen=True)
class Inference:
    """Coeficientes, errores estándar, z y p-valores (normal, dos colas) de los 11 regresores."""

    coef: pd.Series
    se: pd.Series
    n_clusters: int | None  # None si los errores no son por cluster

    @property
    def z(self) -> pd.Series:
        return self.coef / self.se

    @property
    def p(self) -> pd.Series:
        return normal_pvalue(self.z)


def normal_pvalue(z: pd.Series | np.ndarray) -> pd.Series | np.ndarray:
    """p = 2·(1 − Φ(|z|)), como `2 * (1 - pnorm(abs(z)))` del código de los autores."""
    p = 2 * stats.norm.sf(np.abs(z))
    return pd.Series(p, index=z.index) if isinstance(z, pd.Series) else p


def cluster_codes(groups: pd.Series | np.ndarray) -> np.ndarray:
    """Códigos enteros 0..G−1 de las etiquetas de cluster (p. ej. la comuna)."""
    return pd.factorize(np.asarray(groups))[0]


def cluster_groups(df: pd.DataFrame, cluster: str) -> np.ndarray:
    """Etiquetas de cluster de cada fila de `df`: la columna `cluster` u `OBSERVATION`."""
    if cluster == OBSERVATION:
        return np.arange(len(df))
    return df[cluster].to_numpy()


def count_clusters(df: pd.DataFrame, cluster: str) -> int:
    """Nº de clusters de `df` según `cluster` (las filas, si es `OBSERVATION`)."""
    return len(df) if cluster == OBSERVATION else int(df[cluster].nunique())


def cluster_vcov(
    scores: np.ndarray,
    bread: np.ndarray,
    groups: pd.Series | np.ndarray,
    *,
    correction: str = "cr1",
) -> np.ndarray:
    """Matriz de covarianzas sandwich de una vía con cluster.

    `scores`: matriz (N × K) con el score de cada observación en el estimador; `bread`: (K × K),
    la inversa de la información observada (−Hessiano de la log-verosimilitud, o XᵀX para MCO).
    `correction`: `"cr1"` = `G/(G−1)·(N−1)/(N−K)` (lo de `fixest` y `statsmodels`), `"g"` =
    `G/(G−1)`, `"none"` = sin corrección.
    """
    if correction not in CORRECTIONS:
        raise ValueError(f"`correction` debe ser una de {CORRECTIONS}, no {correction!r}")
    scores = np.asarray(scores, dtype=float)
    n, k = scores.shape
    codes = cluster_codes(groups)
    if len(codes) != n:
        raise ValueError("`groups` debe tener una etiqueta por observación")
    g = int(codes.max()) + 1
    cluster_scores = np.zeros((g, k))
    np.add.at(cluster_scores, codes, scores)
    meat = cluster_scores.T @ cluster_scores
    factor = 1.0
    if correction in ("cr1", "g"):
        factor = g / (g - 1.0)
    if correction == "cr1":
        factor *= (n - 1.0) / (n - k)
    return factor * bread @ meat @ bread


def inference_from_vcov(
    coef: pd.Series, vcov: np.ndarray, names: list[str], n_clusters: int | None
) -> Inference:
    """Recorta coeficientes y varianzas a los 11 regresores (en el orden de `names`)."""
    se = pd.Series(np.sqrt(np.diag(vcov)), index=names)
    regs = list(config.REGRESSORS)
    return Inference(coef=coef[regs], se=se[regs], n_clusters=n_clusters)


# --------------------------------------------------------------------------- OLS
def ols_inference(
    result, df: pd.DataFrame, *, cluster: str | None = "comuna", correction: str = "cr1"
) -> Inference:
    """Errores estándar de un OLS de `fit_ols`/`fit_ols_positive`.

    `df` debe ser exactamente el marco (filas) con que se ajustó `result`, y traer la columna
    `cluster`. Con `cluster=None` devuelve los errores estándar clásicos (sin cluster), como el
    `feols` sin `cluster` de `summary_results.R`.
    """
    names = list(result.params.index)
    if cluster is None:
        return inference_from_vcov(result.params, np.asarray(result.cov_params()), names, None)
    x = sm.add_constant(regressors(df), has_constant="add").to_numpy(dtype=float)
    resid = np.asarray(result.resid)
    if len(resid) != len(x):
        raise ValueError("`df` no coincide con las filas del ajuste")
    bread = np.linalg.inv(x.T @ x)
    groups = cluster_groups(df, cluster)
    vcov = cluster_vcov(x * resid[:, None], bread, groups, correction=correction)
    return inference_from_vcov(result.params, vcov, names, count_clusters(df, cluster))


# --------------------------------------------------------------------------- NB equivalente
def nb2_model(df: pd.DataFrame, outcome: str = "vehicles") -> NegativeBinomial:
    """Modelo NB2 sobre los mismos datos del ZINB (para su score y su información)."""
    y = np.round(df[outcome].to_numpy(dtype=float)).astype(int)
    x = sm.add_constant(regressors(df), has_constant="add")
    return NegativeBinomial(y, x, loglike_method="nb2")


def nb2_information(model: NegativeBinomial, params: np.ndarray) -> np.ndarray:
    """Información observada −H de la NB2 en `params` (orden: const, regresores, alpha).

    El `hessian` de `statsmodels` para NB2 no coincide con el Hessiano exacto en α, así que se
    deriva por diferencias finitas centradas el score analítico (verificado contra el Hessiano
    numérico de la log-verosimilitud, `tests/test_cluster_inference.py`).
    """
    hess = approx_fprime(params, lambda q: model.score_obs(q).sum(axis=0), centered=True)
    return -(hess + hess.T) / 2


def nb_inference(
    fit: ZinbResult | pd.Series,
    df: pd.DataFrame,
    *,
    cluster: str | None = "comuna",
    correction: str = "cr1",
    outcome: str = "vehicles",
) -> Inference:
    """Errores estándar de la binomial negativa equivalente al ZINB (π = 0). Solo sensibilidad.

    NO es lo que calcularon los autores: el sandwich del ZINB completo difiere de este (SE de −17 %
    a +6 %, H25; ver `inference/zinb_sandwich.py`, que sí lo replica). Esta versión evita la
    dirección de la inflación, que no está identificada con estos datos, y sirve de contraste.
    `fit` es el `ZinbResult` (se usan sus coeficientes de conteo y α) o una serie de parámetros
    con el índice de `ZinbResult.params`; `df` es el marco de modelación de conteos.
    """
    model = nb2_model(df, outcome)
    names = [CONST, *config.REGRESSORS]
    all_params = fit.params if isinstance(fit, ZinbResult) else fit
    params = all_params.loc[[CONST, *config.REGRESSORS, ALPHA]].to_numpy()
    info = nb2_information(model, params)
    bread = np.linalg.inv(info)
    if cluster is None:
        vcov = bread
        n_clusters = None
    else:
        groups = cluster_groups(df, cluster)
        vcov = cluster_vcov(model.score_obs(params), bread, groups, correction=correction)
        n_clusters = count_clusters(df, cluster)
    coef = all_params.loc[names]
    return inference_from_vcov(coef, vcov[: len(names), : len(names)], names, n_clusters)


# --------------------------------------------------------------------------- dos partes
def two_part_inference(
    result: TwoPartResult, positive_df: pd.DataFrame, *, cluster: str | None = "comuna"
) -> Inference:
    """Réplica de la aproximación de los autores al SE del AME del modelo de dos partes (H12).

        se_1 = |pr·(1−pr)·se_logit·m|,  se_2 = |se_ols·pr|,  se = √(se_1² + se_2²)

    con `se_logit` SIN cluster (modelo del logit), `se_ols` del OLS sobre `K̃>0` (con cluster por
    comuna si `cluster` no es None) y `pr`, `m` tratados como constantes. El p-valor sale de
    `AME/se`. Es una aproximación burda (ignora covarianzas y la variación de `pr` y `m`); se
    replica tal cual porque es lo que produjo las estrellas de las Tablas 4 y 5.
    """
    pr, mean_nonzero = result.pr_nonzero, result.mean_nonzero
    se_logit = result.logit.bse.loc[list(config.REGRESSORS)]
    se_ols = ols_inference(result.ols, positive_df, cluster=cluster).se
    se_1 = (pr * (1 - pr) * se_logit * mean_nonzero).abs()
    se_2 = (se_ols * pr).abs()
    se = np.sqrt(se_1**2 + se_2**2)
    n_clusters = None if cluster is None else count_clusters(positive_df, cluster)
    return Inference(coef=result.ame[list(config.REGRESSORS)], se=se, n_clusters=n_clusters)
