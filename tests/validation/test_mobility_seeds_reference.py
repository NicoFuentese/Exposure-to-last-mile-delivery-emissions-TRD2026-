"""Wasserstein de la Tabla 2 con el método del script de los autores y 200 semillas (H24).

FIJAN el estado documentado: los valores publicados son una extracción de un muestreo sin semilla,
así que no se reproducen exactamente; son compatibles con la distribución de las semillas (13 de
15 dentro de la banda del 95 %) y los extremos de cada categoría son estables. Las 200 semillas
están guardadas en `reference/mobility/` (se versionan: son agregados). La primera prueba recalcula
dos semillas con los datos reales para comprobar que la referencia sigue siendo la del código.
"""

import numpy as np
import pytest

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import (
    group_masses,
    mobility_over_seeds,
    normalize_by_median,
    normalized_seeds,
    seed_agreement,
    summarize_seeds,
)
from lastmile_exposure.validation.paper_tables import (
    load_mobility_reference,
    load_mobility_seeds_reference,
    load_table2,
)

LABELS = [label for label, _, _ in config.TABLE2_GROUPS]


@pytest.fixture(scope="module")
def seeds():
    return load_mobility_seeds_reference()


@pytest.fixture(scope="module")
def published():
    table = load_table2().set_index("variable").loc[LABELS]
    return table["wasserstein"].astype(float), table["mobility_rank"].astype(int)


def test_reference_has_200_seeds_for_the_15_groups(seeds):
    assert seeds.shape == (200, 15) and list(seeds.columns) == LABELS
    assert list(seeds.index) == list(range(200))
    assert (seeds > 0).all().all()


@pytest.mark.slow
def test_two_seeds_recomputed_from_the_data_match_the_stored_reference(panel, seeds):
    fresh = mobility_over_seeds(group_masses(panel), seeds=[0, 1], workers=2)
    assert np.allclose(fresh.to_numpy(), seeds.loc[[0, 1]].to_numpy(), rtol=1e-8)


def test_published_values_are_compatible_with_the_seeds(seeds, published):
    """13 de 15 dentro de la banda del 95 %; quedan fuera D y E (E con |z| = 2,7)."""
    summary = summarize_seeds(seeds, *published)
    assert int(summary["inside_band"].sum()) == 13
    assert set(summary.index[~summary["inside_band"]]) == {"D", "E"}
    assert summary.loc["E", "z"] == pytest.approx(2.66, abs=0.05)
    assert int((summary["z"].abs() > 2).sum()) == 1
    assert (summary["z"].abs() < 3).all()


def test_extremes_of_each_category_are_stable_but_the_exact_ranking_is_not(seeds, published):
    agreement = seed_agreement(seeds, *published)
    extremes = agreement["p_extremes"]
    assert (extremes["sex"]["top"], extremes["sex"]["bottom"]) == ("Male", "Female")
    assert (extremes["age"]["top"], extremes["age"]["bottom"]) == ("45-54", "65+")
    assert (extremes["seg"]["top"], extremes["seg"]["bottom"]) == ("AB", "C1b")
    assert extremes["sex"]["p_top"] == extremes["age"]["p_top"] == 1.0
    assert extremes["age"]["p_bottom"] == 1.0
    assert extremes["seg"]["p_top"] >= 0.95 and extremes["seg"]["p_bottom"] >= 0.95
    # el ranking completo coincide en 1 de 200 semillas: los GSE intermedios casi empatan
    assert agreement["p_all_ranks"] == pytest.approx(1 / 200)
    assert agreement["p_ranks_by_dimension"]["sex"] == 1.0
    assert agreement["p_ranks_by_dimension"]["age"] == pytest.approx(0.58, abs=0.02)
    assert agreement["p_ranks_by_dimension"]["seg"] <= 0.02


def test_error_against_the_published_values_by_seed(seeds, published):
    agreement = seed_agreement(seeds, *published)
    assert agreement["error_min"] == pytest.approx(0.059, abs=0.005)
    assert agreement["error_median"] == pytest.approx(0.157, abs=0.005)
    assert agreement["error_max"] == pytest.approx(0.337, abs=0.005)


def test_the_deterministic_reading_of_the_paper_is_within_the_range_of_the_seeds(seeds, published):
    """El error máx. de 0,14 de la lectura determinista (12/15 rankings) cae dentro del rango
    del error de una extracción cualquiera: no era peor que el muestreo de los autores."""
    deterministic = normalize_by_median(load_mobility_reference().reindex(LABELS))
    error = float((deterministic - published[0]).abs().max())
    agreement = seed_agreement(seeds, *published)
    assert error == pytest.approx(0.14, abs=0.01)
    assert agreement["error_min"] < error < agreement["error_max"]
    assert normalized_seeds(seeds).shape == seeds.shape
