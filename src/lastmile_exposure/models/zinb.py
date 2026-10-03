"""ZINB con inflación constante (Ec. 1–3): la columna ZINB de las Tablas 4 y 5.

Paper: Ec. (1)–(3), §4.2.1, pp.10–11; Apéndice A (Claims 1 y 2)
Código de los autores: `pscl::zeroinfl(vehicles ~ X | 1, dist = "negbin")` en
    02_estimation/summary_results_cluster.R; variante `glmmTMB(..., ziformula = ~1)` en
    summary_results.R
Hallazgos (AGENTS.md §7): H10, H11, D2
Estado: implementado (Fase 3). Estimación puntual y efectos marginales. Errores estándar con
    cluster por comuna: pendientes (Fase 4).

Modelo (NB2, mapeo con `statsmodels`): P(Ỹ=0) = π + (1−π)·f_NB(0; μ, θ) y
P(Ỹ=y>0) = (1−π)·f_NB(y; μ, θ), con log μ = β0 + β'D y π CONSTANTE (Ec. 1–3).

`statsmodels` parametriza la dispersión como α = 1/θ (Var = μ + α·μ²), y el paper y `pscl` como
θ. El orden de los parámetros es [inflate_const, const, regresores…, alpha], donde
π = logística(inflate_const).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.count_model import ZeroInflatedNegativeBinomialP

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors

INFLATE = "inflate_const"
ALPHA = "alpha"
CONST = "const"


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
    y_raw = df[outcome].to_numpy(dtype=float)
    if (y_raw < 0).any() or not np.allclose(y_raw, np.round(y_raw)):
        raise ValueError(f"`{outcome}` debe ser un conteo entero no negativo")
    y = np.round(y_raw).astype(int)
    x = sm.add_constant(regressors(df), has_constant="add")
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
