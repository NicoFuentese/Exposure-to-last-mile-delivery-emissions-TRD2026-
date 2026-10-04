"""Movilidad en la Tabla 2: integración y brecha documentada con los valores publicados (H24).

El método descrito en el paper (W1 exacto en 2D, euclídeo, conteos agrupados, ventanas 10-12 y
20-22) NO reproduce los valores publicados: estas pruebas fijan el estado actual para que un
cambio de método no pase inadvertido. Si algún día se identifica el método de los autores, la
prueba de la brecha debe reemplazarse por una de igualdad con la tabla.
"""

import pytest

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import (
    group_distribution,
    hex_coordinates,
    mobility_rank,
    normalize_by_median,
    wasserstein_1,
)
from lastmile_exposure.reporting.table2 import table2
from lastmile_exposure.validation.paper_tables import load_mobility_reference, load_table2


def _published():
    pub = load_table2().set_index("variable")
    labels = [label for label, _, _ in config.TABLE2_GROUPS]
    return pub.loc[labels, "wasserstein"], pub.loc[labels, "mobility_rank"].astype(int)


def test_table2_with_mobility_fills_the_normalized_columns(panel):
    out = table2(panel, mobility_raw=load_mobility_reference()).set_index("variable")
    assert out.loc["Avg Population", ["wasserstein", "mobility_rank"]].isna().all()
    by_dim = out.drop("Avg Population").groupby("group")["wasserstein"].median()
    assert by_dim.to_numpy() == pytest.approx([1.0, 1.0, 1.0], abs=1e-12)
    assert set(out.drop("Avg Population")["mobility_rank"]) <= set(range(1, 8))
    # sin distancias, las columnas siguen en NaN (como antes)
    assert table2(panel)[["wasserstein", "mobility_rank"]].isna().all().all()


def test_documented_gap_to_the_published_values():
    """H24: error máx. ~0,14 en los valores normalizados y 12 de 15 rankings."""
    published, pub_rank = _published()
    norm = normalize_by_median(load_mobility_reference().reindex(published.index))
    max_err = float((norm - published).abs().max())
    assert 0.10 < max_err < 0.20
    assert int((mobility_rank(norm) == pub_rank).sum()) == 12


def test_the_papers_qualitative_claims_about_mobility_do_hold():
    """Sí coinciden las afirmaciones del texto: hombres > mujeres, 45-54 el más móvil, 65+ el
    menos móvil, AB el GSE más móvil y C1b el menos móvil."""
    rank = mobility_rank(normalize_by_median(load_mobility_reference()))
    assert rank["Male"] < rank["Female"]
    assert rank["45-54"] == 1 and rank["65+"] == 6
    assert rank["AB"] == 1 and rank["C1b"] == 7
    published, pub_rank = _published()
    sex_age = [label for label, _, dim in config.TABLE2_GROUPS if dim in ("sex", "age")]
    assert (rank[sex_age] == pub_rank[sex_age]).all()  # sexo y edad: 8 de 8 rankings


@pytest.mark.slow
def test_recomputed_distances_match_the_stored_reference(panel):
    """Recalcula Male y Female (~2 min) y compara con los valores guardados en reference/."""
    stored = load_mobility_reference()
    hexes = panel["hex"].drop_duplicates().to_numpy()
    coords = hex_coordinates(hexes)
    by_label = {label: col for label, col, _ in config.TABLE2_GROUPS}
    for label in ("Male", "Female"):
        morning = group_distribution(panel, by_label[label], config.MORNING_HOURS, hexes)
        evening = group_distribution(panel, by_label[label], config.EVENING_HOURS, hexes)
        assert wasserstein_1(morning, evening, coords) == pytest.approx(stored[label], rel=1e-6)
