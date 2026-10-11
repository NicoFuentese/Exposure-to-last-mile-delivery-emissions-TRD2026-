"""Wasserstein con el método del script de los autores (H24): piezas con datos sintéticos.

No necesitan los datos confidenciales. La comparación con los valores publicados y con las 200
semillas guardadas está en `tests/validation/test_mobility_seeds_reference.py`.
"""

import h3
import numpy as np
import pandas as pd
import pytest
from pyproj import Geod

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import (
    EARTH_RADIUS_KM,
    GroupMasses,
    authors_sample,
    group_masses,
    haversine_km,
    mobility_over_seeds,
    normalize_by_median,
    normalized_seeds,
    seed_agreement,
    seed_ranks,
    summarize_seeds,
    wasserstein_1,
    wasserstein_1_geodesic,
)

LABELS = tuple(label for label, _, _ in config.TABLE2_GROUPS)


def _rad(*pairs):
    return np.radians(np.array(pairs, dtype=float))


# ------------------------------------------------------------------ distancia geodésica
def test_haversine_known_values():
    a, b = _rad((0, 0)), _rad((0, 90), (0, 0))
    d = haversine_km(a, b)
    assert d[0, 0] == pytest.approx(EARTH_RADIUS_KM * np.pi / 2, rel=1e-12)  # cuarto de círculo
    assert d[0, 1] == 0.0
    assert haversine_km(b, a).T == pytest.approx(d)  # simétrica


def test_haversine_is_within_half_a_percent_of_the_wgs84_ellipsoid_in_santiago():
    """Lo que usa el script de los autores es la elipsoide (`geosphere::distm`)."""
    rng = np.random.default_rng(0)
    lat1, lat2 = rng.uniform(-33.7, -33.2, (2, 400))
    lon1, lon2 = rng.uniform(-71.0, -70.5, (2, 400))
    ellipsoid_m = Geod(ellps="WGS84").inv(lon1, lat1, lon2, lat2)[2]
    sphere_km = np.array(
        [
            haversine_km(_rad((a, b)), _rad((c, d)))[0, 0]
            for a, b, c, d in zip(lat1, lon1, lat2, lon2, strict=True)
        ]
    )
    rel = np.abs(sphere_km / (ellipsoid_m / 1000) - 1)
    assert rel.max() < 0.004


# ------------------------------------------------------------------ transporte óptimo
def test_wasserstein_geodesic_point_masses_and_splits():
    ll = _rad((-33.40, -70.60), (-33.45, -70.65), (-33.50, -70.55))
    d = haversine_km(ll, ll)
    assert wasserstein_1_geodesic([1, 0, 0], [0, 0, 1], ll) == pytest.approx(d[0, 2])
    assert wasserstein_1_geodesic([1, 0, 0], [0.5, 0.5, 0], ll) == pytest.approx(0.5 * d[0, 1])
    assert wasserstein_1_geodesic([2, 1, 1], [2, 1, 1], ll) == 0.0
    # simétrica e invariante a la escala de las masas (se normalizan a 1)
    p, q = np.array([3.0, 1.0, 2.0]), np.array([1.0, 4.0, 1.0])
    assert wasserstein_1_geodesic(p, q, ll) == pytest.approx(wasserstein_1_geodesic(q * 9, p, ll))
    assert wasserstein_1_geodesic(p * 7, q, ll) == pytest.approx(wasserstein_1_geodesic(p, q, ll))


def test_geodesic_and_euclidean_transport_share_the_same_core():
    """Sobre un plano chico, W1 geodésico en km ≈ W1 euclídeo en metros / 1000 (mismo núcleo)."""
    rng = np.random.default_rng(1)
    ll = _rad(*zip(rng.uniform(-33.50, -33.45, 12), rng.uniform(-70.70, -70.65, 12), strict=True))
    p, q = rng.random(12), rng.random(12)
    # coordenadas planas locales en metros (aprox. equirectangular)
    lat0 = ll[:, 0].mean()
    xy = np.column_stack([ll[:, 1] * np.cos(lat0), ll[:, 0]]) * (EARTH_RADIUS_KM * 1000)
    assert wasserstein_1_geodesic(p, q, ll) == pytest.approx(
        wasserstein_1(p, q, xy) / 1000, rel=2e-3
    )


# ------------------------------------------------------------------ muestra y masas
def test_authors_sample_is_reproducible_unique_and_capped():
    a = authors_sample(11_144, seed=3)
    assert len(a) == 5_000 and len(set(a)) == 5_000 and a.min() >= 0 and a.max() < 11_144
    assert np.array_equal(a, authors_sample(11_144, seed=3))
    assert not np.array_equal(a, authors_sample(11_144, seed=4))
    small = authors_sample(30, seed=0)
    assert sorted(small) == list(range(30))  # menos hexágonos que la muestra: se usan todos


def _tiny_panel():
    cells = [h3.latlng_to_cell(-33.45 + 0.01 * i, -70.66, 9) for i in range(2)]
    rows = []
    for k, cell in enumerate(cells):
        for hour in config.HOURS:
            row = {"hex": cell, "hour": hour, "poblacion_flotante": 100.0 * (k + 1)}
            for _, column, _ in config.TABLE2_GROUPS:
                row[column] = 0.1
            row["genero_masc"] = 0.2 if hour in (10, 11, 12) else 0.5  # señal solo en la ventana
            rows.append(row)
    return pd.DataFrame(rows), cells


def test_group_masses_average_the_inclusive_windows():
    panel, cells = _tiny_panel()
    panel.loc[(panel["hour"] == 9) & (panel["hex"] == cells[0]), "genero_masc"] = 0.99  # señuelos
    panel.loc[(panel["hour"] == 13) & (panel["hex"] == cells[0]), "genero_masc"] = 0.99
    m = group_masses(panel)
    assert m.labels == LABELS and list(m.hexes) == cells
    male = LABELS.index("Male")
    # mañana: media de 10, 11, 12 de población × 0,2; tarde: 20, 21, 22 con 0,5
    assert m.morning[male].tolist() == pytest.approx([100 * 0.2, 200 * 0.2])
    assert m.evening[male].tolist() == pytest.approx([100 * 0.5, 200 * 0.5])
    assert m.morning[LABELS.index("AB")].tolist() == pytest.approx([100 * 0.1, 200 * 0.1])
    assert m.latlon.shape == (2, 2) and np.all(np.abs(m.latlon) < np.pi)


# ------------------------------------------------------------------ semillas
def _random_masses(n=60, seed=0):
    rng = np.random.default_rng(seed)
    latlon = _rad(*zip(rng.uniform(-33.7, -33.2, n), rng.uniform(-71.0, -70.5, n), strict=True))
    shape = (len(LABELS), n)
    return GroupMasses(
        LABELS, np.array([f"h{i}" for i in range(n)]), latlon, rng.random(shape), rng.random(shape)
    )


def test_mobility_over_seeds_is_reproducible_and_depends_on_the_seed():
    masses = _random_masses()
    first = mobility_over_seeds(masses, seeds=[0, 1, 2], size=40, workers=1)
    again = mobility_over_seeds(masses, seeds=[0, 1, 2], size=40, workers=1)
    assert first.shape == (3, 15) and first.index.name == "seed"
    assert list(first.columns) == list(LABELS)
    assert np.array_equal(first.to_numpy(), again.to_numpy())
    assert not np.allclose(first.loc[0], first.loc[1])
    assert (first > 0).all().all()
    calls = []
    mobility_over_seeds(
        masses, seeds=[0, 1], size=40, workers=1, progress=lambda d, t: calls.append((d, t))
    )
    assert calls == [(1, 2), (2, 2)]


def test_checkpoint_saves_each_seed_and_resume_only_computes_the_missing_ones(tmp_path):
    masses = _random_masses()
    partial = tmp_path / "partial.csv"
    full = mobility_over_seeds(masses, seeds=[0, 1, 2, 3], size=40, workers=1, checkpoint=partial)
    assert pd.read_csv(partial, index_col="seed").index.tolist() == [0, 1, 2, 3]
    # una corrida interrumpida tras 2 semillas
    pd.read_csv(partial, index_col="seed").iloc[:2].to_csv(partial)
    calls = []
    resumed = mobility_over_seeds(
        masses,
        seeds=[0, 1, 2, 3],
        size=40,
        workers=1,
        checkpoint=partial,
        resume=True,
        progress=lambda d, t: calls.append((d, t)),
    )
    assert calls == [(3, 4), (4, 4)]  # solo calcula las semillas 2 y 3
    assert resumed.index.tolist() == [0, 1, 2, 3] and resumed.index.dtype == full.index.dtype
    assert np.allclose(resumed.to_numpy(), full.to_numpy(), rtol=1e-9)
    assert pd.read_csv(partial, index_col="seed").index.tolist() == [0, 1, 2, 3]
    # sin resume el archivo parcial se parte de cero
    mobility_over_seeds(masses, seeds=[5], size=40, workers=1, checkpoint=partial)
    assert pd.read_csv(partial, index_col="seed").index.tolist() == [5]


def test_resume_rejects_a_checkpoint_with_other_columns(tmp_path):
    partial = tmp_path / "partial.csv"
    pd.DataFrame({"x": [1.0]}, index=pd.Index([0], name="seed")).to_csv(partial)
    with pytest.raises(ValueError, match="columnas"):
        mobility_over_seeds(
            _random_masses(), seeds=[0], size=40, workers=1, checkpoint=partial, resume=True
        )


def test_with_a_sample_as_large_as_the_grid_the_seed_does_not_matter():
    masses = _random_masses(n=25)
    out = mobility_over_seeds(masses, seeds=[0, 7], size=5_000, workers=1)  # usa los 25 hexágonos
    assert np.allclose(out.loc[0], out.loc[7], rtol=1e-10)


# ------------------------------------------------------------------ resumen
def _synthetic_raw(n=60, noise=0.01):
    """Distancias con grupos bien separados dentro de cada categoría y poco ruido."""
    base = dict.fromkeys(LABELS, 1.0)
    for rank, label in enumerate(["Male", "Female"]):
        base[label] = 2.0 - 0.5 * rank
    for rank, label in enumerate(["45-54", "55-64", "35-44", "25-34", "Under 25", "65+"]):
        base[label] = 3.0 - 0.4 * rank
    for rank, label in enumerate(["AB", "E", "C3", "C2", "D", "C1a", "C1b"]):
        base[label] = 5.0 - 0.5 * rank
    rng = np.random.default_rng(0)
    values = pd.Series(base)[list(LABELS)].to_numpy() * np.exp(noise * rng.standard_normal((n, 15)))
    return pd.DataFrame(values, columns=list(LABELS), index=pd.Index(range(n), name="seed"))


def test_summary_of_a_published_table_that_is_one_of_the_draws():
    raw = _synthetic_raw()
    norm = normalized_seeds(raw)
    published = norm.median()
    published_rank = seed_ranks(raw).mode().iloc[0].astype(int)
    summary = summarize_seeds(raw, published, published_rank)
    assert summary["inside_band"].all()
    assert summary["z"].abs().max() < 0.5
    assert summary["p_rank_published"].eq(1.0).all()
    assert (summary["rank_mode"] == summary["rank_published"]).all()
    agreement = seed_agreement(raw, published, published_rank)
    assert agreement["n_inside_band"] == 15 and agreement["n_abs_z_gt_2"] == 0
    assert agreement["p_all_ranks"] == 1.0
    assert all(e["p_top"] == 1.0 and e["p_bottom"] == 1.0 for e in agreement["p_extremes"].values())
    assert agreement["error_max"] < 0.1


def test_summary_flags_a_published_value_far_from_the_seeds():
    raw = _synthetic_raw()
    published = normalized_seeds(raw).median()
    published["C3"] = (
        published["C3"] * 1.5
    )  # un valor publicado muy lejos de lo que dan las semillas
    summary = summarize_seeds(raw, published, seed_ranks(raw).mode().iloc[0].astype(int))
    assert not summary.loc["C3", "inside_band"] and abs(summary.loc["C3", "z"]) > 5
    assert summary["inside_band"].sum() == 14
    assert normalize_by_median(raw.iloc[0]).notna().all()
