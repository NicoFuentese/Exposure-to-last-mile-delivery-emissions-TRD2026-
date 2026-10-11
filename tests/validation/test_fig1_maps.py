"""Fig. 1 con los datos reales: valores de los mapas, escalas y cobertura (AGENTS.md H35).

Requiere los datos confidenciales (se salta sin ellos). Los valores se recalculan con pandas,
por un camino independiente de `group_masses`, y se fijan las cifras documentadas.

Lo que se compara con el paper son las puntas de las escalas de color de la Fig. 1: 1600 (SEG AB)
y 7000 (SEG C1b), las mismas en la mañana y en la tarde. Nuestros máximos son compatibles pero NO
idénticos (1.511 y 7.073); la causa no se conoce (H35), así que las pruebas fijan lo medido y la
distancia al paper, sin forzarla.
"""

import numpy as np
import pytest

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import group_masses
from lastmile_exposure.figures.maps import fig1_data

SHARE_COLUMN = {"AB": "gse_ab", "C1b": "gse_c1b"}
PAPER_SCALE_END = {"AB": 1600.0, "C1b": 7000.0}  # lo que imprime la Fig. 1 del paper (p.6)


@pytest.fixture(scope="module")
def masses(panel):
    return group_masses(panel)


@pytest.fixture(scope="module")
def data(masses):
    return fig1_data(masses)


def _window_mean(panel, label, hours):
    """Media de las horas de la ventana de población × share, por hexágono (pandas puro)."""
    window = panel[panel["hour"].isin(hours)]
    mass = window["poblacion_flotante"] * window[SHARE_COLUMN[label]]
    return mass.groupby(window["hex"]).sum() / len(hours)


@pytest.mark.parametrize("label", ["AB", "C1b"])
@pytest.mark.parametrize(
    ("window", "hours"), [("morning", config.MORNING_HOURS), ("evening", config.EVENING_HOURS)]
)
def test_map_values_equal_an_independent_pandas_computation(panel, data, label, window, hours):
    expected = _window_mean(panel, label, hours).reindex(data["hexes"])
    assert not expected.isna().any()
    assert data["values"][(label, window)] == pytest.approx(expected.to_numpy(), rel=1e-10)


def test_windows_are_the_authors_inclusive_hours():
    assert config.MORNING_HOURS == (10, 11, 12) and config.EVENING_HOURS == (20, 21, 22)


def test_documented_maxima_of_the_four_maps(data):
    """Máximos medidos (hexágonos dentro de los límites): fijan lo que muestra la figura."""
    values = data["values"]
    assert values[("AB", "morning")].max() == pytest.approx(1511.3, abs=0.05)
    assert values[("AB", "evening")].max() == pytest.approx(1163.6, abs=0.05)
    assert values[("C1b", "morning")].max() == pytest.approx(5090.9, abs=0.05)
    assert values[("C1b", "evening")].max() == pytest.approx(7073.2, abs=0.05)
    assert data["vmax"]["AB"] == pytest.approx(1511.3, abs=0.05)  # el máximo es el de la mañana
    assert data["vmax"]["C1b"] == pytest.approx(7073.2, abs=0.05)  # y el de C1b, el de la tarde


def test_scale_ends_are_compatible_with_but_not_identical_to_the_papers(data):
    """H35: AB queda 5,5 % bajo el 1600 del paper y C1b 1,0 % sobre su 7000."""
    for label, paper_end in PAPER_SCALE_END.items():
        ratio = data["vmax"][label] / paper_end
        assert 0.90 < ratio < 1.05, (label, ratio)
    assert data["vmax"]["AB"] / 1600 == pytest.approx(0.944, abs=0.002)
    assert data["vmax"]["C1b"] / 7000 == pytest.approx(1.010, abs=0.002)


def test_hexagons_inside_the_maps_limits(masses, data):
    """El script de los autores filtra por centroide: 9.081 de los 11.144 hexágonos."""
    assert len(masses.hexes) == config.N_HEXAGONS
    assert len(data["hexes"]) == 9_081
    assert data["vertices"].shape == (9_081, 6, 2)


def test_ab_population_lies_north_east_of_c1b_in_both_windows(masses):
    """El patrón que describe el paper: AB en el nororiente, C1b más al centro (Fig. 1)."""
    latlon = np.degrees(masses.latlon)
    labels = list(masses.labels)

    def centroid(label, window):
        mass = np.asarray(getattr(masses, window)[labels.index(label)])
        return (latlon * mass[:, None]).sum(axis=0) / mass.sum()  # (lat, lon)

    for window in ("morning", "evening"):
        ab_lat, ab_lon = centroid("AB", window)
        c1b_lat, c1b_lon = centroid("C1b", window)
        assert ab_lat > c1b_lat and ab_lon > c1b_lon, window  # más al norte y más al este
