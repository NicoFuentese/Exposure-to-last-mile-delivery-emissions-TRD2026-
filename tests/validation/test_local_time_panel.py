"""Marcos en hora local (Fase 5) construidos con los archivos diarios reales.

Requiere los datos confidenciales (se salta sin ellos). Lee 42 + 41 CSV una sola vez por sesión.
- Ancla: reconstruir SIN convertir reproduce las bases publicadas (H2, H30), de modo que cualquier
  diferencia de la versión local se debe solo a la conversión de hora.
- Desfases y cobertura por hora local: H18, H19.
"""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.panel import (
    count_frame,
    distance_frame,
    local_count_frame,
    local_distance_frame,
    rebuild_count_frame,
    rebuild_distance_frame,
    restrict_hours,
)
from lastmile_exposure.timeutils.local_time import coverage_by_hour, day_offsets, local_wednesdays

HOURS_7_19 = config.LOCAL_COMPLETE_HOURS


# ------------------------------------------------------------------ ancla
@pytest.mark.parametrize("static", [False, True], ids=["dinamico", "estatico"])
def test_rebuilding_counts_without_conversion_reproduces_the_published_frame(
    daily_counts_all_hours, static
):
    rebuilt = rebuild_count_frame(daily_counts_all_hours, static=static)
    pd.testing.assert_frame_equal(rebuilt, count_frame(static=static), check_exact=True)


@pytest.mark.parametrize("static", [False, True], ids=["dinamico", "estatico"])
def test_rebuilding_distance_without_conversion_reproduces_the_published_frame(
    daily_metrics_all_hours, static
):
    """Las medianas coinciden hasta el ruido de punto flotante (3e-11, H30)."""
    rebuilt = rebuild_distance_frame(daily_metrics_all_hours, static=static)
    pd.testing.assert_frame_equal(
        rebuilt, distance_frame(static=static), check_exact=False, rtol=0, atol=1e-8
    )


# ------------------------------------------------------------------ desfases y cobertura
def test_17_wednesdays_are_utc_minus_4_and_25_are_utc_minus_3(daily_counts_all_hours):
    """H18: de los 42 miércoles, 2024-04-10 … 2024-09-04 están en UTC−4."""
    offsets = day_offsets(daily_counts_all_hours["date"].unique())
    assert offsets.value_counts().to_dict() == {-3.0: 25, -4.0: 17}
    winter = offsets[offsets == -4].index
    assert (winter.min(), winter.max()) == (pd.Timestamp("2024-04-10"), pd.Timestamp("2024-09-04"))


@pytest.mark.parametrize(
    ("fixture", "days"),
    [("daily_counts_all_hours", 42), ("daily_metrics_all_hours", 41)],
    ids=["conteos", "distancia"],
)
def test_local_hours_7_to_19_have_every_day_and_hour_20_only_the_summer_ones(
    request, fixture, days
):
    """H19: 7-19 completas; 20 solo los 25 días UTC−3; 21-22 ninguno (archivo del jueves)."""
    daily = request.getfixturevalue(fixture)
    coverage = coverage_by_hour(local_wednesdays(daily, hours=config.HOURS))
    assert coverage.loc[7:19].eq(days).all()
    assert coverage.loc[20] == 25
    assert 21 not in coverage.index and 22 not in coverage.index


# ------------------------------------------------------------------ marcos locales
@pytest.fixture(scope="module")
def frames(daily_counts_all_hours, daily_metrics_all_hours):
    return {
        "count_local": local_count_frame(daily=daily_counts_all_hours),
        "distance_local": local_distance_frame(daily=daily_metrics_all_hours),
        "count_published": restrict_hours(count_frame(), HOURS_7_19),
        "distance_published": restrict_hours(distance_frame(), HOURS_7_19),
    }


@pytest.mark.parametrize("kind", ["count", "distance"])
def test_local_frames_differ_from_the_published_ones_only_in_the_outcome(frames, kind):
    local, published = frames[f"{kind}_local"], frames[f"{kind}_published"]
    assert len(local) == config.N_HEXAGONS * len(HOURS_7_19)  # 144.872
    assert sorted(local["hour"].unique()) == list(HOURS_7_19)
    assert not local.isna().any().any()
    outcome = "vehicles" if kind == "count" else config.OUTCOME_DISTANCE
    pd.testing.assert_frame_equal(
        local.drop(columns=outcome), published.drop(columns=outcome), check_exact=True
    )
    assert (local[outcome] >= 0).all()


def test_effect_of_the_hour_label_on_the_counts_matches_the_exploration_of_h19(frames):
    """H19: correlación 0,747 entre la mediana local y la publicada, y ceros 31,10 % → 23,40 %."""
    published, local = frames["count_published"]["vehicles"], frames["count_local"]["vehicles"]
    assert np.corrcoef(published, local)[0, 1] == pytest.approx(0.747, abs=5e-4)
    assert (published == 0).mean() * 100 == pytest.approx(31.10, abs=5e-3)
    assert (local == 0).mean() * 100 == pytest.approx(23.40, abs=5e-3)


def test_effect_of_the_hour_label_on_the_distance(frames):
    """Cifras nuevas de la Fase 5: correlación 0,708 y ceros 34,62 % → 25,39 % (horas 7-19)."""
    column = config.OUTCOME_DISTANCE
    published, local = frames["distance_published"][column], frames["distance_local"][column]
    assert np.corrcoef(published, local)[0, 1] == pytest.approx(0.708, abs=5e-4)
    assert (published == 0).mean() * 100 == pytest.approx(34.62, abs=5e-3)
    assert (local == 0).mean() * 100 == pytest.approx(25.39, abs=5e-3)


@pytest.mark.parametrize("static", [False, True], ids=["dinamico", "estatico"])
def test_static_local_frames_keep_the_residential_shares(daily_counts_all_hours, static):
    frame = local_count_frame(static=static, daily=daily_counts_all_hours)
    constant = frame.groupby("hex")["gse_c1b"].nunique().max() == 1
    assert constant == static
