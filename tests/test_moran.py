"""I de Moran con datos sintéticos (no necesitan los datos confidenciales).

Se contrasta con cálculos a mano, identidades exactas y con `esda` + `libpysal` (implementación
independiente, ya fijada en `requirements.txt`).
"""

import h3
import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp
from esda.moran import Moran
from libpysal.weights import W as PysalW

from lastmile_exposure.inference.moran import (
    AGGREGATIONS,
    aggregate_morans_i,
    expected_i,
    h3_ring1_weights,
    hourly_morans_i,
    morans_i,
    morans_i_grid,
    n_islands,
    row_standardize,
    wide_by_hour,
)
from lastmile_exposure.validation.paper_tables import moran_agreement


def _path(n):
    """Grafo en camino de n nodos (matriz binaria)."""
    w = sp.lil_matrix((n, n))
    for i in range(n - 1):
        w[i, i + 1] = w[i + 1, i] = 1.0
    return w.tocsr()


def _cycle(n):
    w = sp.lil_matrix((n, n))
    for i in range(n):
        w[i, (i + 1) % n] = w[(i + 1) % n, i] = 1.0
    return w.tocsr()


# ------------------------------------------------------------------ fórmula
def test_hand_computed_path_graph():
    """Camino de 4 nodos con x = 1,2,3,4: I = 1/3 (binaria) y 0,4 (filas estandarizadas)."""
    x = np.array([1.0, 2.0, 3.0, 4.0])
    assert morans_i(x, _path(4)) == pytest.approx(1 / 3)
    assert morans_i(x, row_standardize(_path(4))) == pytest.approx(0.4)


def test_alternating_values_on_a_bipartite_cycle_give_minus_one():
    x = np.array([1.0, -1.0] * 3)
    assert morans_i(x, row_standardize(_cycle(6))) == pytest.approx(-1.0)


def test_smooth_values_give_a_strongly_positive_i_and_noise_gives_about_the_expected_value():
    n = 2_000
    w = row_standardize(_cycle(n))
    smooth = np.sin(np.linspace(0, 4 * np.pi, n))
    assert morans_i(smooth, w) > 0.99
    noise = np.random.default_rng(0).normal(size=n)
    assert abs(morans_i(noise, w) - expected_i(n)) < 0.08
    assert expected_i(11_144) == pytest.approx(-1 / 11_143)


def test_invariant_to_shift_and_scale():
    x = np.random.default_rng(1).normal(size=50)
    w = row_standardize(_cycle(50))
    assert morans_i(3.0 * x + 10.0, w) == pytest.approx(morans_i(x, w))


def test_input_validation():
    w = _path(4)
    with pytest.raises(ValueError, match="constante"):
        morans_i(np.ones(4), w)
    with pytest.raises(ValueError, match="n × n"):
        morans_i(np.arange(3.0), w)
    with pytest.raises(ValueError, match="ningún peso"):
        morans_i(np.arange(4.0), sp.csr_matrix((4, 4)))


# ------------------------------------------------------------------ contraste independiente
def _random_graph(n, seed, islands=0):
    rng = np.random.default_rng(seed)
    upper = np.triu(rng.random((n, n)) < 0.15, 1)
    adj = (upper | upper.T).astype(float)
    if islands:
        adj[-islands:, :] = 0.0
        adj[:, -islands:] = 0.0
    return sp.csr_matrix(adj)


@pytest.mark.parametrize("islands", [0, 2])
@pytest.mark.parametrize("style", ["B", "W"])
def test_matches_esda_on_random_graphs_with_and_without_islands(style, islands):
    n = 60
    binary = _random_graph(n, seed=3, islands=islands)
    x = np.random.default_rng(4).normal(size=n)
    neighbors = {i: list(binary[i].indices) for i in range(n)}
    weights = {i: [1.0] * len(js) for i, js in neighbors.items()}
    pysal = PysalW(neighbors, weights, silence_warnings=True)
    # OJO: `Moran` aplica su propio `transformation` (por defecto "r") sobre el objeto W
    reference = Moran(x, pysal, transformation="r" if style == "W" else "b", permutations=0).I
    ours = morans_i(x, row_standardize(binary) if style == "W" else binary)
    assert ours == pytest.approx(reference, rel=1e-10)
    assert n_islands(binary) == islands


# ------------------------------------------------------------------ pesos de H3
def test_h3_ring1_weights_on_a_complete_disk():
    center = h3.latlng_to_cell(-33.45, -70.66, 9)
    cells = sorted(h3.grid_disk(center, 3))  # 37 celdas
    b = h3_ring1_weights(cells, style="B")
    w = h3_ring1_weights(cells, style="W")
    degree = np.asarray(b.sum(axis=1)).ravel()
    assert b.shape == (37, 37) and (b != b.T).nnz == 0  # simétrica
    assert degree[cells.index(center)] == 6  # un hexágono interior tiene 6 vecinos
    assert degree.min() == 3 and degree.max() == 6  # los del borde tienen menos
    assert np.asarray(w.sum(axis=1)).ravel() == pytest.approx(1.0)
    assert n_islands(b) == 0


def test_h3_islands_keep_a_zero_row():
    center = h3.latlng_to_cell(-33.45, -70.66, 9)
    far = h3.latlng_to_cell(-33.30, -70.50, 9)
    cells = [*sorted(h3.grid_ring(center, 1)), center, far]
    w = h3_ring1_weights(cells, style="W")
    assert n_islands(w) == 1
    assert w[cells.index(far)].sum() == 0.0


def test_h3_weights_validation():
    center = h3.latlng_to_cell(-33.45, -70.66, 9)
    with pytest.raises(ValueError, match="style"):
        h3_ring1_weights([center], style="otro")
    with pytest.raises(ValueError, match="repetidas"):
        h3_ring1_weights([center, center])


# ------------------------------------------------------------------ agregaciones
def _hex_hour_wide(hours=4, seed=7):
    center = h3.latlng_to_cell(-33.45, -70.66, 9)
    cells = sorted(h3.grid_disk(center, 4))
    rng = np.random.default_rng(seed)
    base = rng.normal(size=len(cells))
    wide = pd.DataFrame(
        {h: base + rng.normal(0, 0.5 + 0.5 * h, len(cells)) for h in range(hours)}, index=cells
    )
    return cells, wide


def test_aggregations_follow_their_definitions():
    cells, wide = _hex_hour_wide()
    w = h3_ring1_weights(cells, style="W")
    hourly = hourly_morans_i(wide, w)
    assert len(hourly) == 4
    assert aggregate_morans_i(wide, w, "mean_of_hourly") == pytest.approx(hourly.mean())
    assert aggregate_morans_i(wide, w, "mean_map") == pytest.approx(
        morans_i(wide.to_numpy().mean(axis=1), w)
    )
    variances = ((wide - wide.mean()) ** 2).sum()  # el apilado pondera por la varianza de la hora
    assert aggregate_morans_i(wide, w, "stacked") == pytest.approx(
        float((hourly * variances).sum() / variances.sum())
    )


def test_all_aggregations_coincide_when_every_hour_is_the_same_map():
    cells, wide = _hex_hour_wide()
    same = pd.DataFrame({h: wide[0] for h in range(3)}, index=cells)
    w = h3_ring1_weights(cells, style="B")
    values = [aggregate_morans_i(same, w, a) for a in AGGREGATIONS]
    assert values == pytest.approx([values[0]] * 3)
    with pytest.raises(ValueError, match="aggregation"):
        aggregate_morans_i(same, w, "otra")


def test_grid_has_six_combinations_with_one_principal():
    cells, wide = _hex_hour_wide()
    grid = morans_i_grid({"a": wide, "b": wide * 2.0}, cells)
    assert len(grid) == 6 and grid["principal"].sum() == 1
    principal = grid[grid["principal"]].iloc[0]
    assert (principal["estilo"], principal["agregacion"]) == ("W", "mean_of_hourly")
    assert grid["a"].to_numpy() == pytest.approx(grid["b"].to_numpy())  # invariante a la escala


def test_wide_by_hour_orders_rows_and_rejects_incomplete_grids():
    df = pd.DataFrame({"hex": ["b", "a", "b", "a"], "hour": [7, 7, 8, 8], "v": [1, 2, 3, 4]})
    wide = wide_by_hour(df, "v", ["a", "b"])
    assert list(wide.index) == ["a", "b"] and wide.loc["a", 8] == 4
    with pytest.raises(ValueError, match="no cubre"):
        wide_by_hour(df.iloc[:3], "v", ["a", "b"])


# ------------------------------------------------------------------ etiquetas
def test_agreement_labels():
    assert moran_agreement(0.4694, 0.4694) == "exacto"
    assert moran_agreement(0.4698, 0.4694) == "exacto"  # dentro de ±0,0005
    assert moran_agreement(0.4656, 0.4694) == "aproximado"  # 0,8 %
    assert moran_agreement(0.4694 * 1.019, 0.4694) == "aproximado"  # 1,9 %: dentro del 2 %
    assert moran_agreement(0.4694 * 1.021, 0.4694) == "no reproduce"  # 2,1 %: fuera
    assert moran_agreement(0.4190, 0.4694) == "no reproduce"  # -0,05
