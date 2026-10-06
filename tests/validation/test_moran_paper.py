"""I de Moran sobre los datos reales frente a las cifras del paper (AGENTS.md H28, D8).

Requiere los datos confidenciales (se salta sin ellos). El paper no especifica la matriz de pesos
ni cómo promedia el tiempo: estas pruebas FIJAN los resultados de la lista cerrada de lecturas
directas (anillo 1 de H3, pesos W/B, 3 agregaciones) tal como salen. La lectura principal (promedio
de las 16 I horarias con pesos W) NO reproduce; ninguna combinación es exacta; las que se acercan
(≤ 2 %) están rotuladas "aproximado" y eso NO identifica la especificación.
"""

import numpy as np
import pytest

from lastmile_exposure import config
from lastmile_exposure.inference.moran import (
    h3_ring1_weights,
    morans_i_grid,
    n_islands,
    wide_by_hour,
)
from lastmile_exposure.io.panel import load_counts_dataset, load_distance_dataset
from lastmile_exposure.validation.paper_tables import load_paper_scalars, moran_agreement

# (estilo, agregación) -> (distancia, vehículos): valores tal como salen, no son del paper
DOCUMENTED = {
    ("W", "mean_of_hourly"): (0.4190, 0.4297),  # lectura literal (principal)
    ("B", "mean_of_hourly"): (0.4269, 0.4400),
    ("W", "mean_map"): (0.4656, 0.4702),
    ("B", "mean_map"): (0.4725, 0.4792),
    ("W", "stacked"): (0.4620, 0.4660),
    ("B", "stacked"): (0.4726, 0.4774),
}


@pytest.fixture(scope="module")
def grid(panel):
    distance, counts = load_distance_dataset(), load_counts_dataset()
    hexes = np.array(sorted(distance["hex"].unique()))
    wides = {
        "distancia": wide_by_hour(distance, "median_distance", hexes),
        "vehiculos": wide_by_hour(counts, "median_vehicles", hexes),
    }
    return morans_i_grid(wides, hexes).set_index(["estilo", "agregacion"]), hexes


def test_h3_grid_structure(grid):
    """La grilla de 11.144 hexágonos tiene 15 islas con vecindad de anillo 1 y ~5,5 vecinos."""
    _, hexes = grid
    w = h3_ring1_weights(hexes, style="B")
    assert len(hexes) == config.N_HEXAGONS
    assert n_islands(w) == 15
    degree = np.asarray(w.sum(axis=1)).ravel()
    assert degree.mean() == pytest.approx(5.51, abs=0.01) and degree.max() == 6


def test_documented_values_are_pinned(grid):
    table, _ = grid
    for key, (distance, vehicles) in DOCUMENTED.items():
        assert table.loc[key, "distancia"] == pytest.approx(distance, abs=6e-4), key
        assert table.loc[key, "vehiculos"] == pytest.approx(vehicles, abs=6e-4), key


def test_the_principal_reading_does_not_reproduce_the_paper(grid):
    """La lectura literal queda ~0,05 por debajo: no se presenta como reproducida."""
    table, _ = grid
    scalars = load_paper_scalars()
    principal = table[table["principal"]]
    assert list(principal.index) == [("W", "mean_of_hourly")]
    row = principal.iloc[0]
    assert moran_agreement(row["distancia"], scalars["moran_i_distance"]) == "no reproduce"
    assert moran_agreement(row["vehiculos"], scalars["moran_i_vehicles"]) == "no reproduce"
    assert scalars["moran_i_distance"] - row["distancia"] > 0.04


def test_no_combination_is_exact_and_approximate_does_not_mean_identified(grid):
    """Ninguna de las 6 lecturas coincide en el cuarto decimal; algunas solo se acercan."""
    table, _ = grid
    scalars = load_paper_scalars()
    labels = {
        key: (
            moran_agreement(row["distancia"], scalars["moran_i_distance"]),
            moran_agreement(row["vehiculos"], scalars["moran_i_vehicles"]),
        )
        for key, row in table.iterrows()
    }
    assert all("exacto" not in pair for pair in labels.values())
    assert labels[("W", "mean_map")] == ("aproximado", "aproximado")
    assert labels[("B", "mean_map")] == ("aproximado", "aproximado")
    assert labels[("W", "stacked")] == ("aproximado", "no reproduce")  # 2,0 %: justo fuera
    assert labels[("W", "mean_of_hourly")] == ("no reproduce", "no reproduce")
    assert labels[("B", "mean_of_hourly")] == ("no reproduce", "no reproduce")


def test_strong_positive_spatial_correlation_in_every_reading(grid):
    """Lo cualitativo que sí se sostiene: I mucho mayor que E[I] ≈ 0 en todas las lecturas."""
    table, _ = grid
    assert (table[["distancia", "vehiculos"]] > 0.4).all().all()


@pytest.mark.parametrize("style", ["W", "B"])
def test_one_real_hour_matches_esda(grid, style):
    """Contraste independiente con `esda` + `libpysal` sobre la hora 12 de la distancia real."""
    from esda.moran import Moran
    from libpysal.weights import W as PysalW

    _, hexes = grid
    distance = load_distance_dataset()
    x = wide_by_hour(distance, "median_distance", hexes)[12].to_numpy(dtype=float)
    binary = h3_ring1_weights(hexes, style="B")
    neighbors = {i: list(binary[i].indices) for i in range(len(hexes))}
    weights = {i: [1.0] * len(js) for i, js in neighbors.items()}
    pysal = PysalW(neighbors, weights, silence_warnings=True)
    transformation = "r" if style == "W" else "b"  # nombres de libpysal
    reference = Moran(x, pysal, transformation=transformation, permutations=0).I
    ours = morans_i_grid({"d": wide_by_hour(distance, "median_distance", hexes)[[12]]}, hexes)
    value = ours.set_index(["estilo", "agregacion"]).loc[(style, "mean_of_hourly"), "d"]
    assert value == pytest.approx(reference, rel=1e-9)
