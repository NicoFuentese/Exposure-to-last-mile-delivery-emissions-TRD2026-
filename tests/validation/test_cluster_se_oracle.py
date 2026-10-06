"""Errores estándar con cluster de Python contra `sandwich::vcovCL` de R (`reference/r_oracle/`).

R (`pscl::zeroinfl` + `vcovCL`, `lm` + `vcovCL`) calcula el mismo sandwich que el código de los
autores. No es una réplica del paper sino un contraste independiente de la implementación; las
diferencias residuales vienen del punto de evaluación (pscl se detiene antes del óptimo) y de la
Hessiana numérica de `optim` frente a nuestras derivadas analíticas.
"""

import pytest

from lastmile_exposure import config
from lastmile_exposure.inference.cluster import nb_inference, ols_inference
from lastmile_exposure.inference.zinb_sandwich import PARAM_ORDER, zinb_inference
from lastmile_exposure.models.ols import fit_ols, fit_ols_positive
from lastmile_exposure.validation.paper_tables import load_cluster_se_oracle, load_pscl_oracle

TAGS = ("dynamic", "static")
REGS = list(config.REGRESSORS)


def test_oracle_has_51_clusters_and_all_columns():
    for tag in TAGS:
        oracle = load_cluster_se_oracle(tag)
        assert list(oracle.index) == ["(Intercept)", *REGS]
        assert oracle["zinb_se_cluster"].gt(0).all()


@pytest.mark.parametrize("tag", TAGS)
def test_zinb_cluster_sandwich_matches_r_vcovcl(model_frames, tag):
    """`vcovCL(zeroinfl)`: el sandwich del ZINB completo (no el de la NB), a ≤ 2,5 %."""
    oracle = load_cluster_se_oracle(tag)["zinb_se_cluster"].loc[REGS]
    params = load_pscl_oracle(tag).loc[list(PARAM_ORDER)]
    ours = zinb_inference(params, model_frames[tag]["count"])
    assert ours.n_clusters == config.N_COMUNAS
    ratio = ours.se / oracle
    assert ratio.between(0.975, 1.025).all(), ratio.round(4).to_dict()


@pytest.mark.parametrize("tag", TAGS)
def test_zinb_sandwich_differs_moderately_from_the_nb_equivalent(model_frames, tag):
    """H25: con π̂ ≈ 0 el ZINB colapsa en la NB, pero su sandwich no coincide exactamente.

    La inflación casi no identificada filtra al bloque de conteo una parte O(1) del sandwich:
    los SE del ZINB completo difieren de los de la NB (π = 0) entre ~5 % y ~17 %. (El
    `vcovCL(glm.nb)` de R no sirve de contraste de la NB: usa información esperada con θ fijo y
    da SE que no son comparables con ninguno de los dos.)
    """
    params = load_pscl_oracle(tag)
    frame = model_frames[tag]["count"]
    ratio = zinb_inference(params, frame).se / nb_inference(params, frame).se
    assert 0.05 < (ratio - 1).abs().max() < 0.25, ratio.round(3).to_dict()


@pytest.mark.parametrize("tag", TAGS)
def test_ols_cluster_se_matches_r(model_frames, tag):
    oracle = load_cluster_se_oracle(tag)
    df = model_frames[tag]["distance"]
    positive = df[df[config.OUTCOME_DISTANCE] > 0]
    cases = {
        "ols_k_se_cluster": ols_inference(fit_ols(df), df).se,
        "ols_logk_se_cluster": ols_inference(fit_ols(df, log_positive=True), positive).se,
        "ols_pos_se_cluster": ols_inference(fit_ols_positive(df), positive).se,
    }
    for column, ours in cases.items():
        ratio = ours / oracle[column].loc[REGS]
        assert ratio.between(0.995, 1.005).all(), (column, ratio.round(4).to_dict())
