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


def test_outputs_dir_can_be_redirected_with_an_environment_variable(tmp_path):
    """Para que las pruebas que ejecutan scripts de verdad no pisen los resultados reales."""
    import os
    import subprocess
    import sys

    code = "from lastmile_exposure import config; print(config.OUTPUTS_DIR)"

    def outputs_dir(**env):
        merged = {k: v for k, v in os.environ.items() if k != "LASTMILE_OUTPUTS_DIR"} | env
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, env=merged
        )
        return out.stdout.strip()

    assert outputs_dir().endswith("outputs")
    assert outputs_dir(LASTMILE_OUTPUTS_DIR=str(tmp_path)) == str(tmp_path)
