"""Marcos de modelación construidos desde los datos reales (H8, H11). Requieren los datos."""

import numpy as np
import pytest

from lastmile_exposure import config
from lastmile_exposure.io.panel import load_counts_dataset
from lastmile_exposure.panel import count_frame, distance_frame


def _expected_columns(outcome):
    return ["hex", "hour", "comuna", outcome, *config.REGRESSORS]


@pytest.mark.parametrize("static", [False, True], ids=["dinamico", "estatico"])
def test_frames_have_expected_shape_and_no_missing(panel, static):
    for frame, outcome in (
        (distance_frame(static=static), config.OUTCOME_DISTANCE),
        (count_frame(static=static), "vehicles"),
    ):
        assert list(frame.columns) == _expected_columns(outcome)
        assert len(frame) == config.N_HEXAGON_HOURS
        assert not frame.isna().any().any()


def test_static_shares_repeat_across_hours(panel):
    frame = distance_frame(static=True)
    assert frame.groupby("hex")["gse_c1b"].nunique().max() == 1
    dynamic = distance_frame()
    assert dynamic.groupby("hex")["gse_c1b"].nunique().max() > 1


def test_static_and_dynamic_frames_share_the_same_outcome(panel):
    d, s = distance_frame(), distance_frame(static=True)
    merged = d.merge(s, on=["hex", "hour"], suffixes=("_d", "_s"))
    assert (merged["median_distance_d"] == merged["median_distance_s"]).all()


def test_count_frame_rounds_half_to_even_like_r(panel):
    """H11: `round()` de R lleva 0,5 a 0, 1,5 a 2 y 2,5 a 2; el 3,3 % de las medianas es x,5."""
    raw = load_counts_dataset()
    frame = count_frame().merge(raw[["hex", "hour", "median_vehicles"]], on=["hex", "hour"])
    half = frame[frame["median_vehicles"] % 1 == 0.5]
    assert len(half) == 5_810
    assert (frame["vehicles"] % 1 == 0).all()
    assert (half["vehicles"] % 2 == 0).all()  # las mitades siempre van al entero PAR
    # Cada día presente tiene >= 1 vehículo, así que la primera mitad posible es 1,5
    assert half["median_vehicles"].min() == 1.5
    assert set(half.loc[half["median_vehicles"] == 1.5, "vehicles"]) == {2.0}
    assert set(half.loc[half["median_vehicles"] == 2.5, "vehicles"]) == {2.0}
    assert np.array_equal(frame["vehicles"], np.round(frame["median_vehicles"]))
