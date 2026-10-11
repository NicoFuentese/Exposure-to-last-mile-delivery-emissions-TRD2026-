"""La mediana de distancia y tiempo desde los archivos diarios coincide con la del paper.

Requiere los datos confidenciales (se salta sin ellos). Lee 41 CSV una sola vez por sesión.
H30: igualdad exacta de `median_distance`, `median_time` y `count_wednesdays` en las 178.304 filas.
"""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.exposure.vehicles_counts import count_outside_grid
from lastmile_exposure.exposure.vehicles_distance import median_distance
from lastmile_exposure.io.panel import load_distance_dataset

COLUMNS = ["median_distance", "median_time", "count_wednesdays"]


@pytest.fixture(scope="module")
def paper():
    return load_distance_dataset()[["hex", "hour", *COLUMNS]]


@pytest.fixture(scope="module")
def rebuilt(daily_metrics, panel):
    return median_distance(daily_metrics, panel[["hex", "hour"]])


def test_daily_files_are_41_wednesdays_in_utc(daily_metrics):
    """H3, H30: 41 miércoles (no hay archivo del 2024-05-01, feriado), sin julio ni diciembre."""
    dates = daily_metrics["date"].drop_duplicates()
    assert len(dates) == 41
    assert (dates.dt.dayofweek == 2).all()
    assert pd.Timestamp("2024-05-01") not in set(dates)
    assert pd.Timestamp("2024-09-18") not in set(dates)
    assert not dates.dt.month.isin([7, 12]).any()
    assert set(daily_metrics["hour"]) == set(config.HOURS)


def test_rebuilt_medians_are_identical_to_the_papers(rebuilt, paper):
    """Réplica fiel: igualdad exacta (178.304 filas); la distancia a ruido de punto flotante."""
    merged = rebuilt.merge(paper, on=["hex", "hour"], suffixes=("_rebuilt", "_paper"))
    assert len(merged) == config.N_HEXAGON_HOURS
    for column in COLUMNS:
        a, b = merged[f"{column}_rebuilt"], merged[f"{column}_paper"]
        assert np.allclose(a, b, rtol=0.0, atol=1e-6), column
    assert (merged["count_wednesdays_rebuilt"] == merged["count_wednesdays_paper"]).all()
    assert (merged["median_time_rebuilt"] == merged["median_time_paper"]).all()


def test_rebuilt_summary_statistics(rebuilt):
    assert (rebuilt["median_distance"] == 0).mean() == pytest.approx(0.3279, abs=5e-4)
    assert int((rebuilt["median_distance"] > 0).sum()) == 119_837
    assert int((rebuilt["count_wednesdays"] > 0).sum()) == 120_483
    assert rebuilt["count_wednesdays"].max() == 41


def test_distance_uses_41_days_and_counts_42(rebuilt, paper):
    """H3, D4: los conteos se calculan sobre 42 miércoles y la distancia sobre 41."""
    counts = pd.read_csv(
        config.PACKAGE_DIR / "00_data" / "hexagon_model_median_wednesdays_RM.csv",
        usecols=["count_wednesdays"],
    )
    assert counts["count_wednesdays"].max() == 42
    assert paper["count_wednesdays"].max() == 41


def test_hexagons_outside_the_grid_are_dropped(daily_metrics, panel):
    """H14: hay hexágonos con tránsito fuera de la grilla de 11.144; se descartan."""
    outside = count_outside_grid(daily_metrics, panel[["hex", "hour"]])
    assert outside > 5_000
    assert daily_metrics["hex"].nunique() - outside < panel["hex"].nunique()


def test_absent_days_as_zero_changes_most_rows_and_only_lowers(daily_metrics, panel, rebuilt):
    """Contar los días sin tránsito como 0 cambia ~59 % de las filas (solo a la baja)."""
    other = median_distance(daily_metrics, panel[["hex", "hour"]], include_absent_days=True)
    share = float((~np.isclose(rebuilt["median_distance"], other["median_distance"])).mean())
    assert 0.5 < share < 0.7
    assert (other["median_distance"] <= rebuilt["median_distance"] + 1e-9).all()
    assert (other["count_wednesdays"] == rebuilt["count_wednesdays"]).all()


def test_legacy_data_base_distance_is_the_median_of_the_first_two_wednesdays(
    daily_metrics, panel, legacy_data_base
):
    """H26: el `data_base` de distancia del paquete anterior (residuo de prueba de los autores)
    es exactamente la mediana de los dos primeros miércoles (2024-01-03 y 2024-01-10)."""
    first_two = sorted(daily_metrics["date"].unique())[:2]
    assert [str(d.date()) for d in first_two] == ["2024-01-03", "2024-01-10"]
    two = median_distance(
        daily_metrics[daily_metrics["date"].isin(first_two)], panel[["hex", "hour"]]
    )
    legacy = pd.read_csv(
        legacy_data_base / "hexagon_model_median_wednesday_alternative_metrics_RM.csv",
        usecols=["hex", "hour", *COLUMNS],
    )
    merged = two.merge(legacy, on=["hex", "hour"], suffixes=("_rebuilt", "_legacy"))
    assert len(merged) == config.N_HEXAGON_HOURS
    for column in COLUMNS:
        assert np.allclose(
            merged[f"{column}_rebuilt"], merged[f"{column}_legacy"], rtol=0, atol=1e-6
        )
    assert legacy["count_wednesdays"].max() == 2
