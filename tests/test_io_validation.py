"""`validate_grid` rechaza datos que no son la grilla completa del paper (sin datos reales)."""

import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.io.panel import validate_grid


def _grid(n_hex=config.N_HEXAGONS):
    hexes = [f"h{i}" for i in range(n_hex)]
    return pd.DataFrame(
        [(h, hour) for h in hexes for hour in config.HOURS], columns=["hex", "hour"]
    )


def test_full_grid_passes_and_is_returned():
    df = _grid()
    assert validate_grid(df) is df


def test_wrong_number_of_rows_is_rejected():
    with pytest.raises(ValueError, match="filas"):
        validate_grid(_grid().iloc[:-1])


def test_wrong_number_of_hexagons_is_rejected():
    df = _grid()
    df.loc[df["hex"] == "h0", "hex"] = "h1"  # mismas filas, un hexágono menos
    with pytest.raises(ValueError):
        validate_grid(df)


def test_wrong_hours_are_rejected():
    df = _grid()
    df["hour"] = df["hour"] - 1  # 6..21 en lugar de 7..22
    with pytest.raises(ValueError, match="horas"):
        validate_grid(df)
