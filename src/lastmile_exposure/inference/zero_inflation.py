"""Probabilidad de cero estructural π del ZINB: verosimilitud perfilada y test de frontera.

Paper: §4.2.1, pp.10–11 (Ec. 1: π constante, "probabilidad de un cero estructural": parques,
    zonas sin cobertura). El paper NO reporta ningún valor de π: no hay cifra que reproducir.
Código de los autores: `pscl::zeroinfl(vehicles ~ X | 1, dist = "negbin")` en
    02_estimation/summary_results_cluster.R (la inflación `| 1` es solo una constante)
Hallazgos (AGENTS.md §7): H21, H22, H29
Estado: implementado (Fase 4D). Es un DIAGNÓSTICO de nuestros datos dentro del modelo del paper,
    no una réplica: se documenta lo que los datos dicen de π, sin objetivo del paper contra el
    cual compararlo.

Qué se calcula. Para π fijo se maximiza la log-verosimilitud del ZINB (Ec. 1–3) sobre (β, α):
`ℓ_p(π)`, la verosimilitud perfilada. `ℓ_p(0)` es la de la binomial negativa (NB). Con eso:

- **π̂** (el argmax de `ℓ_p`) y la log-verosimilitud máxima `ℓ_ZINB`.
- **Test de razón de verosimilitudes** de H0: π = 0 (ZINB frente a NB), `LR = 2(ℓ_ZINB − ℓ_NB)`.
  π = 0 está en la FRONTERA del espacio paramétrico, así que LR no es χ²₁: bajo H0 es la mezcla
  0,5·χ²₀ + 0,5·χ²₁ (Self y Liang, 1987; Chernoff, 1954), con p-valor `0,5·P(χ²₁ ≥ LR)` si
  LR > 0 y 1 si LR = 0 (la masa 0,5 en cero). Usar el χ²₁ ingenuo daría la mitad de rechazos
  de los que corresponden (2,5 % en vez de 5 % al nivel nominal del 5 %).
- **Intervalo de confianza** de π por inversión de la verosimilitud perfilada: los π con
  `2(ℓ_ZINB − ℓ_p(π)) ≤ χ²₁(nivel)`. Si π̂ está en la frontera, el intervalo es [0, cota].

Identificación. Lo que no está identificado con estos datos es el coeficiente en escala logit
(γ = logit π → −∞, razón por la que el optimizador se detiene en valores distintos: H21–H23).
π SÍ está identificado: la verosimilitud es empinada en π, con el máximo en la frontera.

Numérica. La NB es el límite γ → −∞; se evalúa en `NB_GAMMA = −40` (π ≈ 4·10⁻¹⁸, para el cual
n·π ≈ 10⁻¹² en la log-verosimilitud: numéricamente idéntico a la NB). Reutiliza la
log-verosimilitud y los scores analíticos de `zinb_sandwich` (ya validados contra `statsmodels`).
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.optimize import brentq, minimize, minimize_scalar

from lastmile_exposure.inference.zinb_sandwich import zinb_design, zinb_loglike, zinb_scores

NB_GAMMA = -40.0  # logit(π) con el que se evalúa la NB (π ≈ 4e-18)
ALPHA_BOUNDS = (1e-4, 50.0)  # cotas de α = 1/θ en la optimización perfilada
DEFAULT_GRID = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 0.05, 0.1, 0.2, 0.3, 0.5)
DEFAULT_LEVEL = 0.95
MAX_SCORE_TOLERANCE = 1e-6  # max |score| / n con el que se acepta un ajuste perfilado


@dataclass(frozen=True)
class ProfileFit:
    """Ajuste del ZINB con π fijo: máximo de (β, α)."""

    pi: float
    loglik: float
    theta: np.ndarray  # [const, regresores…, alpha]
    success: bool  # el optimizador declaró convergencia
    max_abs_score: float  # max |score| / n de (β, α) en el óptimo (≈ 0 si es un máximo)

    @property
    def alpha(self) -> float:
        return float(self.theta[-1])

    @property
    def alpha_at_bound(self) -> bool:
        lo, hi = ALPHA_BOUNDS
        return bool(np.isclose(self.alpha, lo, rtol=1e-6) or np.isclose(self.alpha, hi, rtol=1e-6))


@dataclass(frozen=True)
class ZeroInflationReport:
    """π̂, test de frontera H0: π = 0 e intervalo de confianza perfilado."""

    nobs: int
    pi_hat: float  # 0,0 si el máximo está en la frontera
    loglik_nb: float  # ℓ_p(0): la NB
    loglik_zinb: float  # sup de ℓ_p(π): ≥ loglik_nb
    lr: float  # 2·(loglik_zinb − loglik_nb) ≥ 0
    pvalue: float  # de frontera: 0,5·P(χ²₁ ≥ LR); 1 si LR = 0
    level: float
    ci_lower: float
    ci_upper: float  # NaN si no queda acotado en la grilla
    profile: pd.DataFrame  # pi, loglik, lr (= 2(ℓ_ZINB − ℓ_p(π))), success, max_abs_score

    @property
    def on_boundary(self) -> bool:
        """π̂ = 0: la verosimilitud perfilada es máxima en la NB."""
        return self.pi_hat == 0.0


def lr_boundary_test(loglik_zinb: float, loglik_nb: float) -> tuple[float, float]:
    """(LR, p-valor) de H0: π = 0 con π en la frontera: mezcla 0,5·χ²₀ + 0,5·χ²₁.

    `loglik_zinb` es el MÁXIMO del ZINB (≥ el de la NB; una diferencia negativa, por ruido del
    optimizador, se trata como 0). El p-valor es 1 si LR = 0 y `0,5·P(χ²₁ ≥ LR)` si LR > 0.
    """
    lr = max(0.0, 2.0 * (loglik_zinb - loglik_nb))
    if lr == 0.0:
        return 0.0, 1.0
    return lr, float(0.5 * stats.chi2.sf(lr, df=1))


def default_start(y: np.ndarray, x: np.ndarray) -> np.ndarray:
    """Valores iniciales [const, regresores…, α]: Poisson (IRLS) y α por momentos."""
    pois = sm.GLM(y, x, family=sm.families.Poisson()).fit()
    mu = np.asarray(pois.predict(x))
    alpha = float(((y - mu) ** 2 - mu).sum() / (mu**2).sum())
    alpha = float(np.clip(alpha, 10 * ALPHA_BOUNDS[0], ALPHA_BOUNDS[1] / 10))
    return np.append(np.asarray(pois.params, dtype=float), alpha)


def _gamma(pi: float) -> float:
    if not 0.0 <= pi < 1.0:
        raise ValueError(f"π debe estar en [0, 1), no {pi!r}")
    return NB_GAMMA if pi == 0.0 else float(np.log(pi / (1.0 - pi)))


class ZeroInflationProfile:
    """Verosimilitud perfilada del ZINB en π (con caché y arranques tibios).

    `y` es el conteo (entero ≥ 0) y `x` la matriz de diseño CON constante (como
    `zinb_design`). Cada `fit(π)` maximiza sobre (β, α) con π fijo; es el costo dominante
    (segundos con 178.304 filas), por eso los ajustes se guardan y cada uno arranca desde el
    ya ajustado más cercano.
    """

    def __init__(self, y: np.ndarray, x: np.ndarray, *, start: np.ndarray | None = None):
        self.y = np.asarray(y, dtype=float)
        self.x = np.asarray(x, dtype=float)
        if len(self.y) != len(self.x):
            raise ValueError("`y` y `x` deben tener las mismas filas")
        self._start = default_start(self.y, self.x) if start is None else np.asarray(start, float)
        self._fits: dict[float, ProfileFit] = {}

    def fit(self, pi: float) -> ProfileFit:
        """Máximo de la log-verosimilitud sobre (β, α) con π fijo (π = 0: la NB)."""
        pi = float(pi)
        gamma = _gamma(pi)
        if pi in self._fits:
            return self._fits[pi]
        if self._fits:
            near = min(self._fits, key=lambda q: abs(_gamma(q) - gamma))
            theta0 = self._fits[near].theta
        else:
            theta0 = self._start
        n = len(self.y)

        def value_and_grad(theta: np.ndarray) -> tuple[float, np.ndarray]:
            params = np.r_[gamma, theta]
            scores = zinb_scores(self.y, self.x, params)[:, 1:]
            return -zinb_loglike(self.y, self.x, params) / n, -scores.sum(axis=0) / n

        bounds = [(None, None)] * (len(theta0) - 1) + [ALPHA_BOUNDS]
        res = minimize(
            value_and_grad,
            theta0,
            jac=True,
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 2000, "ftol": 1e-14, "gtol": 1e-9, "maxcor": 30},
        )
        _, grad = value_and_grad(res.x)
        fit = ProfileFit(
            pi=pi,
            loglik=float(-res.fun * n),
            theta=np.asarray(res.x, dtype=float),
            success=bool(res.success),
            max_abs_score=float(np.abs(grad[:-1]).max()),  # el score de α puede estar en su cota
        )
        if not (fit.success or fit.max_abs_score < MAX_SCORE_TOLERANCE):
            raise RuntimeError(f"El ajuste perfilado en π = {pi:g} no convergió: {res.message}")
        self._fits[pi] = fit
        return fit

    def loglik(self, pi: float) -> float:
        return self.fit(pi).loglik

    def table(self, grid=DEFAULT_GRID) -> pd.DataFrame:
        """Perfil `ℓ_p(π)` en la grilla (en orden ascendente, con la NB en π = 0)."""
        points = sorted({0.0, *map(float, grid)})
        fits = [self.fit(p) for p in points]
        return pd.DataFrame(
            {
                "pi": points,
                "loglik": [f.loglik for f in fits],
                "success": [f.success for f in fits],
                "max_abs_score": [f.max_abs_score for f in fits],
            }
        )

    def maximum(self, grid=DEFAULT_GRID) -> tuple[float, float]:
        """(π̂, ℓ_ZINB): el argmax y el máximo de la verosimilitud perfilada.

        Se evalúa la NB (π = 0) y la grilla; si el mejor punto es la NB el máximo está en la
        frontera (π̂ = 0). Si es interior se refina en el intervalo entre sus vecinos (búsqueda
        acotada en la escala logit).
        """
        points = sorted({0.0, *map(float, grid)})
        lls = [self.fit(p).loglik for p in points]
        k = int(np.argmax(lls))
        if k == 0:
            return 0.0, lls[0]
        lo = _gamma(points[k - 1])
        hi = _gamma(points[k + 1]) if k + 1 < len(points) else _gamma(0.99)

        def neg(gamma: float) -> float:
            return -self.loglik(1.0 / (1.0 + np.exp(-gamma)))

        opt = minimize_scalar(neg, bounds=(lo, hi), method="bounded", options={"xatol": 1e-4})
        pi_ref = float(1.0 / (1.0 + np.exp(-opt.x)))
        if -opt.fun >= lls[k]:
            return pi_ref, float(-opt.fun)
        return points[k], lls[k]

    def interval(
        self, pi_hat: float, loglik_max: float, level=DEFAULT_LEVEL, grid=DEFAULT_GRID
    ) -> tuple[float, float]:
        """Intervalo de confianza de π: `{π : 2(ℓ_ZINB − ℓ_p(π)) ≤ χ²₁(nivel)}`.

        Los extremos se buscan con `brentq` entre puntos consecutivos de la grilla. La cota
        inferior es 0 si π = 0 pertenece al intervalo; la superior es NaN si no queda acotada
        dentro de la grilla.
        """
        critical = float(stats.chi2.ppf(level, df=1))
        points = sorted({0.0, *map(float, grid)})

        def excess(pi: float) -> float:
            return 2.0 * (loglik_max - self.loglik(pi))

        def crossing(inside: float, outside: float) -> float:
            return float(
                brentq(lambda p: excess(p) - critical, inside, outside, xtol=1e-14, rtol=2e-3)
            )

        def search(start: float, candidates: list[float], default: float) -> float:
            previous = start
            for c in candidates:
                if excess(c) > critical:
                    return crossing(previous, c)
                previous = c
            return default

        upper = search(pi_hat, [p for p in points if p > pi_hat], float("nan"))
        lower = 0.0
        if pi_hat > 0.0:
            below = [p for p in reversed(points) if p < pi_hat]  # incluye 0,0 al final
            lower = search(pi_hat, below, 0.0)
        return lower, upper


def report_from_design(
    y: np.ndarray,
    x: np.ndarray,
    *,
    grid=DEFAULT_GRID,
    level: float = DEFAULT_LEVEL,
    start: np.ndarray | None = None,
) -> ZeroInflationReport:
    """Perfil, π̂, test de frontera e intervalo para (y, x) con constante en `x`."""
    profile = ZeroInflationProfile(y, x, start=start)
    table = profile.table(grid)
    pi_hat, loglik_zinb = profile.maximum(grid)
    loglik_nb = profile.loglik(0.0)
    lr, pvalue = lr_boundary_test(loglik_zinb, loglik_nb)
    lower, upper = profile.interval(pi_hat, loglik_zinb, level, grid)
    table["lr"] = 2.0 * (loglik_zinb - table["loglik"])
    return ZeroInflationReport(
        nobs=len(profile.y),
        pi_hat=pi_hat,
        loglik_nb=loglik_nb,
        loglik_zinb=loglik_zinb,
        lr=lr,
        pvalue=pvalue,
        level=level,
        ci_lower=lower,
        ci_upper=upper,
        profile=table[["pi", "loglik", "lr", "success", "max_abs_score"]],
    )


def zero_inflation_report(
    df: pd.DataFrame, outcome: str = "vehicles", **kwargs
) -> ZeroInflationReport:
    """`report_from_design` sobre el marco de modelación de conteos (`panel.count_frame`)."""
    y, x = zinb_design(df, outcome)
    return report_from_design(y, x, **kwargs)
