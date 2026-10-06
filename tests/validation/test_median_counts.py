"""La mediana de conteos reconstruida desde los archivos diarios coincide con la del paper (H2).

Requiere los datos confidenciales (se salta sin ellos). Lee 42 CSV una sola vez por sesión.
"""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.exposure.vehicles_counts import count_outside_grid, median_vehicles
from lastmile_exposure.io.daily_counts import load_daily_counts
from lastmile_exposure.io.panel import load_counts_dataset


@pytest.fixture(scope="module")
def paper():
    return load_counts_dataset()[["hex", "hour", "median_vehicles", "count_wednesdays"]]


@pytest.fixture(scope="module")
def rebuilt(daily_counts, panel):
    return median_vehicles(daily_counts, panel[["hex", "hour"]])


def test_daily_files_are_42_wednesdays_in_utc(daily_counts):
    """H3: 42 miércoles (incluye el 2024-05-01, feriado), sin julio ni diciembre."""
    dates = daily_counts["date"].drop_duplicates()
    assert len(dates) == 42
    assert (dates.dt.dayofweek == 2).all()
    assert pd.Timestamp("2024-05-01") in set(dates)
    assert not dates.dt.month.isin([7, 12]).any()
    assert set(daily_counts["hour"]) == set(config.HOURS)


def test_rebuilt_median_is_identical_to_the_papers(rebuilt, paper):
    """Réplica fiel: igualdad exacta de `median_vehicles` y `count_wednesdays` (178.304 filas)."""
    merged = rebuilt.merge(paper, on=["hex", "hour"], suffixes=("_rebuilt", "_paper"))
    assert len(merged) == config.N_HEXAGON_HOURS
    assert (merged["median_vehicles_rebuilt"] == merged["median_vehicles_paper"]).all()
    assert (merged["count_wednesdays_rebuilt"] == merged["count_wednesdays_paper"]).all()


def test_rebuilt_summary_statistics(rebuilt):
    assert (rebuilt["median_vehicles"] == 0).mean() == pytest.approx(0.2956, abs=5e-4)
    assert int((rebuilt["median_vehicles"] % 1 == 0.5).sum()) == 5_810  # medianas x,5
    assert rebuilt["count_wednesdays"].max() == 42


def test_hexagons_outside_the_grid_are_dropped(daily_counts, panel):
    """H14: muchos hexágonos con vehículos quedan fuera de la grilla de 11.144 y se descartan."""
    outside = count_outside_grid(daily_counts, panel[["hex", "hour"]])
    inside = daily_counts["hex"].nunique() - outside
    assert outside > 5_000
    assert 8_000 < inside < panel["hex"].nunique()  # y hay hexágonos de la grilla sin vehículos


def test_absent_days_as_zero_changes_a_large_share_of_rows(daily_counts, panel, rebuilt):
    """H2: contar los días ausentes como 0 cambia ~41 % de las filas respecto del paquete."""
    other = median_vehicles(daily_counts, panel[["hex", "hour"]], include_absent_days=True)
    share = float((~np.isclose(rebuilt["median_vehicles"], other["median_vehicles"])).mean())
    assert 0.30 < share < 0.50
    assert (other["median_vehicles"] <= rebuilt["median_vehicles"]).all()  # solo baja
    assert (other["count_wednesdays"] == rebuilt["count_wednesdays"]).all()


def test_excluding_the_holiday_gives_41_wednesdays(panel, rebuilt):
    """D4: sin el 2024-05-01 quedan 41 miércoles, como el paper."""
    daily_41 = load_daily_counts(exclude_dates=("2024-05-01",))
    assert daily_41["date"].nunique() == 41
    out = median_vehicles(daily_41, panel[["hex", "hour"]])
    assert out["count_wednesdays"].max() <= 41
    assert not np.array_equal(out["median_vehicles"], rebuilt["median_vehicles"])


def test_data_base_counts_are_the_median_of_the_first_two_wednesdays(daily_counts, panel):
    """H26: `00_out/data_base` (la copia que leen por defecto los scripts de los autores) NO es la
    base del paper: su `median_vehicles` es exactamente la mediana de los dos primeros miércoles
    (2024-01-03 y 2024-01-10) de los conteos diarios."""
    path = config.PACKAGE_DIR / "00_out" / "data_base" / "hexagon_model_median_wednesdays_RM.csv"
    data_base = pd.read_csv(path, usecols=["hex", "hour", "median_vehicles", "count_wednesdays"])
    first_two = sorted(daily_counts["date"].unique())[:2]
    assert [str(d.date()) for d in first_two] == ["2024-01-03", "2024-01-10"]
    rebuilt = median_vehicles(
        daily_counts[daily_counts["date"].isin(first_two)], panel[["hex", "hour"]]
    )
    merged = rebuilt.merge(data_base, on=["hex", "hour"], suffixes=("_rebuilt", "_data_base"))
    assert len(merged) == config.N_HEXAGON_HOURS
    assert (merged["median_vehicles_rebuilt"] == merged["median_vehicles_data_base"]).all()
    assert (merged["count_wednesdays_rebuilt"] == merged["count_wednesdays_data_base"]).all()
    assert data_base["count_wednesdays"].max() == 2
