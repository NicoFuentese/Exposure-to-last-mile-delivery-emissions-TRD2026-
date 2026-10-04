"""Corrección matemática del transporte óptimo (Wasserstein-1). No necesita los datos.

Capa 1 de la validación: el cálculo es correcto en sí mismo (casos con respuesta conocida,
propiedades de una distancia y contraste con un programa lineal resuelto con otro algoritmo).
"""

import h3
import numpy as np
import ot
import pandas as pd
import pytest
from scipy.optimize import linprog
from scipy.stats import wasserstein_distance

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import (
    group_distribution,
    hex_coordinates,
    wasserstein_1,
)


def _cloud(n=25, seed=0):
    rng = np.random.default_rng(seed)
    coords = rng.random((n, 2)) * 1000.0
    p, q = rng.random(n), rng.random(n)
    return coords, p, q


def _lp_w1(coords, p, q):
    """Wasserstein-1 por programación lineal (HiGHS), sin ninguna reducción."""
    n = len(p)
    cost = ot.dist(coords, coords, metric="euclidean").ravel()
    rows = np.zeros((2 * n, n * n))
    for i in range(n):
        rows[i, i * n : (i + 1) * n] = 1  # lo que sale de i = p_i
        rows[n + i, i::n] = 1  # lo que llega a i = q_i
    res = linprog(
        cost,
        A_eq=rows,
        b_eq=np.concatenate([p / p.sum(), q / q.sum()]),
        bounds=(0, None),
        method="highs",
    )
    return float(res.fun)


def test_matches_a_linear_program_solved_with_another_algorithm():
    for seed in range(3):
        coords, p, q = _cloud(seed=seed)
        assert wasserstein_1(p, q, coords) == pytest.approx(_lp_w1(coords, p, q), abs=1e-9)


def test_reduction_to_surplus_and_deficit_equals_the_full_transport_problem():
    coords, p, q = _cloud(40, seed=7)
    full = float(ot.emd2(p / p.sum(), q / q.sum(), ot.dist(coords, coords, metric="euclidean")))
    assert wasserstein_1(p, q, coords) == pytest.approx(full, abs=1e-9)


def test_two_point_masses_at_distance_d_give_w_equal_to_d():
    coords = np.array([[0.0, 0.0], [3.0, 4.0]])
    assert wasserstein_1([1.0, 0.0], [0.0, 1.0], coords) == pytest.approx(5.0)


def test_translating_a_cloud_by_t_gives_w_equal_to_the_norm_of_t():
    rng = np.random.default_rng(1)
    pts = rng.random((30, 2)) * 100
    t = np.array([3.0, 4.0])
    both = np.vstack([pts, pts + t])
    p = np.concatenate([np.ones(30), np.zeros(30)])
    q = np.concatenate([np.zeros(30), np.ones(30)])
    assert wasserstein_1(p, q, both) == pytest.approx(5.0, rel=1e-9)


def test_collinear_points_match_scipy_one_dimensional_wasserstein():
    rng = np.random.default_rng(2)
    x = np.sort(rng.random(50) * 1000)
    coords = np.column_stack([x, np.zeros(50)])
    p, q = rng.random(50), rng.random(50)
    expected = wasserstein_distance(x, x, p, q)
    assert wasserstein_1(p, q, coords) == pytest.approx(expected, rel=1e-9)


def test_distance_properties_identity_symmetry_and_triangle_inequality():
    coords, p, q = _cloud(seed=4)
    r = np.random.default_rng(5).random(len(p))
    assert wasserstein_1(p, p, coords) == 0.0
    assert wasserstein_1(p, q, coords) == pytest.approx(wasserstein_1(q, p, coords), abs=1e-9)
    assert (
        wasserstein_1(p, r, coords)
        <= wasserstein_1(p, q, coords) + wasserstein_1(q, r, coords) + 1e-9
    )


def test_scaling_the_coordinates_scales_w_and_scaling_the_masses_changes_nothing():
    coords, p, q = _cloud(seed=6)
    base = wasserstein_1(p, q, coords)
    assert wasserstein_1(p, q, coords * 2.5) == pytest.approx(2.5 * base, rel=1e-9)
    assert wasserstein_1(p * 1234.5, q * 0.01, coords) == pytest.approx(base, rel=1e-9)


def test_inputs_are_validated():
    coords, p, q = _cloud(5)
    with pytest.raises(ValueError, match="no negativas"):
        wasserstein_1(-p, q, coords)
    with pytest.raises(ValueError, match="mismo número"):
        wasserstein_1(p[:-1], q, coords)


def test_group_distribution_pools_the_hours_and_follows_the_given_order():
    panel = pd.DataFrame(
        {
            "hex": ["a", "a", "b", "b", "a"],
            "hour": [10, 11, 10, 11, 20],
            "poblacion_flotante": [100.0, 100.0, 50.0, 50.0, 999.0],
            "gse_ab": [0.5, 0.1, 0.4, 0.0, 0.9],
        }
    )
    dist = group_distribution(panel, "gse_ab", (10, 11), ["b", "a", "c"])
    # a: 100*0.5 + 100*0.1 = 60 ; b: 50*0.4 + 50*0 = 20 ; c: sin datos -> 0 ; la hora 20 no cuenta
    assert dist.tolist() == pytest.approx([20 / 80, 60 / 80, 0.0])
    with pytest.raises(ValueError, match="no tiene población"):
        group_distribution(panel, "gse_ab", (15,), ["a"])


def test_hex_coordinates_are_in_meters_and_neighbors_are_a_few_hundred_meters_apart():
    cell = h3.latlng_to_cell(-33.45, -70.66, config.H3_RESOLUTION)
    neighbors = [c for c in h3.grid_disk(cell, 1) if c != cell]
    xy = hex_coordinates([cell, *neighbors])
    distances = np.hypot(*(xy[1:] - xy[0]).T)
    assert len(neighbors) == 6
    assert np.all((distances > 250) & (distances < 450))  # ~350 m entre centros en res. 9
