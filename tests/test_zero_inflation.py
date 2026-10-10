"""Verosimilitud perfilada de π y test de frontera con datos sintéticos (sin datos confidenciales).

Se contrasta con implementaciones independientes de `statsmodels` (NB2 y ZINB), con identidades
exactas y con parámetros conocidos. La prueba de calibración (lenta) simula muchas muestras con
π = 0 para comprobar que el p-valor de frontera tiene la distribución que dice la teoría.
"""

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats

from lastmile_exposure import config
from lastmile_exposure.inference.zero_inflation import (
    NB_GAMMA,
    ZeroInflationProfile,
    lr_boundary_test,
    report_from_design,
    zero_inflation_report,
)
from lastmile_exposure.inference.zinb_sandwich import zinb_design, zinb_loglike
from lastmile_exposure.models.zinb import fit_zinb

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
def with_inflation():
    df = _simulate(pi=0.25)
    return df, zero_inflation_report(df)


@pytest.fixture(scope="module")
def without_inflation():
    df = _simulate(pi=0.0, seed=5)
    return df, zero_inflation_report(df)


# --- test de frontera -------------------------------------------------------------------------


def test_boundary_p_value_rules():
    assert lr_boundary_test(-100.0, -100.0) == (0.0, 1.0)  # LR = 0 → p = 1 (masa 0,5 en cero)
    assert lr_boundary_test(-101.0, -100.0) == (0.0, 1.0)  # una diferencia negativa es ruido
    critical = stats.chi2.ppf(0.95, 1)
    lr, p = lr_boundary_test(-100.0 + critical / 2, -100.0)
    assert lr == pytest.approx(critical) and p == pytest.approx(0.025)  # 0,5·P(χ²₁ ≥ 3,84)
    lr, p = lr_boundary_test(-100.0 + 2.706 / 2, -100.0)
    assert p == pytest.approx(0.05, abs=1e-3)  # el 5 % de la mezcla es χ²₁(0,90) = 2,706


def test_boundary_p_value_is_half_the_naive_chi2_p_value():
    for lr in (0.5, 3.0, 10.0, 40.0):
        assert lr_boundary_test(lr / 2, 0.0)[1] == pytest.approx(0.5 * stats.chi2.sf(lr, 1))


# --- identidades y contrastes independientes --------------------------------------------------


def test_the_profile_at_pi_zero_is_the_negative_binomial(without_inflation):
    """ℓ_p(0) coincide con el NB2 de `statsmodels` y con `zinb_loglike` en γ → −∞ (exacto)."""
    df, _ = without_inflation
    y, x = zinb_design(df)
    nb = sm.NegativeBinomial(y, x, loglike_method="nb2").fit(disp=0, method="bfgs", maxiter=500)
    fit0 = ZeroInflationProfile(y, x).fit(0.0)
    assert fit0.loglik == pytest.approx(nb.llf, abs=1e-3)
    assert fit0.alpha == pytest.approx(float(nb.params[-1]), rel=1e-3)
    same_params = zinb_loglike(y, x, np.r_[NB_GAMMA, fit0.theta])
    assert same_params == pytest.approx(float(nb.model.loglike(fit0.theta)), rel=1e-12)


def test_profile_fits_are_maxima(with_inflation):
    """Score de (β, α) ≈ 0 y α fuera de sus cotas en todos los puntos de la grilla."""
    df, _ = with_inflation
    y, x = zinb_design(df)
    profile = ZeroInflationProfile(y, x)
    for pi in (0.0, 0.01, 0.25, 0.4):
        fit = profile.fit(pi)
        assert fit.success and fit.max_abs_score < 1e-6 and not fit.alpha_at_bound


def test_recovers_the_known_inflation_and_matches_statsmodels_zinb(with_inflation):
    """π = 0,25: el máximo perfilado es el MLE del ZINB (el de `statsmodels`), no una grilla."""
    df, report = with_inflation
    sm_fit = fit_zinb(df)
    assert report.pi_hat == pytest.approx(0.25, abs=0.02)
    assert report.pi_hat == pytest.approx(sm_fit.pi, abs=2e-4)
    assert report.loglik_zinb == pytest.approx(sm_fit.llf, abs=0.01)
    assert not report.on_boundary


def test_inflation_is_detected_and_the_interval_covers_the_truth(with_inflation):
    _, report = with_inflation
    assert report.lr > 100 and report.pvalue < 1e-6
    assert report.ci_lower > 0.05  # excluye 0
    assert report.ci_lower < 0.25 < report.ci_upper


def test_interval_endpoints_solve_the_likelihood_ratio_equation(with_inflation):
    """En cada extremo, 2(ℓ_ZINB − ℓ_p(π)) = χ²₁(0,95) (brentq con tolerancia relativa 0,2 %)."""
    df, report = with_inflation
    y, x = zinb_design(df)
    profile = ZeroInflationProfile(y, x)
    critical = stats.chi2.ppf(0.95, 1)
    for end in (report.ci_lower, report.ci_upper):
        assert 2 * (report.loglik_zinb - profile.loglik(end)) == pytest.approx(critical, abs=0.1)


def test_profile_table_is_consistent(with_inflation):
    _, report = with_inflation
    table = report.profile
    assert list(table.columns) == ["pi", "loglik", "lr", "success", "max_abs_score"]
    assert table["pi"].iloc[0] == 0.0 and table["pi"].is_monotonic_increasing
    assert (table["lr"] >= -1e-9).all()  # ningún punto supera al máximo
    assert table["loglik"].iloc[0] == pytest.approx(report.loglik_nb)
    assert table["success"].all()
    # el perfil sube hasta π ≈ 0,25 y baja después: el mínimo de `lr` está en 0,2–0,3
    assert table.loc[table["lr"].idxmin(), "pi"] in (0.2, 0.3)


def test_without_structural_zeros_the_data_do_not_reject_the_null(without_inflation):
    """Datos NB puros: π̂ ≈ 0, p-valor de frontera no significativo y π = 0 dentro del intervalo."""
    df, report = without_inflation
    sm_fit = fit_zinb(df)
    assert report.pi_hat == pytest.approx(sm_fit.pi, abs=2e-4)
    assert report.loglik_zinb == pytest.approx(sm_fit.llf, abs=0.01)
    assert report.lr < 1.0 and report.pvalue > 0.1
    assert report.ci_lower == 0.0 and 0.0 < report.ci_upper < 0.05


def test_log_likelihood_never_exceeds_the_maximum_and_nb_never_exceeds_zinb(without_inflation):
    _, report = without_inflation
    assert report.loglik_zinb >= report.loglik_nb
    assert report.profile["loglik"].max() <= report.loglik_zinb + 1e-9


# --- validación de entradas -------------------------------------------------------------------


def test_input_validation():
    y = np.array([0.0, 1.0, 2.0, 0.0])
    x = np.ones((4, 1))
    with pytest.raises(ValueError, match="mismas filas"):
        ZeroInflationProfile(y, np.ones((3, 1)))
    profile = ZeroInflationProfile(y, x)
    for bad in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError, match=r"\[0, 1\)"):
            profile.fit(bad)


def test_report_builds_from_a_design_matrix_and_from_a_frame(without_inflation):
    df, report = without_inflation
    y, x = zinb_design(df)
    again = report_from_design(y, x)
    assert again.loglik_zinb == pytest.approx(report.loglik_zinb)
    assert again.nobs == len(df) == report.nobs


# --- calibración por simulación (lenta) -------------------------------------------------------


@pytest.mark.slow
def test_boundary_test_is_calibrated_under_the_null():
    """Con π = 0 verdadero, LR ~ 0,5·χ²₀ + 0,5·χ²₁: la mitad de las muestras tiene LR = 0 y
    P(LR > c) = 0,5·P(χ²₁ > c). Con el χ²₁ ingenuo se rechazaría la mitad de lo que corresponde."""
    rng = np.random.default_rng(2024)
    n, reps, grid = 800, 500, (1e-3, 1e-2, 0.05, 0.2)
    lrs = np.empty(reps)
    for r in range(reps):
        x = np.column_stack([np.ones(n), rng.random(n)])
        mu = np.exp(0.5 + 0.8 * x[:, 1])
        y = rng.negative_binomial(1.25, 1.25 / (1.25 + mu)).astype(float)
        profile = ZeroInflationProfile(y, x)
        _, ll_zinb = profile.maximum(grid)
        lrs[r] = lr_boundary_test(ll_zinb, profile.loglik(0.0))[0]
    assert np.mean(lrs == 0.0) == pytest.approx(0.5, abs=0.07)  # la masa en la frontera
    # una cola con potencia: P(LR > 1) = 0,159 (mezcla) frente a 0,317 (χ²₁ ingenuo)
    assert np.mean(lrs > 1.0) == pytest.approx(0.5 * stats.chi2.sf(1.0, 1), abs=0.04)
    # al nivel nominal del 5 % (LR > 2,706) se rechaza ~5 %, no el ~2,5 % del χ²₁ ingenuo
    rejection = np.mean(lrs > stats.chi2.ppf(0.90, 1))
    assert 0.025 <= rejection <= 0.085
