"""Conversión UTC → hora local (Fase 5): casos sintéticos, sin datos confidenciales."""

import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.exposure.vehicles_counts import median_vehicles
from lastmile_exposure.timeutils.local_time import (
    coverage_by_hour,
    day_offsets,
    local_wednesdays,
    to_local,
)

SUMMER = "2024-04-03"  # miércoles UTC−3 (último antes del cambio de abril)
WINTER = "2024-04-10"  # miércoles UTC−4 (primero después)


def _daily(dates=(SUMMER, WINTER), *, hex_id="a"):
    """Un hexágono con `vehicles` = hora UTC en las 24 horas de cada día."""
    rows = [
        {"hex": hex_id, "hour": h, "date": pd.Timestamp(d), "vehicles": h}
        for d in dates
        for h in range(24)
    ]
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ desfases
@pytest.mark.parametrize(
    ("date", "offset"),
    [
        ("2024-01-03", -3),
        ("2024-04-03", -3),  # antes del cambio del 6-7 de abril
        ("2024-04-10", -4),  # después
        ("2024-09-04", -4),  # antes del cambio del 7-8 de septiembre
        ("2024-09-11", -3),  # después
        ("2024-11-27", -3),
    ],
)
def test_wednesday_offsets_of_2024(date, offset):
    assert day_offsets([date]).iloc[0] == offset


def test_day_offsets_rejects_a_day_where_the_offset_changes():
    """El cambio de abril ocurre el domingo 7 a las 03:00 UTC: ese día mezcla -3 y -4."""
    with pytest.raises(ValueError, match="cambia dentro del día"):
        day_offsets(["2024-04-07"])


def test_day_offsets_is_one_value_per_distinct_date():
    out = day_offsets([SUMMER, WINTER, SUMMER])
    assert out.index.tolist() == [pd.Timestamp(SUMMER), pd.Timestamp(WINTER)]
    assert out.tolist() == [-3, -4]


# ------------------------------------------------------------------ conversión
def test_to_local_shifts_hours_and_keeps_order_and_columns():
    daily = _daily()
    out = to_local(daily)
    assert out[list(daily.columns)].equals(daily)  # no filtra ni altera lo que había
    row = out[(out["date"] == SUMMER) & (out["hour"] == 10)].iloc[0]
    assert (row["local_hour"], row["local_date"], row["utc_offset"]) == (
        7,
        pd.Timestamp(SUMMER),
        -3,
    )
    row = out[(out["date"] == WINTER) & (out["hour"] == 11)].iloc[0]
    assert (row["local_hour"], row["utc_offset"]) == (7, -4)


def test_early_utc_hours_belong_to_the_previous_local_day():
    out = to_local(_daily([WINTER]))
    early = out[out["hour"] < 4]  # UTC−4: 00-03 UTC son 20-23 h del martes
    assert (early["local_date"] == pd.Timestamp("2024-04-09")).all()
    assert early["local_hour"].tolist() == [20, 21, 22, 23]
    late = out[out["hour"] >= 4]
    assert (late["local_date"] == pd.Timestamp(WINTER)).all()


# ------------------------------------------------------------------ miércoles locales
def test_local_wednesdays_keeps_hours_7_to_19_from_the_same_utc_wednesday():
    daily = _daily()
    out = local_wednesdays(daily)
    assert list(out.columns) == list(daily.columns)
    assert sorted(out["hour"].unique()) == list(config.LOCAL_COMPLETE_HOURS)
    assert len(out) == 2 * len(config.LOCAL_COMPLETE_HOURS)
    # `vehicles` guarda la hora UTC de origen: local 7 viene de UTC 10 (−3) o 11 (−4)
    summer = out[out["date"] == SUMMER].set_index("hour")["vehicles"]
    winter = out[out["date"] == WINTER].set_index("hour")["vehicles"]
    assert summer.loc[7] == 10 and summer.loc[19] == 22
    assert winter.loc[7] == 11 and winter.loc[19] == 23
    assert (out["date"].dt.dayofweek == 2).all()


def test_local_wednesdays_drops_tuesday_evening_and_respects_custom_hours():
    out = local_wednesdays(_daily([WINTER]), hours=range(24))
    # UTC−4: los 4 primeros registros UTC son martes local y se pierden; el resto, 20 horas
    assert len(out) == 20 and out["hour"].min() == 0 and out["hour"].max() == 19
    assert (out["date"] == pd.Timestamp(WINTER)).all()
    only = local_wednesdays(_daily(), hours=[8, 9])
    assert sorted(only["hour"].unique()) == [8, 9] and len(only) == 4


def test_coverage_by_hour_matches_the_utc_minus_3_and_minus_4_split():
    """Hora local 20: solo los días UTC−3 (UTC 23); 21-22: ninguno (H19)."""
    out = local_wednesdays(_daily([SUMMER, WINTER, "2024-09-11"]), hours=range(7, 23))
    coverage = coverage_by_hour(out)
    assert coverage.loc[7:19].eq(3).all()
    assert coverage.loc[20] == 2  # 2024-04-03 y 2024-09-11 (UTC−3)
    assert 21 not in coverage.index and 22 not in coverage.index


def test_converted_frame_feeds_the_median_without_changes():
    """La salida de `local_wednesdays` entra tal cual a `median_vehicles` (mismo esquema)."""
    grid = pd.DataFrame({"hex": ["a"] * 3, "hour": [7, 8, 22]})
    out = median_vehicles(local_wednesdays(_daily()), grid)
    # local 7: UTC 10 (−3) y UTC 11 (−4) → mediana 10,5; local 8: 11 y 12 → 11,5
    assert out["median_vehicles"].tolist() == [10.5, 11.5, 0.0]
    assert out["count_wednesdays"].tolist() == [2, 2, 0]


def test_other_columns_are_preserved_for_distance_frames():
    daily = _daily().assign(total_distance_m=100.0, total_time_sec=5.0)
    out = local_wednesdays(daily)
    assert {"total_distance_m", "total_time_sec"} <= set(out.columns)
    assert (out["total_distance_m"] == 100.0).all()
