"""Normalización por la mediana y ranking de movilidad (Tabla 2). No necesitan los datos."""

import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.demographics.mobility import mobility_rank, normalize_by_median
from lastmile_exposure.validation.paper_tables import load_table2


def _published():
    table = load_table2().set_index("variable")
    labels = [label for label, _, _ in config.TABLE2_GROUPS]
    return table.loc[labels, "wasserstein"], table.loc[labels, "mobility_rank"].astype(int)


def test_every_table2_group_has_a_dimension_and_hours_are_inclusive_windows():
    assert len(config.TABLE2_GROUPS) == 15
    assert set(config.DIMENSION_OF.values()) == {"sex", "age", "seg"}
    assert config.MORNING_HOURS == (10, 11, 12) and config.EVENING_HOURS == (20, 21, 22)


def test_published_values_have_median_one_in_every_dimension():
    """Hallazgo sobre la Tabla 2: la mediana publicada de cada dimensión es exactamente 1."""
    values, _ = _published()
    medians = values.groupby(values.index.map(config.DIMENSION_OF)).median()
    assert medians.to_numpy() == pytest.approx([1.0, 1.0, 1.0], abs=1e-12)


def test_normalizing_the_published_values_leaves_them_unchanged():
    values, _ = _published()
    assert normalize_by_median(values).to_numpy() == pytest.approx(values.to_numpy(), abs=1e-12)


def test_normalization_is_invariant_to_the_scale_of_the_raw_distances():
    values, _ = _published()
    raw = values * 7_341.5  # p. ej. metros en lugar de unidades relativas
    assert normalize_by_median(raw).to_numpy() == pytest.approx(values.to_numpy(), abs=1e-9)


def test_normalization_divides_by_the_median_of_each_dimension():
    raw = pd.Series({"Male": 30.0, "Female": 10.0, "AB": 5.0, "C1a": 1.0, "C1b": 3.0})
    out = normalize_by_median(raw)
    assert out["Male"] == pytest.approx(1.5) and out["Female"] == pytest.approx(0.5)  # mediana 20
    assert out["C1b"] == pytest.approx(1.0)  # mediana de {5, 1, 3} = 3
    assert out["AB"] == pytest.approx(5 / 3) and out["C1a"] == pytest.approx(1 / 3)


def test_rank_reproduces_the_published_ranking_in_all_15_groups():
    values, ranks = _published()
    assert mobility_rank(values).to_dict() == ranks.to_dict()


def test_rank_is_per_dimension_with_one_for_the_highest_and_ties_share_the_best_place():
    values = pd.Series({"Male": 1.2, "Female": 0.8, "AB": 3.0, "C1a": 3.0, "E": 1.0})
    assert mobility_rank(values).to_dict() == {"Male": 1, "Female": 2, "AB": 1, "C1a": 1, "E": 3}


def test_unknown_groups_are_rejected():
    with pytest.raises(KeyError, match="Tabla 2"):
        normalize_by_median(pd.Series({"Otro": 1.0}))
