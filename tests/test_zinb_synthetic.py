"""ZINB y sus efectos marginales con datos sintéticos (no necesitan los datos confidenciales).

Se simula un ZINB con parámetros conocidos y se comprueba que `fit_zinb` los recupera y que las
fórmulas de efecto marginal cumplen sus relaciones algebraicas.
"""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.models.marginal_effects import ZINB_FORMULAS, zinb_marginal_effects
from lastmile_exposure.models.zinb import ALPHA, INFLATE, fit_zinb

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
