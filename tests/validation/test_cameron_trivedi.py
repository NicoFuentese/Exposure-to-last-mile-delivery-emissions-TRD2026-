"""Cameron–Trivedi sobre los datos reales frente al 7,73 del paper (AGENTS.md H27).

Requiere los datos confidenciales (se salta sin ellos). El estadístico principal es el del paper:
Poisson dinámico con los 11 regresores, H0: dispersión = 1. Se compara con el 7,73 con el criterio
relativo de 1 % (D2). Las variantes (solo constante, 41 miércoles, días ausentes como 0, estático,
Pearson) NO se usan para "acertar": se fijan aquí tal como salen, incluidas las que no reproducen.
"""

import numpy as np
import pytest

from lastmile_exposure.exposure.vehicles_counts import median_vehicles
from lastmile_exposure.inference.dispersion import cameron_trivedi, dispersion_report
from lastmile_exposure.io.daily_counts import load_daily_counts
from lastmile_exposure.panel import attach_regressors
from lastmile_exposure.validation.paper_tables import DISPERSION_TOLERANCE, load_paper_scalars


def _paper():
    return float(load_paper_scalars()["cameron_trivedi_dispersion"])


def _frame_from_daily(panel, daily, *, include_absent_days=False):
    med = median_vehicles(daily, panel[["hex", "hour"]], include_absent_days=include_absent_days)
    base = panel.drop(columns=[c for c in ("median_vehicles", "count_wednesdays") if c in panel])
    raw = base.merge(med[["hex", "hour", "median_vehicles"]], on=["hex", "hour"])
    raw = raw.assign(vehicles=np.round(raw["median_vehicles"]))
    return attach_regressors(raw, "vehicles", static=False)


def test_paper_scalars_are_loaded():
    scalars = load_paper_scalars()
    assert scalars["cameron_trivedi_dispersion"] == 7.73
    assert scalars["moran_i_distance"] == 0.4694 and scalars["moran_i_vehicles"] == 0.4756
    assert DISPERSION_TOLERANCE.limit(7.73) == pytest.approx(0.0773)


def test_dynamic_dispersion_reproduces_the_paper_within_tolerance(model_frames):
    """El criterio acordado: error relativo ≤ 1 %, dispersión > 1 y p < 0,001."""
    test = dispersion_report(model_frames["dynamic"]["count"]).test
    assert abs(test.dispersion - _paper()) <= DISPERSION_TOLERANCE.limit(_paper())
    assert test.dispersion > 1 and test.pvalue < 0.001
    assert test.statistic > 50  # "significantly greater than 1" por un margen enorme
    assert test.nobs == 178_304


def test_documented_values_are_pinned(model_frames):
    """Valores tal como salen (no son del paper): si cambian, hay que revisar H27."""
    dyn = dispersion_report(model_frames["dynamic"]["count"])
    sta = dispersion_report(model_frames["static"]["count"])
    assert dyn.test.dispersion == pytest.approx(7.750, abs=0.005)
    assert dyn.pearson == pytest.approx(7.738, abs=0.005)  # secundaria: no es el test del paper
    assert sta.test.dispersion == pytest.approx(7.494, abs=0.005)
    assert sta.pearson == pytest.approx(7.497, abs=0.005)
    assert dyn.n_params == 12


def test_variants_are_documented_including_those_that_do_not_reproduce(
    model_frames, panel, daily_counts
):
    """H27: ninguna variante da 7,73 a dos decimales; algunas quedan fuera de la tolerancia."""
    paper, limit = _paper(), DISPERSION_TOLERANCE.limit(_paper())
    counts = model_frames["dynamic"]["count"]["vehicles"].to_numpy(dtype=float)
    constant_only = cameron_trivedi(counts, np.full(len(counts), counts.mean())).dispersion
    assert constant_only == pytest.approx(8.284, abs=0.005)  # Poisson sin regresores
    assert abs(constant_only - paper) > limit  # NO reproduce

    daily_41 = load_daily_counts(exclude_dates=("2024-05-01",))
    d41 = dispersion_report(_frame_from_daily(panel, daily_41)).test.dispersion
    assert d41 == pytest.approx(7.785, abs=0.005)  # 41 miércoles, como declara el paper
    assert abs(d41 - paper) <= limit  # dentro de la tolerancia, pero no más cerca que 42

    absent_zero = dispersion_report(
        _frame_from_daily(panel, daily_counts, include_absent_days=True)
    ).test.dispersion
    assert absent_zero == pytest.approx(9.82, abs=0.02)  # días ausentes como 0
    assert abs(absent_zero - paper) > limit  # NO reproduce
