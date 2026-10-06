"""Test de Cameron–Trivedi con datos sintéticos (no necesitan los datos confidenciales).

Se contrasta con cálculos a mano, identidades exactas y con implementaciones independientes de
`statsmodels` (su "CT nb2" valida el vector auxiliar; su OLS sobre una constante, la inferencia).
"""

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.discrete._diagnostics_count import test_poisson_dispersion as sm_dispersion

from lastmile_exposure import config
from lastmile_exposure.inference.dispersion import (
    auxiliary_variable,
    cameron_trivedi,
    dispersion_report,
    pearson_dispersion,
    poisson_fit,
)


def _covariates(n, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.random((n, len(config.REGRESSORS))), columns=list(config.REGRESSORS))
    beta = np.zeros(len(config.REGRESSORS))
    beta[0], beta[2] = 0.6, -0.4
    return df, np.exp(0.5 + df.to_numpy() @ beta), rng


def test_hand_computed_example():
    y, mu = np.array([0.0, 2.0, 4.0]), np.array([1.0, 2.0, 3.0])
    aux = auxiliary_variable(y, mu)
    assert aux.tolist() == pytest.approx([1.0, -1.0, -1.0])  # ((y-mu)^2 - y)/mu
    test = cameron_trivedi(y, mu)
    assert test.alpha == pytest.approx(-1.0 / 3.0)
    assert test.dispersion == pytest.approx(2.0 / 3.0)
    assert test.se == pytest.approx(np.std([1, -1, -1], ddof=1) / np.sqrt(3))
    assert test.statistic == pytest.approx(test.alpha / test.se)
    assert test.nobs == 3


def test_intercept_only_identity():
    """Con μ̂ = ȳ (Poisson solo con constante): 1 + α̂ = Σ(y − ȳ)² / (n·ȳ) exactamente."""
    y = np.random.default_rng(3).negative_binomial(2, 0.4, 500).astype(float)
    test = cameron_trivedi(y, np.full(len(y), y.mean()))
    assert test.dispersion == pytest.approx(((y - y.mean()) ** 2).sum() / (len(y) * y.mean()))


def test_poisson_data_is_not_overdispersed():
    df, mu, rng = _covariates(30_000)
    df["vehicles"] = rng.poisson(mu)
    test = dispersion_report(df).test
    assert test.dispersion == pytest.approx(1.0, abs=0.05)
    assert test.pvalue > 0.01  # no se rechaza la equidispersión


def test_negative_binomial_data_is_overdispersed_with_the_expected_size():
    """NB2 con α conocido: E[aux] = α·μ, luego 1 + α̂ ≈ 1 + α·media(μ)."""
    df, mu, rng = _covariates(30_000, seed=1)
    alpha = 0.8
    df["vehicles"] = rng.negative_binomial(1 / alpha, 1 / (1 + alpha * mu))
    test = dispersion_report(df).test
    assert test.dispersion == pytest.approx(1 + alpha * mu.mean(), rel=0.07)
    assert test.pvalue < 1e-6 and test.statistic > 5


def test_underdispersion_is_detected_by_the_other_alternatives():
    rng = np.random.default_rng(4)
    mu = np.full(20_000, 3.0)
    y = rng.binomial(6, 0.5, len(mu)).astype(float)  # Var = 1,5 < media = 3
    greater, less = cameron_trivedi(y, mu), cameron_trivedi(y, mu, alternative="less")
    two = cameron_trivedi(y, mu, alternative="two-sided")
    assert greater.dispersion < 1 and greater.pvalue > 0.99
    assert less.pvalue < 1e-6
    assert two.pvalue == pytest.approx(2 * min(less.pvalue, greater.pvalue))


def test_statistic_matches_an_independent_ols_on_a_constant():
    """La regresión auxiliar sobre una constante: el t de `statsmodels` (OLS) es el nuestro."""
    df, mu, rng = _covariates(5_000, seed=2)
    df["vehicles"] = rng.negative_binomial(1.5, 0.35, len(df))
    y, mu_hat, _ = poisson_fit(df)
    ours = cameron_trivedi(y, mu_hat)
    ols = sm.OLS(auxiliary_variable(y, mu_hat), np.ones(len(y))).fit(use_t=False)
    assert ours.alpha == pytest.approx(ols.params[0])
    assert ours.se == pytest.approx(ols.bse[0])
    assert ours.statistic == pytest.approx(ols.tvalues[0])
    assert ours.pvalue == pytest.approx(stats.norm.sf(ols.tvalues[0]))


def test_auxiliary_variable_matches_statsmodels_ct_nb2():
    """Su "CT nb2" regresa el mismo `((y−μ)²−y)/μ` sobre μ: el t coincide con el que da nuestro
    vector auxiliar, lo que valida la definición de `aux` con una implementación independiente."""
    df, _, rng = _covariates(5_000, seed=5)
    df["vehicles"] = rng.negative_binomial(1.5, 0.35, len(df))
    x = sm.add_constant(df[list(config.REGRESSORS)])
    poisson = sm.Poisson(df["vehicles"].to_numpy(dtype=float), x).fit(disp=0)
    reference = sm_dispersion(poisson)
    ct_nb2 = reference.statistic[list(reference.method).index("CT nb2")]
    y, mu = df["vehicles"].to_numpy(dtype=float), np.asarray(poisson.predict(x))
    ours = sm.OLS(auxiliary_variable(y, mu), mu).fit(use_t=False).tvalues[0]
    assert ours == pytest.approx(ct_nb2, rel=1e-6)


def test_pearson_dispersion_identity():
    y, mu = np.array([1.0, 3.0, 2.0, 6.0]), np.array([2.0, 2.0, 2.0, 4.0])
    assert pearson_dispersion(y, mu, 1) == pytest.approx(((y - mu) ** 2 / mu).sum() / 3)


def test_poisson_fit_returns_positive_means_and_parameter_count():
    df, mu, rng = _covariates(8_000, seed=6)
    df["vehicles"] = rng.poisson(mu)
    y, mu_hat, k = poisson_fit(df)
    assert k == 12 and len(y) == len(mu_hat) == len(df)
    assert (mu_hat > 0).all()
    assert mu_hat.mean() == pytest.approx(y.mean(), rel=1e-6)  # el Poisson con constante


def test_input_validation():
    ok = np.array([1.0, 2.0, 3.0])
    with pytest.raises(ValueError, match="alternative"):
        cameron_trivedi(ok, ok, alternative="otra")
    with pytest.raises(ValueError, match="misma longitud"):
        cameron_trivedi(ok, ok[:2])
    with pytest.raises(ValueError, match="estrictamente positivo"):
        cameron_trivedi(ok, np.array([1.0, 0.0, 2.0]))
    with pytest.raises(ValueError, match="finitos"):
        cameron_trivedi(ok, np.array([1.0, np.nan, 2.0]))
    with pytest.raises(ValueError, match="al menos 2"):
        cameron_trivedi(np.array([1.0]), np.array([1.0]))
