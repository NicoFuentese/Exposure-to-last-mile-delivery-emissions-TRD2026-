"""ZINB con inflación constante (Ec. 1–3): la columna ZINB de las Tablas 4 y 5.

Paper: Ec. (1)–(3), §4.2.1, pp.10–11; Apéndice A (Claims 1 y 2)
Código de los autores: `pscl::zeroinfl(vehicles ~ X | 1, dist = "negbin")` en
    02_estimation/summary_results_cluster.R; variante `glmmTMB(..., ziformula = ~1)` en
    summary_results.R
Hallazgos (AGENTS.md §7): H10, H11, H21, H23, H29, D2
Estado: implementado (Fase 3). Estimación puntual y efectos marginales. Errores estándar con
    cluster por comuna: `inference/zinb_sandwich.py` (Fase 4A). `fit_zinb_mle` (2026-10-10)
    reporta el MÁXIMO de la verosimilitud, que con estos datos está en la frontera π = 0 (la NB).

Modelo (NB2, mapeo con `statsmodels`): P(Ỹ=0) = π + (1−π)·f_NB(0; μ, θ) y
P(Ỹ=y>0) = (1−π)·f_NB(y; μ, θ), con log μ = β0 + β'D y π CONSTANTE (Ec. 1–3).

`statsmodels` parametriza la dispersión como α = 1/θ (Var = μ + α·μ²), y el paper y `pscl` como
θ. El orden de los parámetros es [inflate_const, const, regresores…, alpha], donde
π = logística(inflate_const).

Dos formas de ajustar:

- `fit_zinb`: BFGS de `statsmodels` sobre (γ, β, α) con π = logística(γ). Sirve cuando π̂ > 0
  (interior), pero si π̂ = 0 NO puede llegar a la frontera (γ → −∞): se detiene con γ ≈ −21 y los
  β quedan un poco lejos del máximo (hasta 0,03 en los efectos marginales del estático, H23).
- `fit_zinb_mle`: el máximo verdadero. Ajusta la NB (π = 0) y comprueba la condición de primer
  orden en la frontera, ∂ℓ/∂π = Σ_{y=0} 1/f₀ᵢ − n ≤ 0 (`inflation_score_at_zero`); si se cumple,
  la devuelve incrustada con γ = `BOUNDARY_GAMMA` (π ≈ 4·10⁻¹⁸) y si no, cae en `fit_zinb`. Con
  estos datos la derivada vale −24.820 (dinámico) y −43.922 (estático): el máximo está en π = 0
  (H29) y la columna ZINB del paper coincide con la NB a la precisión que imprime (H23).
"""

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.count_model import ZeroInflatedNegativeBinomialP
from statsmodels.tools.sm_exceptions import ConvergenceWarning, HessianInversionWarning

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors

INFLATE = "inflate_const"
ALPHA = "alpha"
CONST = "const"
# logit(π) con que se incrusta la NB (π = 0) en la parametrización del ZINB: π ≈ 4·10⁻¹⁸, que
# numéricamente es 0 (la verosimilitud coincide con la de la NB a todas las cifras).
BOUNDARY_GAMMA = -40.0
# Un ajuste se acepta como máximo si max |score| / n ≤ esto (el mismo `gtol` de `fit_zinb`). La NB
# se valida con su propio score y no con la bandera `converged` de BFGS, que con muestras chicas
# marca "pérdida de precisión" aunque el gradiente ya sea mínimo.
SCORE_TOLERANCE = 1e-6


@dataclass(frozen=True)
class ZinbResult:
    """Resultado del ajuste de un ZINB con inflación constante."""

    model: ZeroInflatedNegativeBinomialP
    params: pd.Series  # índice: inflate_const, const, <regresores>, alpha
    converged: bool
    n_iter: int
    llf: float  # log-verosimilitud en el óptimo
    max_abs_score: float  # max |score| / n en el óptimo (≈ 0 si es un máximo)
    nobs: int
    boundary: bool = False  # True: máximo en la frontera π = 0 (la NB), de `fit_zinb_boundary`

    @property
    def pi(self) -> float:
        """Probabilidad de cero estructural π = logística(inflate_const)."""
        return float(1.0 / (1.0 + np.exp(-self.params[INFLATE])))

    @property
    def theta(self) -> float:
        """Dispersión θ del paper (= 1/α de `statsmodels`)."""
        return float(1.0 / self.params[ALPHA])

    @property
    def beta(self) -> pd.Series:
        """Coeficientes de los 11 regresores en log μ (sin la constante)."""
        return self.params[list(config.REGRESSORS)]

    def mu(self) -> np.ndarray:
        """μ_hi de la componente NB, para cada observación."""
        return np.asarray(self.model.predict(self.params.to_numpy(), which="mean-main"))

    def expected_count(self) -> np.ndarray:
        """E[Ỹ_hi] = (1−π)·μ_hi (Claim 2), para cada observación."""
        return np.asarray(self.model.predict(self.params.to_numpy(), which="mean"))


def _design(df: pd.DataFrame, outcome: str) -> tuple[np.ndarray, pd.DataFrame]:
    """(y entero ≥ 0, matriz de diseño con constante) del marco de modelación de conteos."""
    y_raw = df[outcome].to_numpy(dtype=float)
    if (y_raw < 0).any() or not np.allclose(y_raw, np.round(y_raw)):
        raise ValueError(f"`{outcome}` debe ser un conteo entero no negativo")
    return np.round(y_raw).astype(int), sm.add_constant(regressors(df), has_constant="add")


def _start_params(y: np.ndarray, x: pd.DataFrame) -> np.ndarray:
    """Valores iniciales: Poisson (IRLS) → NB2 (analítico) → ZINB con π inicial ≈ 0,27.

    Sin esto, `statsmodels` arranca con Nelder–Mead sobre toda la muestra, que es lento y poco
    fiable con 178.304 filas.
    """
    pois = sm.GLM(y, x, family=sm.families.Poisson()).fit()
    nb = sm.NegativeBinomial(y, x, loglike_method="nb2").fit(
        start_params=np.append(pois.params.to_numpy(), 1.0), method="bfgs", maxiter=300, disp=0
    )
    nb_params = nb.params.to_numpy()
    return np.concatenate([[-1.0], nb_params[:-1], [nb_params[-1]]])


def fit_zinb(
    df: pd.DataFrame,
    outcome: str = "vehicles",
    *,
    maxiter: int = 2000,
    gtol: float = 1e-6,
    start_params: np.ndarray | None = None,
) -> ZinbResult:
    """Ajusta el ZINB con π constante por máxima verosimilitud (BFGS).

    `df` debe traer `outcome` (conteo entero ≥ 0, p. ej. `vehicles` de `panel.count_frame`) y
    los 11 regresores de `config.REGRESSORS`. Lanza `RuntimeError` si el optimizador no converge.
    """
    y, x = _design(df, outcome)
    n = len(y)

    start = _start_params(y, x) if start_params is None else start_params
    model = ZeroInflatedNegativeBinomialP(y, x, exog_infl=np.ones((n, 1)), inflation="logit", p=2)
    counter = {"k": 0}
    res = model.fit(
        start_params=start,
        method="bfgs",
        maxiter=maxiter,
        gtol=gtol,
        disp=0,
        callback=lambda _: counter.update(k=counter["k"] + 1),
    )
    converged = bool(res.mle_retvals["converged"])
    if not converged:
        raise RuntimeError("El ZINB no convergió (aumenta `maxiter` o revisa `start_params`)")

    names = [INFLATE, *x.columns, ALPHA]
    params = pd.Series(np.asarray(res.params), index=names)
    max_score = float(np.abs(model.score(params.to_numpy())).max() / n)
    return ZinbResult(
        model=model,
        params=params,
        converged=converged,
        n_iter=counter["k"],
        llf=float(res.llf),
        max_abs_score=max_score,
        nobs=n,
    )


def inflation_score_at_zero(y: np.ndarray, mu: np.ndarray, alpha: float) -> float:
    """Derivada de la log-verosimilitud del ZINB respecto de π, evaluada en π = 0.

    Con β y α fijos, ℓ(π) = Σ_{y=0} log(π + (1−π) f₀ᵢ) + Σ_{y>0} log(1−π), donde f₀ᵢ =
    (1 + αμᵢ)^(−1/α) es P(y = 0) de la NB, y su derivada en 0 es Σ_{y=0} (1−f₀ᵢ)/f₀ᵢ − #(y>0) =
    Σ_{y=0} 1/f₀ᵢ − n. Si es ≤ 0 en el máximo de la NB se cumple la condición de primer orden de
    un máximo en la frontera π = 0 (la restricción π ≥ 0 está activa); si es > 0, subir π mejora
    la verosimilitud y el máximo es interior.
    """
    f0 = np.exp(-np.log1p(alpha * np.asarray(mu, dtype=float)) / alpha)
    return float(np.sum(1.0 / f0[np.asarray(y) == 0]) - len(y))


def fit_zinb_boundary(
    df: pd.DataFrame, outcome: str = "vehicles", *, maxiter: int = 3000, gtol: float = 1e-9
) -> ZinbResult:
    """Máximo del ZINB restringido a π = 0, es decir la NB2, en la parametrización del ZINB.

    Ajusta la NB por máxima verosimilitud (BFGS, arranque Poisson) y la incrusta con
    γ = `BOUNDARY_GAMMA`: el `ZinbResult` resultante sirve igual para los efectos marginales y los
    errores estándar. `boundary=True`. NO comprueba que el máximo del ZINB esté en la frontera:
    para eso `fit_zinb_mle`. Lanza `RuntimeError` si el score máximo por observación del ajuste
    supera `SCORE_TOLERANCE`.
    """
    y, x = _design(df, outcome)
    n = len(y)
    pois = sm.GLM(y, x, family=sm.families.Poisson()).fit()
    nb = sm.NegativeBinomial(y, x, loglike_method="nb2")
    counter = {"k": 0}
    with warnings.catch_warnings():
        # el hessiano de statsmodels para NB2 no se usa (la información se deriva aparte) y la
        # convergencia se valida abajo con el score
        warnings.simplefilter("ignore", HessianInversionWarning)
        warnings.simplefilter("ignore", ConvergenceWarning)
        res = nb.fit(
            start_params=np.append(np.asarray(pois.params), 1.0),
            method="bfgs",
            maxiter=maxiter,
            gtol=gtol,
            disp=0,
            callback=lambda _: counter.update(k=counter["k"] + 1),
        )
    names = [INFLATE, *x.columns, ALPHA]
    params = pd.Series(np.concatenate([[BOUNDARY_GAMMA], np.asarray(res.params)]), index=names)
    model = ZeroInflatedNegativeBinomialP(y, x, exog_infl=np.ones((n, 1)), inflation="logit", p=2)
    max_score = float(np.abs(model.score(params.to_numpy())).max() / n)
    if max_score > SCORE_TOLERANCE:
        raise RuntimeError(
            f"La NB no convergió (max|score|/n = {max_score:.1e}; aumenta `maxiter`)"
        )
    return ZinbResult(
        model=model,
        params=params,
        converged=True,
        n_iter=counter["k"],
        llf=float(model.loglike(params.to_numpy())),
        max_abs_score=max_score,
        nobs=n,
        boundary=True,
    )


def fit_zinb_mle(df: pd.DataFrame, outcome: str = "vehicles", **zinb_kwargs) -> ZinbResult:
    """Máximo verdadero del ZINB con π constante: la frontera π = 0 si ahí está, si no `fit_zinb`.

    Ajusta la NB (`fit_zinb_boundary`) y evalúa `inflation_score_at_zero`. Si es ≤ 0 devuelve la
    NB incrustada (π = 0); si es > 0 el máximo es interior y devuelve `fit_zinb(df, outcome,
    **zinb_kwargs)`. La condición de primer orden es necesaria, no suficiente; con estos datos la
    verosimilitud perfilada en π muestra que el máximo global es π = 0 (H29).
    """
    boundary = fit_zinb_boundary(df, outcome)
    y, _ = _design(df, outcome)
    if inflation_score_at_zero(y, boundary.mu(), float(boundary.params[ALPHA])) <= 0.0:
        return boundary
    return fit_zinb(df, outcome, **zinb_kwargs)
