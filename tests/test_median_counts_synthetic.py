"""Mediana de conteos con datos sintéticos (no necesitan los datos confidenciales).

Cubre la lectura de los archivos diarios (con carpetas temporales) y las dos formas de agregar
entre días: sobre los días presentes (código de los autores) y con los ausentes como 0.
"""

from pathlib import Path

import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.exposure.aggregate import median_over_days
from lastmile_exposure.exposure.vehicles_counts import count_outside_grid, median_vehicles
from lastmile_exposure.io.daily_counts import date_from_filename, load_daily_counts

# Tres miércoles de 2024 (el 2024-05-01 es feriado) y uno que NO es miércoles
WED = ["03-01-2024", "10-01-2024", "17-01-2024"]


def _write_day(folder, name, rows):
    df = pd.DataFrame(rows, columns=["hex", "hour", "vehicles"])
    df.to_csv(folder / f"hexagon_count_{name}_cleaned.csv", index=False)


def _daily(rows_by_day):
    """Marco largo como el de `load_daily_counts`; `rows_by_day` = {fecha ISO: [(hex, hour, n)]}."""
    frames = []
    for iso, rows in rows_by_day.items():
        df = pd.DataFrame(rows, columns=["hex", "hour", "vehicles"])
        frames.append(df.assign(date=pd.Timestamp(iso)))
    return pd.concat(frames, ignore_index=True)[["hex", "hour", "date", "vehicles"]]


# ---------------------------------------------------------------- lectura
def test_date_from_filename_is_day_month_year():
    assert date_from_filename(Path("hexagon_count_01-05-2024_cleaned.csv")) == pd.Timestamp(
        "2024-05-01"
    )
    with pytest.raises(ValueError, match="fecha"):
        date_from_filename(Path("hexagon_count_sin_fecha.csv"))


def test_load_filters_hours_and_adds_the_utc_date(tmp_path):
    _write_day(tmp_path, WED[0], [("h1", 3, 5), ("h1", 7, 2), ("h2", 22, 1), ("h2", 23, 9)])
    daily = load_daily_counts(tmp_path)
    assert list(daily.columns) == ["hex", "hour", "date", "vehicles"]
    assert sorted(daily["hour"]) == [7, 22]  # solo 7..22
    assert set(daily["date"]) == {pd.Timestamp("2024-01-03")}
    assert len(load_daily_counts(tmp_path, hours=None)) == 4  # todas las horas


def test_exclude_dates_drops_that_wednesday(tmp_path):
    for name in WED[:2]:
        _write_day(tmp_path, name, [("h1", 8, 1)])
    daily = load_daily_counts(tmp_path, exclude_dates=("2024-01-10",))
    assert set(daily["date"]) == {pd.Timestamp("2024-01-03")}


def test_rejects_non_wednesday_duplicates_and_empty_folders(tmp_path):
    _write_day(tmp_path, "04-01-2024", [("h1", 8, 1)])  # jueves
    with pytest.raises(ValueError, match="no es miércoles"):
        load_daily_counts(tmp_path)
    (tmp_path / "hexagon_count_04-01-2024_cleaned.csv").unlink()
    _write_day(tmp_path, WED[0], [("h1", 8, 1), ("h1", 8, 2)])  # (hex, hour) repetido
    with pytest.raises(ValueError, match="repetidos"):
        load_daily_counts(tmp_path)
    (tmp_path / f"hexagon_count_{WED[0]}_cleaned.csv").unlink()
    with pytest.raises(FileNotFoundError):
        load_daily_counts(tmp_path)


# ---------------------------------------------------------------- agregación
def test_present_days_vs_absent_days_as_zero():
    """3 miércoles: h1 con 4 y 2 (un día ausente), h2 con un solo día, h3 en los tres días."""
    daily = _daily(
        {
            "2024-01-03": [("h1", 8, 4), ("h2", 8, 5), ("h3", 8, 1)],
            "2024-01-10": [("h1", 8, 2), ("h3", 8, 2)],
            "2024-01-17": [("h3", 8, 3)],
        }
    )
    authors = median_over_days(daily).set_index("hex")
    assert authors.loc["h1", "median_vehicles"] == 3.0  # mediana de [2, 4]
    assert authors.loc["h2", "median_vehicles"] == 5.0  # un solo día: queda esa cifra (H2)
    assert authors.loc["h3", "median_vehicles"] == 2.0
    assert authors["count_wednesdays"].to_dict() == {"h1": 2, "h2": 1, "h3": 3}

    paper_text = median_over_days(daily, include_absent_days=True).set_index("hex")
    assert paper_text.loc["h1", "median_vehicles"] == 2.0  # mediana de [0, 2, 4]
    assert paper_text.loc["h2", "median_vehicles"] == 0.0  # [0, 0, 5]
    assert paper_text.loc["h3", "median_vehicles"] == 2.0
    # count_wednesdays es siempre el nº de días con vehículos
    assert paper_text["count_wednesdays"].to_dict() == {"h1": 2, "h2": 1, "h3": 3}


def test_even_number_of_days_gives_half_integers():
    daily = _daily(
        {
            "2024-01-03": [("h1", 8, 1)],
            "2024-01-10": [("h1", 8, 2)],
            "2024-01-17": [("h1", 8, 3), ("h2", 8, 1)],
            "2024-01-24": [("h2", 8, 1)],  # cuarto día: h1 ausente en él
        }
    )
    authors = median_over_days(daily).set_index("hex")["median_vehicles"]
    assert authors["h1"] == 2.0  # [1, 2, 3]
    paper_text = median_over_days(daily, include_absent_days=True).set_index("hex")
    assert paper_text.loc["h1", "median_vehicles"] == 1.5  # [0, 1, 2, 3]
    assert paper_text.loc["h2", "median_vehicles"] == 0.5  # [0, 0, 1, 1]


def test_hours_are_aggregated_independently():
    daily = _daily({"2024-01-03": [("h1", 8, 4), ("h1", 9, 7)], "2024-01-10": [("h1", 8, 2)]})
    out = median_over_days(daily).set_index(["hex", "hour"])["median_vehicles"]
    assert out.loc[("h1", 8)] == 3.0 and out.loc[("h1", 9)] == 7.0


# ---------------------------------------------------------------- grilla
def test_median_vehicles_covers_the_grid_fills_zero_and_drops_outside_hexes():
    daily = _daily({"2024-01-03": [("h1", 8, 4), ("fuera", 8, 9)], "2024-01-10": [("h1", 8, 2)]})
    grid = pd.DataFrame({"hex": ["h2", "h1", "h1"], "hour": [8, 9, 8]})  # orden propio
    out = median_vehicles(daily, grid)
    assert out[["hex", "hour"]].values.tolist() == grid.values.tolist()  # mismo orden y filas
    assert out["median_vehicles"].tolist() == [0.0, 0.0, 3.0]
    assert out["count_wednesdays"].tolist() == [0, 0, 2]
    assert "fuera" not in set(out["hex"])
    assert count_outside_grid(daily, grid) == 1


def test_grid_constants_used_by_the_loader():
    assert config.HOURS == tuple(range(7, 23))
