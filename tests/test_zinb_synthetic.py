"""ZINB y sus efectos marginales con datos sintéticos (no necesitan los datos confidenciales).

Se simula un ZINB con parámetros conocidos y se comprueba que `fit_zinb` los recupera y que las
fórmulas de efecto marginal cumplen sus relaciones algebraicas. También se prueba `fit_zinb_mle`
(máximo en la frontera π = 0 o interior) y la derivada de la verosimilitud en la frontera.
"""

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors
from lastmile_exposure.inference.zinb_sandwich import zinb_design, zinb_loglike
from lastmile_exposure.models.marginal_effects import ZINB_FORMULAS, zinb_marginal_effects
from lastmile_exposure.models.zinb import (
    ALPHA,
    BOUNDARY_GAMMA,
    INFLATE,
    SCORE_TOLERANCE,
    fit_zinb,
    fit_zinb_boundary,
    fit_zinb_mle,
    inflation_score_at_zero,
)

TRUE_BETA = np.zeros(len(config.REGRESSORS))
TRUE_BETA[0], TRUE_BETA[1], TRUE_BETA[5] = 0.8, -0.6, 0.5
TRUE_CONST = 0.4
TRUE_THETA = 2.0


def _simulate(pi, n=20_000, seed=3):
    rng = np.random.default_rng(seed)
    x = rng.random((n, len(config.REGRESSORS)))
    mu = np.exp(TRUE_CONST + x @ TRUE_BETA)
    y = rng.negative_binomial(TRUE_THETA, TRUE_THETA / (TRUE_THETA + mu))
    y = np.where(rng.random(n) < pi, 0, y)
    df = pd.DataFrame(x, columns=list(config.REGRESSORS))
    df["vehicles"] = y
    return df


@pytest.fixture(scope="module")
def fit_with_inflation():
    return fit_zinb(_simulate(pi=0.25))


@pytest.fixture(scope="module")
def fit_without_inflation():
    return fit_zinb(_simulate(pi=0.0, seed=5))


def test_recovers_known_parameters(fit_with_inflation):
    r = fit_with_inflation
    assert r.converged and r.max_abs_score < 1e-3
    assert r.pi == pytest.approx(0.25, abs=0.04)
    assert r.theta == pytest.approx(TRUE_THETA, rel=0.25)
    assert r.params["const"] == pytest.approx(TRUE_CONST, abs=0.15)
    assert r.beta.to_numpy() == pytest.approx(TRUE_BETA, abs=0.2)


def test_parameter_names_and_theta_alpha_relation(fit_with_inflation):
    r = fit_with_inflation
    assert list(r.params.index) == [INFLATE, "const", *config.REGRESSORS, ALPHA]
    assert r.theta == pytest.approx(1.0 / r.params[ALPHA])
    assert r.nobs == 20_000


def test_expected_count_is_mu_times_one_minus_pi(fit_with_inflation):
    r = fit_with_inflation
    assert r.expected_count() == pytest.approx(r.mu() * (1 - r.pi))


def test_authors_formula_is_eq4_times_one_minus_pi(fit_with_inflation):
    """H10: con π > 0 la fórmula del código de los autores subestima la Ec. (4) en (1−π)."""
    r = fit_with_inflation
    authors = zinb_marginal_effects(r, "authors")
    eq4 = zinb_marginal_effects(r, "eq4")
    assert r.pi > 0.1
    assert authors.to_numpy() == pytest.approx((eq4 * (1 - r.pi)).to_numpy())
    assert not np.allclose(authors, eq4)


def test_eq4_matches_a_numerical_derivative_of_expected_count(fit_with_inflation):
    """La Ec. (4) promediada es el efecto marginal de E[Ỹ] (derivada numérica del promedio)."""
    r = fit_with_inflation
    col = list(config.REGRESSORS).index("genero_masc")
    x = np.asarray(r.model.exog, dtype=float)
    main = r.params.drop([INFLATE, ALPHA]).to_numpy()
    h = 1e-5

    def mean_ey(shift):
        xs = x.copy()
        xs[:, 1 + col] += shift
        return float(((1 - r.pi) * np.exp(xs @ main)).mean())

    numeric = (mean_ey(h) - mean_ey(-h)) / (2 * h)
    assert zinb_marginal_effects(r, "eq4")["genero_masc"] == pytest.approx(numeric, rel=1e-6)


def test_all_formulas_return_one_value_per_regressor(fit_with_inflation):
    for formula in ZINB_FORMULAS:
        eff = zinb_marginal_effects(fit_with_inflation, formula)
        assert list(eff.index) == list(config.REGRESSORS)
    with pytest.raises(ValueError, match="formula"):
        zinb_marginal_effects(fit_with_inflation, "otra")


def test_without_structural_zeros_pi_goes_to_zero_and_formulas_coincide(fit_without_inflation):
    """Con datos NB puros π̂ → 0 (frontera): las fórmulas del código y de la Ec. (4) coinciden."""
    r = fit_without_inflation
    assert r.pi < 0.03
    authors = zinb_marginal_effects(r, "authors")
    eq4 = zinb_marginal_effects(r, "eq4")
    assert authors.to_numpy() == pytest.approx(eq4.to_numpy(), rel=0.06)


def test_rejects_non_count_outcome():
    df = _simulate(pi=0.0, n=500)
    df["vehicles"] = df["vehicles"] + 0.5
    with pytest.raises(ValueError, match="entero"):
        fit_zinb(df)


def _deflated(n=5_000, seed=11):
    """NB con la mayoría de sus ceros reemplazados por 1: menos ceros de los que la NB espera."""
    df = _simulate(pi=0.0, n=n, seed=seed)
    rng = np.random.default_rng(seed + 100)
    y = df["vehicles"].to_numpy()
    df["vehicles"] = np.where((y == 0) & (rng.random(n) < 0.6), 1, y)
    return df


@pytest.mark.filterwarnings("ignore::statsmodels.tools.sm_exceptions.ConvergenceWarning")
def test_mle_is_the_negative_binomial_at_the_boundary_when_zeros_are_scarce():
    df = _deflated()
    r = fit_zinb_mle(df)
    assert r.boundary and r.converged
    assert r.params[INFLATE] == BOUNDARY_GAMMA and r.pi < 1e-15
    assert inflation_score_at_zero(r.model.endog, r.mu(), float(r.params[ALPHA])) < 0
    x = sm.add_constant(regressors(df), has_constant="add")
    nb = sm.NegativeBinomial(np.round(df["vehicles"]).astype(int), x, loglike_method="nb2").fit(
        method="bfgs", maxiter=3000, gtol=1e-9, disp=0
    )
    assert r.llf == pytest.approx(nb.llf, abs=1e-4)  # misma verosimilitud que la NB
    assert r.params[list(config.REGRESSORS)].to_numpy() == pytest.approx(
        np.asarray(nb.params)[1:-1], abs=1e-4
    )
    assert r.max_abs_score <= SCORE_TOLERANCE


def test_mle_falls_back_to_the_interior_maximum_with_structural_zeros(fit_with_inflation):
    df = _simulate(pi=0.25)  # la misma muestra del fixture
    assert inflation_score_at_zero_of(fit_zinb_boundary(df)) > 0  # subir π mejora: no es frontera
    r = fit_zinb_mle(df)
    assert not r.boundary
    assert r.pi == pytest.approx(fit_with_inflation.pi, rel=1e-6)
    assert r.params.to_numpy() == pytest.approx(fit_with_inflation.params.to_numpy(), rel=1e-6)


def inflation_score_at_zero_of(boundary_fit):
    return inflation_score_at_zero(
        boundary_fit.model.endog, boundary_fit.mu(), float(boundary_fit.params[ALPHA])
    )


def test_inflation_score_at_zero_matches_a_numerical_derivative():
    """∂ℓ/∂π en π = 0 (Σ_{y=0} 1/f₀ − n) contra la diferencia finita de la log-verosimilitud."""
    df = _deflated(n=3_000, seed=4)
    r = fit_zinb_boundary(df)
    y, x = zinb_design(df)
    theta = r.params.to_numpy()
    eps = 1e-6
    shifted = theta.copy()
    shifted[0] = np.log(eps / (1 - eps))
    numeric = (zinb_loglike(y, x, shifted) - zinb_loglike(y, x, theta)) / eps
    assert inflation_score_at_zero_of(r) == pytest.approx(numeric, rel=1e-2)
