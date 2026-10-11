"""Sustituto de la Fig. 2 con los datos reales: vehículos por hexágono (NO son puntos GPS).

Requiere los datos confidenciales (se salta sin ellos). La Fig. 2 del paper («GPS Points per
Hexagon») necesita el GPS crudo de todos los días y no se puede reproducir; esto es lo más cercano
con los datos del paquete: la mediana de vehículos de la base del paper, promediada en las horas
7-22.
"""

import h3
import numpy as np
import pytest

from lastmile_exposure import config
from lastmile_exposure.figures.maps import in_bounds, log_colorbar_ticks, vehicle_means
from lastmile_exposure.io.panel import load_counts_dataset


@pytest.fixture(scope="module")
def means(panel):  # `panel` solo asegura que los datos existen (se salta si no)
    return vehicle_means(load_counts_dataset())


def test_means_equal_an_independent_pandas_computation(means):
    counts = load_counts_dataset()
    window = counts[counts["hour"].between(7, 22)]
    expected = window.groupby("hex")["median_vehicles"].sum() / len(config.HOURS)
    assert len(means) == config.N_HEXAGONS
    assert means.set_index("hex")["mean_vehicles"].reindex(expected.index).to_numpy() == (
        pytest.approx(expected.to_numpy(), rel=1e-12)
    )


def test_documented_figures_of_the_proxy(means):
    """Cifras medidas (hexágonos dentro de los límites del mapa) que fijan lo que muestra."""
    latlon = np.radians([h3.cell_to_latlng(cell) for cell in means["hex"]])
    keep = in_bounds(latlon)
    values = means["mean_vehicles"].to_numpy()[keep]
    assert int(keep.sum()) == 9_081  # los mismos hexágonos que en la Fig. 1
    assert values.max() == pytest.approx(47.1562, abs=5e-4)
    assert values.mean() == pytest.approx(2.644, abs=5e-4)
    assert (values == 0).mean() * 100 == pytest.approx(6.24, abs=0.01)
    _, labels = log_colorbar_ticks(float(np.log1p(values.max())))
    assert labels == ["0", "3", "12", "47"]
