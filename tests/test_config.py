"""Coherencia interna de las constantes de config.py con el paper."""

from lastmile_exposure import config


def test_grid_dimensions():
    assert len(config.HOURS) == 16
    assert config.HOURS[0] == 7 and config.HOURS[-1] == 22
    assert config.N_HEXAGON_HOURS == 178_304  # [P §3.1]


def test_local_complete_hours_are_subset_of_hours():
    assert set(config.LOCAL_COMPLETE_HOURS) <= set(config.HOURS)
    assert config.LOCAL_COMPLETE_HOURS == tuple(range(7, 20))


def test_eleven_regressors_without_reference_categories():
    assert len(config.REGRESSORS) == 11
    assert len(set(config.REGRESSORS)) == 11
    for ref in config.REFERENCE_CATEGORIES.values():
        assert ref not in config.REGRESSORS


def test_every_regressor_and_reference_has_a_paper_label():
    for name in (*config.REGRESSORS, *config.REFERENCE_CATEGORIES.values()):
        if name == "genero_fem":  # Female no aparece como fila en las Tablas 4-5
            continue
        assert name in config.LABELS


def test_variants():
    assert {v.value for v in config.Variant} == {"as_published", "local_time"}
