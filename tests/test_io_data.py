"""Lectura y estructura de los datos reales del paquete (H6, H13). Requiere los datos."""

import pytest

from lastmile_exposure import config
from lastmile_exposure.demographics.static import static_shares
from lastmile_exposure.io.panel import load_counts_dataset
from lastmile_exposure.io.static import load_static_raw


def test_panel_grid_and_comunas(panel):
    assert len(panel) == config.N_HEXAGON_HOURS
    assert panel["comuna"].nunique() == config.N_COMUNAS
    assert "MAIPÚ" in set(panel["comuna"])  # la lectura respeta los acentos (UTF-8)


def test_zero_population_rows_have_zero_shares(panel):
    """H13: 1.427 filas con población 0 y todos los shares en 0 (no NaN)."""
    empty = panel[panel["poblacion_flotante"] == 0]
    assert len(empty) == 1_427
    assert (empty["genero_masc"] == 0).all() and (empty["gse_ab"] == 0).all()


def test_counts_dataset_is_the_papers_not_the_data_base_copy(panel):
    """H6: la base de 00_data tiene ~29,6 % de ceros (la copia de 00_out tiene ~52 %)."""
    counts = load_counts_dataset()
    assert (counts["median_vehicles"] == 0).mean() == pytest.approx(0.2956, abs=5e-4)
    assert counts["count_wednesdays"].max() == 42


def test_static_gse_are_percentages_and_convert_to_proportions(panel):
    raw = load_static_raw()
    assert (
        raw[["gse_ab", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3", "gse_d", "gse_e"]]
        .sum(axis=1)
        .between(99.9, 100.1)
        .all()
    )
    converted = static_shares(raw)
    assert (
        converted[["gse_ab", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3", "gse_d", "gse_e"]]
        .sum(axis=1)
        .between(0.999, 1.001)
        .all()
    )
