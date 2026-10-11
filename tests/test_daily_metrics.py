"""Lector de métricas diarias y mediana de distancia con datos sintéticos (sin datos reales).

Fechas usadas (todas de 2024): 03-01, 10-01 y 17-01 son miércoles; 04-01 es jueves.
"""

import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.exposure.vehicles_distance import median_distance, median_over_days
from lastmile_exposure.io.daily_metrics import load_daily_metrics


def _write(folder, date, rows):
    frame = pd.DataFrame(rows, columns=["hex", "hour", "total_distance_m", "total_time_sec"])
    frame.to_csv(folder / f"{date}_metrics.csv", index=False)


@pytest.fixture
def folder(tmp_path):
    # hexágono A: tránsito los tres días (distancias 10, 20, 30); B: un solo día (100)
    _write(tmp_path, "03-01-2024", [("A", 7, 10, 1), ("B", 7, 100, 50), ("A", 3, 5, 5)])
    _write(tmp_path, "10-01-2024", [("A", 7, 20, 2)])
    _write(tmp_path, "17-01-2024", [("A", 7, 30, 3)])
    return tmp_path


def test_loader_reads_all_files_and_filters_hours(folder):
    daily = load_daily_metrics(folder)
    assert list(daily.columns) == ["hex", "hour", "date", "total_distance_m", "total_time_sec"]
    assert daily["date"].nunique() == 3
    assert set(daily["hour"]) == {7}  # la hora 3 no está en la grilla (7-22)
    assert set(load_daily_metrics(folder, hours=None)["hour"]) == {3, 7}


def test_loader_can_exclude_dates(folder):
    daily = load_daily_metrics(folder, exclude_dates=("2024-01-17",))
    assert daily["date"].nunique() == 2


def test_loader_rejects_non_wednesdays(tmp_path):
    _write(tmp_path, "04-01-2024", [("A", 7, 10, 1)])  # jueves
    with pytest.raises(ValueError, match="no es miércoles"):
        load_daily_metrics(tmp_path)


def test_loader_rejects_duplicates_negatives_and_missing(tmp_path):
    _write(tmp_path, "03-01-2024", [("A", 7, 10, 1), ("A", 7, 20, 2)])
    with pytest.raises(ValueError, match="repetidos"):
        load_daily_metrics(tmp_path)
    _write(tmp_path, "03-01-2024", [("A", 7, -1, 1)])
    with pytest.raises(ValueError, match="negativa"):
        load_daily_metrics(tmp_path)
    _write(tmp_path, "03-01-2024", [("A", 7, float("nan"), 1)])
    with pytest.raises(ValueError, match="finita"):
        load_daily_metrics(tmp_path)
    pd.DataFrame({"hex": ["A"], "hour": [7]}).to_csv(tmp_path / "03-01-2024_metrics.csv")
    with pytest.raises(ValueError, match="faltan las columnas"):
        load_daily_metrics(tmp_path)


def test_loader_without_files_fails(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_daily_metrics(tmp_path)


def test_median_uses_only_the_days_with_data(folder):
    """Réplica: la mediana de A es la de 10, 20, 30; B queda con su único día (H2, H30)."""
    out = median_over_days(load_daily_metrics(folder)).set_index("hex")
    assert out.loc["A", ["median_distance", "median_time", "count_wednesdays"]].tolist() == [
        20,
        2,
        3,
    ]
    assert out.loc["B", ["median_distance", "median_time", "count_wednesdays"]].tolist() == [
        100,
        50,
        1,
    ]


def test_absent_days_as_zero_lowers_the_median_but_not_the_count(folder):
    out = median_over_days(load_daily_metrics(folder), include_absent_days=True).set_index("hex")
    assert out.loc["A", "median_distance"] == 20  # presente los tres días: no cambia
    assert out.loc["B", "median_distance"] == 0  # [100, 0, 0]
    assert out.loc["B", "median_time"] == 0
    assert out.loc["B", "count_wednesdays"] == 1  # el conteo sigue siendo el de días con dato


def test_grid_merge_fills_zeros_keeps_order_and_drops_hexagons_outside(folder):
    grid = pd.DataFrame({"hex": ["Z", "B", "A"], "hour": [7, 7, 7]})  # Z sin datos
    out = median_distance(load_daily_metrics(folder), grid)
    assert list(out["hex"]) == ["Z", "B", "A"]
    assert out["median_distance"].tolist() == [0.0, 100.0, 20.0]
    assert out["count_wednesdays"].tolist() == [0, 1, 3]
    assert out["count_wednesdays"].dtype.kind == "i"
    assert len(out) == len(grid)  # ninguna fila extra aunque haya hexágonos fuera de la grilla


def test_result_columns_follow_the_published_dataset(folder):
    grid = pd.DataFrame({"hex": ["A"], "hour": [7]})
    out = median_distance(load_daily_metrics(folder), grid)
    assert list(out.columns) == [
        "hex",
        "hour",
        "median_distance",
        "median_time",
        "count_wednesdays",
    ]
    assert config.OUTCOME_DISTANCE == "median_distance"
