"""π del ZINB sobre los datos reales (AGENTS.md H29). DIAGNÓSTICO: el paper no reporta π.

Requiere los datos confidenciales (se salta sin ellos). No hay cifra del paper que reproducir: se
fijan aquí los valores tal como salen, para que un cambio en el código o en los datos sea visible.
Lo que sí se comprueba contra algo externo: el ZINB de `statsmodels` y `pscl` (R) coinciden con
lo que dice el perfil (π ≈ 0, log-verosimilitud igual a la de la NB, π de `pscl` dentro del IC).
"""

import numpy as np
import pytest

from lastmile_exposure.models.zinb import INFLATE
from lastmile_exposure.validation.paper_tables import load_pscl_oracle

pytestmark = pytest.mark.slow

TAGS = ("dynamic", "static")
LOGLIK_NB = {"dynamic": -347_284.370, "static": -342_420.097}
CI_UPPER = {"dynamic": 7.73e-5, "static": 4.37e-5}
# 2·(ℓ_ZINB − ℓ_p(π)) en π = 1e-3 y 1e-2 (la verosimilitud es empinada en π)
LR_AT = {"dynamic": {1e-3: 50.18, 1e-2: 542.42}, "static": {1e-3: 87.98, 1e-2: 892.23}}


@pytest.mark.parametrize("tag", TAGS)
def test_the_maximum_is_on_the_boundary_and_the_data_do_not_support_structural_zeros(
    zero_inflation_reports, tag
):
    r = zero_inflation_reports[tag]
    assert r.nobs == 178_304
    assert r.on_boundary and r.pi_hat == 0.0  # el máximo de la verosimilitud perfilada es la NB
    assert r.lr == 0.0 and r.pvalue == 1.0  # el test de frontera no rechaza H0: π = 0
    assert r.loglik_zinb == r.loglik_nb


@pytest.mark.parametrize("tag", TAGS)
def test_documented_log_likelihood_of_the_nb(zero_inflation_reports, tag):
    assert zero_inflation_reports[tag].loglik_nb == pytest.approx(LOGLIK_NB[tag], abs=0.01)


@pytest.mark.parametrize("tag", TAGS)
def test_upper_bound_of_the_interval_is_tiny(zero_inflation_reports, tag):
    """El IC del 95 % es [0, cota] con la cota entre 1e-5 y 1e-4 (≈ 8e-5 y 4e-5)."""
    r = zero_inflation_reports[tag]
    assert r.ci_lower == 0.0
    assert 1e-5 < r.ci_upper < 1e-4
    assert r.ci_upper == pytest.approx(CI_UPPER[tag], rel=0.02)


@pytest.mark.parametrize("tag", TAGS)
def test_profile_is_steep_and_strictly_increasing_in_pi(zero_inflation_reports, tag):
    """La verosimilitud es empinada en π (no plana): ya π = 0,001 está rechazado con holgura."""
    table = zero_inflation_reports[tag].profile.set_index("pi")
    assert table["success"].all() and (table["max_abs_score"] < 1e-6).all()
    assert table["lr"].is_monotonic_increasing and table["lr"].iloc[0] == 0.0
    for pi, expected in LR_AT[tag].items():
        assert table.loc[pi, "lr"] == pytest.approx(expected, abs=0.05)
    assert table.loc[1e-3, "lr"] > 10 * 3.841  # ≥ 13 veces el crítico del 95 % (50,2 y 88,0)


@pytest.mark.parametrize("tag", TAGS)
def test_pscl_inflation_is_inside_the_interval(zero_inflation_reports, tag):
    """`pscl` (R) llega a π ≈ 8e-6 / 6e-6: dentro del IC, es decir, indistinguible de 0."""
    r = zero_inflation_reports[tag]
    pi_pscl = 1.0 / (1.0 + np.exp(-float(load_pscl_oracle(tag)[INFLATE])))
    assert 0.0 < pi_pscl < 1e-4
    assert r.ci_lower <= pi_pscl <= r.ci_upper


def test_statsmodels_zinb_reaches_the_same_likelihood_as_the_nb(
    zero_inflation_reports, zinb_dynamic, zinb_static
):
    """El ZINB de `statsmodels` (BFGS) termina con π ≈ 0 y la log-verosimilitud de la NB."""
    for tag, fit in (("dynamic", zinb_dynamic), ("static", zinb_static)):
        assert fit.pi < 1e-6
        assert fit.llf == pytest.approx(zero_inflation_reports[tag].loglik_nb, abs=0.01)
