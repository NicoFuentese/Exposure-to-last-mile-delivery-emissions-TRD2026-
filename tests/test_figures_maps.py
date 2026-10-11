"""Mapas hexagonales (Fig. 1): geometría, escalas y estructura con datos sintéticos.

No necesitan los datos confidenciales. Las pruebas con los datos reales están en
`tests/validation/test_fig1_maps.py`.
"""

import h3
import matplotlib
import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure
from pyproj import Geod

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import GroupMasses
from lastmile_exposure.figures.maps import (
    BOUNDS,
    FIG2_PROXY_NAME,
    fig1_data,
    hex_vertices,
    in_bounds,
    km_to_lon_degrees,
    log_colorbar_ticks,
    plot_fig1,
    plot_vehicle_proxy,
    vehicle_means,
)

LABELS = tuple(label for label, _, _ in config.TABLE2_GROUPS)
CENTER = h3.latlng_to_cell(-33.45, -70.65, 9)
FAR_AWAY = h3.latlng_to_cell(-33.05, -71.62, 9)  # fuera de los límites del mapa


def _masses(seed=0):
    """127 hexágonos en Santiago + 1 lejano; los máximos de AB y C1b están en lugares conocidos."""
    cells = sorted(h3.grid_disk(CENTER, 6)) + [FAR_AWAY]
    rng = np.random.default_rng(seed)
    n = len(cells)
    latlon = np.radians([h3.cell_to_latlng(c) for c in cells])
    morning, evening = rng.random((15, n)) * 100, rng.random((15, n)) * 100
    ab, c1b = LABELS.index("AB"), LABELS.index("C1b")
    morning[ab, 3], evening[ab, 5] = 1511.0, 1164.0  # el máximo de AB está en la mañana
    morning[c1b, 7], evening[c1b, 9] = 5091.0, 7073.0  # el máximo de C1b está en la tarde
    morning[:, -1] = evening[:, -1] = 10_000.0  # el hexágono lejano no debe mandar en la escala
    return GroupMasses(LABELS, np.array(cells), latlon, morning, evening), cells


# ------------------------------------------------------------------ geometría
def test_hex_vertices_are_lon_lat_hexagons_around_their_centroid():
    vertices = hex_vertices([CENTER])
    assert vertices.shape == (1, 6, 2)
    lat, lon = h3.cell_to_latlng(CENTER)
    assert vertices[0].mean(axis=0) == pytest.approx([lon, lat], abs=1e-4)  # orden (lon, lat)
    assert vertices[0, :, 0].min() < -70.0 and vertices[0, :, 1].max() < -33.0
    # arista media de un H3 de resolución 9: ~175 m, así que el hexágono mide ~0,004° de ancho
    assert np.ptp(vertices[0, :, 0]) == pytest.approx(0.0035, abs=0.001)


def test_in_bounds_keeps_santiago_and_drops_far_cells():
    latlon = np.radians([h3.cell_to_latlng(c) for c in (CENTER, FAR_AWAY)])
    assert in_bounds(latlon).tolist() == [True, False]
    lon_min, lon_max, lat_min, lat_max = BOUNDS
    edge = np.radians([[lat_max, lon_max], [lat_max + 1e-6, lon_max]])
    assert in_bounds(edge).tolist() == [True, False]  # los bordes cuentan como dentro


def test_ten_km_scale_bar_is_ten_km_on_the_ground():
    lat, lon = -33.5, -70.6
    degrees = km_to_lon_degrees(10.0, lat, lon)
    _, _, meters = Geod(ellps="WGS84").inv(lon, lat, lon + degrees, lat)
    assert meters == pytest.approx(10_000, abs=2)
    assert 0.10 < degrees < 0.12


# ------------------------------------------------------------------ datos de la Fig. 1
def test_fig1_data_drops_far_hexagons_and_shares_one_scale_per_group():
    masses, cells = _masses()
    data = fig1_data(masses)
    assert len(data["hexes"]) == len(cells) - 1 and FAR_AWAY not in set(data["hexes"])
    assert data["vertices"].shape == (len(cells) - 1, 6, 2)
    # el máximo de cada grupo es el de la ventana que lo tiene, sin contar el hexágono lejano
    assert data["vmax"] == {"AB": 1511.0, "C1b": 7073.0}
    ab = masses.morning[LABELS.index("AB")][:-1]
    assert np.array_equal(data["values"][("AB", "morning")], ab)


# ------------------------------------------------------------------ dibujo
@pytest.fixture(scope="module")
def fig1():
    masses, cells = _masses()
    return plot_fig1(masses), masses, cells


def test_fig1_has_four_maps_with_their_color_bars_and_the_papers_titles(fig1):
    fig, _, _ = fig1
    assert isinstance(fig, Figure) and "pyplot" not in type(fig).__module__
    assert len(fig.axes) == 4  # 4 mapas; cada uno lleva su barra de color como eje insertado
    assert all(len(ax.child_axes) == 1 for ax in fig.axes)
    titles = [ax.get_title() for ax in fig.axes]
    assert titles == [
        "SEG AB Daytime Population (10:00-12:00)",
        "SEG AB Daytime Population (20:00-22:00)",
        "SEG C1B Daytime Population (10:00-12:00)",
        "SEG C1B Daytime Population (20:00-22:00)",
    ]


def test_each_row_uses_one_linear_scale_from_zero_to_the_groups_maximum(fig1):
    fig, _, cells = fig1
    maps = fig.axes
    collections = [ax.collections[0] for ax in maps]
    assert [c.get_clim() for c in collections] == [(0.0, 1511.0)] * 2 + [(0.0, 7073.0)] * 2
    assert all(len(c.get_paths()) == len(cells) - 1 for c in collections)
    # la barra de color marca solo los extremos
    labels = [[t.get_text() for t in ax.child_axes[0].get_xticklabels()] for ax in maps]
    assert labels == [["0", "1511"]] * 2 + [["0", "7073"]] * 2


def test_polygon_colors_follow_the_turbo_palette_on_a_linear_scale(fig1):
    fig, masses, _ = fig1
    ax = next(
        a for a in fig.axes if a.get_title().startswith("SEG AB") and "10:00" in a.get_title()
    )
    collection = ax.collections[0]
    collection.update_scalarmappable()
    values = collection.get_array()
    cmap, norm = matplotlib.colormaps["turbo"], collection.norm
    for i in (0, 3, 50):  # el 3 es el máximo de AB (1511 → extremo rojo oscuro)
        assert collection.get_facecolor()[i] == pytest.approx(cmap(norm(values[i])))
    assert norm(1511.0) == pytest.approx(1.0) and norm(0.0) == pytest.approx(0.0)


def test_axes_use_degrees_south_and_west_with_the_authors_limits(fig1):
    fig, _, _ = fig1
    ax = next(a for a in fig.axes if a.get_title().startswith("SEG"))
    lon_min, lon_max, lat_min, lat_max = BOUNDS
    assert (ax.get_xlim(), ax.get_ylim()) == ((lon_min, lon_max), (lat_min, lat_max))
    assert [t.get_text() for t in ax.get_xticklabels()] == [
        "70.8°W",
        "70.7°W",
        "70.6°W",
        "70.5°W",
        "70.4°W",
    ]
    assert [t.get_text() for t in ax.get_yticklabels()][0] == "33.3°S"
    # proporción real: 0,40° de latitud por 0,45° de longitud × cos(33,5°)
    assert ax.get_box_aspect() == pytest.approx(0.40 / (0.45 * np.cos(np.radians(33.5))))


def test_fig1_renders_to_png(fig1, tmp_path):
    fig, _, _ = fig1
    path = tmp_path / "fig1.png"
    fig.savefig(path, dpi=40)
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# ------------------------------------------------------------------ sustituto de la Fig. 2
def _counts():
    """Tres hexágonos con vehículos en varias horas (una fuera de la grilla, la 6) y uno lejano."""
    near = sorted(h3.grid_disk(CENTER, 1))[:3]
    rows = []
    for k, cell in enumerate(near):
        for hour, vehicles in ((6, 99.0), (7, 2.0 * (k + 1)), (8, 4.0 * (k + 1)), (22, 0.0)):
            rows.append({"hex": cell, "hour": hour, "median_vehicles": vehicles})
    rows.append({"hex": FAR_AWAY, "hour": 7, "median_vehicles": 500.0})
    return pd.DataFrame(rows), near


def test_vehicle_means_average_the_published_hours_only():
    counts, near = _counts()
    means = vehicle_means(counts).set_index("hex")["mean_vehicles"]
    # horas 7, 8 y 22 → (2k + 4k + 0) / 3; la hora 6 (99) queda fuera
    for k, cell in enumerate(near):
        assert means[cell] == pytest.approx(6.0 * (k + 1) / 3)
    assert means[FAR_AWAY] == pytest.approx(500.0)


def test_log_colorbar_ticks_follow_the_rule_that_gives_the_papers_fig2_labels():
    """0, 1/3, 2/3 y el máximo de log1p, con exp(x) − 1: 0, 11, 147 y 1807 (Fig. 2, p.8)."""
    ticks, labels = log_colorbar_ticks(float(np.log1p(1807)))
    assert labels == ["0", "11", "147", "1807"]
    assert ticks[0] == 0 and ticks[-1] == pytest.approx(np.log1p(1807))


@pytest.fixture(scope="module")
def proxy():
    counts, near = _counts()
    return plot_vehicle_proxy(vehicle_means(counts)), near


def test_proxy_is_labelled_as_a_substitute_and_uses_the_fig2_style(proxy):
    fig, near = proxy
    (ax,) = fig.axes
    assert ax.get_title().startswith("PROXY, NOT Fig. 2")
    collection = ax.collections[0]
    assert collection.cmap.name == "inferno" and len(collection.get_paths()) == len(
        near
    )  # sin el lejano
    top = float(np.log1p(6.0 * len(near) / 3))
    assert collection.get_clim() == (0.0, pytest.approx(top))
    ticks, labels = log_colorbar_ticks(top)
    colorbar_axes = ax.child_axes[0]
    assert [t.get_text() for t in colorbar_axes.get_xticklabels()] == labels
    assert colorbar_axes.get_title() == "Vehicles"


def test_proxy_name_is_the_stem_of_the_published_png():
    """`docs/figures/` lleva este nombre, solo como PNG (lo vigila test_published_figures)."""
    assert FIG2_PROXY_NAME == "fig2_proxy_vehicles"
