"""La columna ZINB de las Tablas 4 y 5 y el contraste con pscl (R). Requiere datos; son lentas.

Cada ajuste del ZINB sobre los datos reales tarda ~1 minuto (se hace una sola vez por sesión).
Se pueden omitir con `pytest -m "not slow"`.
"""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.models.marginal_effects import zinb_marginal_effects
from lastmile_exposure.models.zinb import ALPHA, CONST, INFLATE
from lastmile_exposure.reporting.marginal_tables import zinb_marginal_column
from lastmile_exposure.validation.paper_tables import (
    ZINB_TOLERANCE,
    compare_columns,
    load_pscl_oracle,
    load_table4,
    load_table5,
)

pytestmark = pytest.mark.slow

CASES = [("zinb_dynamic", "dynamic", load_table4), ("zinb_static", "static", load_table5)]
IDS = ["tabla4_dinamico", "tabla5_estatico"]
PSCL_SPREAD = 0.05  # dispersión entre dos optimizadores sobre la misma verosimilitud plana


def _table(result, formula="authors"):
    return pd.DataFrame(
        {
            "variable": [v for v, _, _ in config.TABLE_ROWS],
            "zinb": zinb_marginal_column(result, formula),
        }
    )


@pytest.mark.parametrize(("fixture", "tag", "loader"), CASES, ids=IDS)
def test_zinb_column_matches_paper_within_optimizer_tolerance(request, fixture, tag, loader):
    result = request.getfixturevalue(fixture)
    report = compare_columns(_table(result), loader(), {"zinb": ZINB_TOLERANCE})
    assert len(report) == 13
    assert report["ok"].all(), f"Celdas fuera de tolerancia:\n{report[~report['ok']]}"
    nonzero = report[report["paper"] != 0]
    assert (np.sign(nonzero["computed"]) == np.sign(nonzero["paper"])).all()  # mismos signos


@pytest.mark.parametrize(("fixture", "tag", "loader"), CASES, ids=IDS)
def test_wrong_formula_is_far_from_the_paper(request, fixture, tag, loader):
    """Guardia: evaluar la Ec. (4) en las medias de los regresores NO reproduce el paper."""
    result = request.getfixturevalue(fixture)
    wrong = _table(result, "eq4_at_means")
    report = compare_columns(wrong, loader(), {"zinb": ZINB_TOLERANCE})
    assert report["abs_diff"].max() > 1.0
    assert not report["ok"].all()  # y además no pasa el criterio relativo


@pytest.mark.parametrize(("fixture", "tag", "loader"), CASES, ids=IDS)
def test_zinb_collapses_to_negative_binomial_and_formulas_coincide(request, fixture, tag, loader):
    """H21: con estos datos π̂ ≈ 0, así que la fórmula del código y la Ec. (4) son iguales."""
    result = request.getfixturevalue(fixture)
    assert result.pi < 1e-6
    authors = zinb_marginal_effects(result, "authors")
    eq4 = zinb_marginal_effects(result, "eq4")
    assert authors.to_numpy() == pytest.approx(eq4.to_numpy(), rel=1e-5)


@pytest.mark.parametrize(("fixture", "tag", "loader"), CASES, ids=IDS)
def test_same_likelihood_as_pscl_and_a_slightly_higher_maximum(request, fixture, tag, loader):
    """H22: mismo modelo que pscl (misma log-verosimilitud en sus parámetros), óptimo más alto."""
    result = request.getfixturevalue(fixture)
    pscl = load_pscl_oracle(tag)
    params = pscl[[INFLATE, CONST, *config.REGRESSORS, ALPHA]].to_numpy()
    assert float(result.model.loglike(params)) == pytest.approx(pscl["loglik"], abs=5e-3)
    assert 0 < result.llf - pscl["loglik"] < 1.0  # pscl se detiene un poco antes del máximo


@pytest.mark.parametrize(("fixture", "tag", "loader"), CASES, ids=IDS)
def test_marginal_effects_are_close_to_pscl(request, fixture, tag, loader):
    result = request.getfixturevalue(fixture)
    pscl = load_pscl_oracle(tag)
    theirs = pscl[[f"ame_authors:{v}" for v in config.REGRESSORS]].to_numpy()
    mine = zinb_marginal_effects(result, "authors").to_numpy()
    assert np.abs(mine - theirs).max() < PSCL_SPREAD
