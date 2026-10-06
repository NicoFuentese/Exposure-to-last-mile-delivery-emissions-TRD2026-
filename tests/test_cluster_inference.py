"""Errores estándar con cluster, p-valores y estrellas con datos sintéticos.

No necesitan los datos confidenciales. Cada implementación se contrasta con una forma
independiente de calcular lo mismo (bucle por cluster, `statsmodels`, derivadas numéricas).
"""

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm
from scipy import stats
from statsmodels.tools.numdiff import approx_fprime, approx_hess

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import regressors
from lastmile_exposure.inference.cluster import (
    cluster_vcov,
    nb2_information,
    nb2_model,
    nb_inference,
    normal_pvalue,
    ols_inference,
    two_part_inference,
)
from lastmile_exposure.inference.zinb_sandwich import (
    PARAM_ORDER,
    _scaled_inverse,
    zinb_design,
    zinb_inference,
    zinb_information,
    zinb_loglike,
    zinb_scores,
)
from lastmile_exposure.models.ols import fit_ols
from lastmile_exposure.models.two_part import fit_two_part
from lastmile_exposure.models.zinb import fit_zinb
from lastmile_exposure.reporting.significance import (
    COLUMNS,
    inference_table,
    nearest_threshold,
    stars,
)
from lastmile_exposure.validation.paper_tables import compare_stars

N_CLUSTERS = 30
PER_CLUSTER = 80


def _clustered_frame(seed=0, cluster_sd=3.0):
    """Marco sintético con regresores y errores correlacionados dentro de la comuna."""
    rng = np.random.default_rng(seed)
    n = N_CLUSTERS * PER_CLUSTER
    comuna = np.repeat(np.arange(N_CLUSTERS), PER_CLUSTER)
    k = len(config.REGRESSORS)
    x = rng.random((n, k)) + rng.normal(0, 0.5, (N_CLUSTERS, k))[comuna]  # parte común por comuna
    beta = np.linspace(-2.0, 2.0, k)
    error = rng.normal(0, cluster_sd, N_CLUSTERS)[comuna] + rng.normal(0, 1.0, n)
    df = pd.DataFrame(x, columns=list(config.REGRESSORS))
    df["comuna"] = comuna
    df["median_distance"] = 60.0 + 40.0 * (x @ beta + error)
    df["median_distance"] = df["median_distance"].clip(lower=0.0)  # ~30 % de ceros
    return df


@pytest.fixture(scope="module")
def frame():
    return _clustered_frame()


# ------------------------------------------------------------------ sandwich genérico y OLS
def test_cluster_vcov_matches_loop_over_clusters():
    rng = np.random.default_rng(1)
    n, k, g = 500, 4, 12
    codes = rng.integers(0, g, n)
    scores = rng.normal(size=(n, k))
    bread = np.linalg.inv(np.cov(rng.normal(size=(60, k)).T) * 10)
    meat = sum(np.outer(scores[codes == c].sum(0), scores[codes == c].sum(0)) for c in range(g))
    expected = g / (g - 1) * (n - 1) / (n - k) * bread @ meat @ bread
    assert cluster_vcov(scores, bread, codes) == pytest.approx(expected, rel=1e-12)


def test_cluster_vcov_correction_factors_and_validation():
    rng = np.random.default_rng(2)
    n, k, g = 300, 3, 10
    codes = np.arange(n) % g
    scores, bread = rng.normal(size=(n, k)), np.eye(k)
    none = cluster_vcov(scores, bread, codes, correction="none")
    assert cluster_vcov(scores, bread, codes, correction="g") == pytest.approx(none * g / (g - 1))
    assert cluster_vcov(scores, bread, codes, correction="cr1") == pytest.approx(
        none * g / (g - 1) * (n - 1) / (n - k)
    )
    with pytest.raises(ValueError, match="correction"):
        cluster_vcov(scores, bread, codes, correction="otra")
    with pytest.raises(ValueError, match="una etiqueta"):
        cluster_vcov(scores, bread, codes[:-1])


def test_ols_cluster_se_matches_statsmodels(frame):
    res = fit_ols(frame)
    inf = ols_inference(res, frame)
    ref = fit_ols(frame).get_robustcov_results(
        cov_type="cluster", groups=frame["comuna"].to_numpy()
    )
    assert inf.se.to_numpy() == pytest.approx(ref.bse[1:], rel=1e-9)  # [0] es la constante
    assert inf.n_clusters == N_CLUSTERS
    assert list(inf.se.index) == list(config.REGRESSORS)


def test_ols_without_cluster_is_the_classic_se(frame):
    res = fit_ols(frame)
    inf = ols_inference(res, frame, cluster=None)
    assert inf.se.to_numpy() == pytest.approx(res.bse.drop("const").to_numpy())
    assert inf.n_clusters is None


def test_ols_log_positive_uses_the_positive_rows(frame):
    positive = frame[frame["median_distance"] > 0]
    res = fit_ols(frame, log_positive=True)
    inf = ols_inference(res, positive)
    ref = res.get_robustcov_results(cov_type="cluster", groups=positive["comuna"].to_numpy())
    assert inf.se.to_numpy() == pytest.approx(ref.bse[1:], rel=1e-9)
    with pytest.raises(ValueError, match="no coincide"):
        ols_inference(res, frame)  # marco distinto del ajuste


def test_cluster_se_exceeds_iid_se_when_errors_are_clustered(frame):
    res = fit_ols(frame)
    ratio = ols_inference(res, frame).se / ols_inference(res, frame, cluster=None).se
    assert ratio.mean() > 1.3  # la correlación dentro de la comuna infla la varianza


def test_pvalue_is_two_sided_normal():
    z = np.array([0.0, 1.96, -1.96, 3.29])
    assert normal_pvalue(z) == pytest.approx([1.0, 0.0500, 0.0500, 0.0010], abs=1e-4)
    assert normal_pvalue(pd.Series([2.5758])).iloc[0] == pytest.approx(0.01, abs=1e-4)
    coef = pd.Series(1.0, index=list(config.REGRESSORS))
    from lastmile_exposure.inference.cluster import Inference

    inf = Inference(coef=coef, se=pd.Series(0.5, index=coef.index), n_clusters=None)
    assert inf.z.iloc[0] == pytest.approx(2.0)
    assert inf.p.iloc[0] == pytest.approx(2 * stats.norm.sf(2.0))


# ------------------------------------------------------------------ NB2 / ZINB
def _count_frame(n=6000, seed=4, pi=0.0):
    rng = np.random.default_rng(seed)
    comuna = rng.integers(0, 25, n)
    k = len(config.REGRESSORS)
    x = rng.random((n, k)) + rng.normal(0, 0.3, (25, k))[comuna]
    beta = np.zeros(k)
    beta[0], beta[1], beta[5] = 0.7, -0.5, 0.4
    mu = np.exp(0.3 + x @ beta + rng.normal(0, 0.3, 25)[comuna])
    theta = 2.0
    df = pd.DataFrame(x, columns=list(config.REGRESSORS))
    y = rng.negative_binomial(theta, theta / (theta + mu))
    df["vehicles"] = np.where(rng.random(n) < pi, 0, y)  # ceros estructurales con prob. `pi`
    df["comuna"] = comuna
    return df


@pytest.fixture(scope="module")
def counts():
    return _count_frame()


@pytest.fixture(scope="module")
def zinb(counts):
    return fit_zinb(counts)


@pytest.fixture(scope="module")
def counts_inflated():
    return _count_frame(seed=8, pi=0.25)


@pytest.fixture(scope="module")
def zinb_inflated(counts_inflated):
    return fit_zinb(counts_inflated)


def test_nb2_information_matches_the_numerical_hessian(counts, zinb):
    """El Jacobiano del score analítico es el Hessiano exacto (el `hessian` de statsmodels no)."""
    model = nb2_model(counts)
    params = zinb.params.loc[["const", *config.REGRESSORS, "alpha"]].to_numpy() * 1.03
    info = nb2_information(model, params)
    numeric = -approx_hess(params, model.loglike)
    assert info == pytest.approx(numeric, rel=1e-4, abs=1e-3)
    assert np.allclose(info, info.T)


def _numeric_sandwich(counts, zinb, *, cluster):
    """Sandwich de la NB con scores y Hessiano por diferencias finitas (independiente)."""
    model = nb2_model(counts)
    p = zinb.params.loc[["const", *config.REGRESSORS, "alpha"]].to_numpy()
    scores = approx_fprime(p, model.loglikeobs, centered=True)
    bread = np.linalg.inv(-approx_hess(p, model.loglike))
    if not cluster:
        return bread
    n, k = scores.shape
    codes = pd.factorize(counts["comuna"])[0]
    g = codes.max() + 1
    sums = np.vstack([scores[codes == c].sum(0) for c in range(g)])
    return g / (g - 1) * (n - 1) / (n - k) * bread @ (sums.T @ sums) @ bread


def test_nb_cluster_se_matches_an_independent_sandwich(counts, zinb):
    inf = nb_inference(zinb, counts)
    expected = np.sqrt(np.diag(_numeric_sandwich(counts, zinb, cluster=True)))[1:12]
    assert zinb.pi < 1e-3  # la NB equivalente solo vale con π ≈ 0 (H21)
    assert inf.se.to_numpy() == pytest.approx(expected, rel=2e-3)
    assert inf.coef.to_numpy() == pytest.approx(zinb.beta.to_numpy())  # los coeficientes del ZINB
    assert inf.n_clusters == 25


def test_nb_without_cluster_is_the_model_based_se(counts, zinb):
    inf = nb_inference(zinb, counts, cluster=None)
    expected = np.sqrt(np.diag(_numeric_sandwich(counts, zinb, cluster=False)))[1:12]
    assert inf.se.to_numpy() == pytest.approx(expected, rel=2e-3)
    cluster_se = nb_inference(zinb, counts).se
    assert (cluster_se / inf.se).mean() > 1.1  # hay estructura por comuna en los datos simulados


# ------------------------------------------------------------------ sandwich del ZINB completo
def test_zinb_loglike_and_scores_match_statsmodels(counts_inflated, zinb_inflated):
    """Scores y log-verosimilitud analíticos contra `statsmodels` (con π = 0,25, regular)."""
    y, x = zinb_design(counts_inflated)
    model = zinb_inflated.model
    params = zinb_inflated.params.loc[list(PARAM_ORDER)].to_numpy() * np.array(
        [1.2] + [0.9] * 12 + [1.1]
    )  # un punto que NO es el óptimo, para que los scores no sean ≈ 0
    assert zinb_loglike(y, x, params) == pytest.approx(model.loglike(params), rel=1e-9)
    numeric = approx_fprime(params, model.loglikeobs, centered=True)
    assert zinb_scores(y, x, params) == pytest.approx(numeric, rel=1e-5, abs=1e-6)


def test_zinb_scores_vanish_at_the_optimum(counts_inflated, zinb_inflated):
    y, x = zinb_design(counts_inflated)
    scores = zinb_scores(y, x, zinb_inflated.params.loc[list(PARAM_ORDER)].to_numpy())
    assert zinb_inflated.pi == pytest.approx(0.25, abs=0.05)
    assert np.abs(scores.sum(axis=0)).max() / len(y) < 1e-3


def test_zinb_information_matches_the_numerical_hessian(counts_inflated, zinb_inflated):
    y, x = zinb_design(counts_inflated)
    params = zinb_inflated.params.loc[list(PARAM_ORDER)].to_numpy()
    info = zinb_information(y, x, params)
    numeric = -approx_hess(params, zinb_inflated.model.loglike)
    assert info == pytest.approx(numeric, rel=1e-3, abs=1e-2)
    assert np.allclose(info, info.T)


def test_scaled_inverse_equals_the_plain_inverse_when_well_conditioned():
    rng = np.random.default_rng(5)
    a = rng.normal(size=(6, 6))
    info = a @ a.T + 6 * np.eye(6)
    assert _scaled_inverse(info) == pytest.approx(np.linalg.inv(info), rel=1e-9)
    # y no pierde precisión cuando una dirección tiene información ~1e-12 veces menor
    scale = np.diag([1e-6] + [1.0] * 5)
    badly_scaled = scale @ info @ scale
    assert _scaled_inverse(badly_scaled) == pytest.approx(
        np.linalg.inv(scale) @ np.linalg.inv(info) @ np.linalg.inv(scale), rel=1e-6
    )


def _numeric_zinb_sandwich(counts, zinb, *, cluster):
    """Sandwich del ZINB completo con derivadas numéricas de `statsmodels` (independiente)."""
    model = zinb.model
    p = zinb.params.loc[list(PARAM_ORDER)].to_numpy()
    scores = approx_fprime(p, model.loglikeobs, centered=True)
    bread = np.linalg.inv(-approx_hess(p, model.loglike))
    if not cluster:
        return bread
    n, k = scores.shape
    codes = pd.factorize(counts["comuna"])[0]
    g = codes.max() + 1
    sums = np.vstack([scores[codes == c].sum(0) for c in range(g)])
    return g / (g - 1) * (n - 1) / (n - k) * bread @ (sums.T @ sums) @ bread


def test_zinb_cluster_se_matches_an_independent_sandwich(counts_inflated, zinb_inflated):
    inf = zinb_inference(zinb_inflated, counts_inflated)
    expected = np.sqrt(
        np.diag(_numeric_zinb_sandwich(counts_inflated, zinb_inflated, cluster=True))
    )
    assert inf.se.to_numpy() == pytest.approx(expected[2:13], rel=5e-3)
    assert inf.coef.to_numpy() == pytest.approx(zinb_inflated.beta.to_numpy())
    assert inf.n_clusters == 25
    # sin cluster: la inversa de la información
    plain = zinb_inference(zinb_inflated, counts_inflated, cluster=None)
    expected_plain = np.sqrt(
        np.diag(_numeric_zinb_sandwich(counts_inflated, zinb_inflated, cluster=False))
    )
    assert plain.se.to_numpy() == pytest.approx(expected_plain[2:13], rel=5e-3)
    assert plain.n_clusters is None


def test_zinb_inference_accepts_a_parameter_series(counts_inflated, zinb_inflated):
    """Se puede evaluar en otros parámetros (p. ej. los de `pscl`) pasando la serie."""
    from_result = zinb_inference(zinb_inflated, counts_inflated)
    from_series = zinb_inference(zinb_inflated.params, counts_inflated)
    assert from_series.se.to_numpy() == pytest.approx(from_result.se.to_numpy())


def test_inference_table_has_both_zinb_methods(frame, counts, zinb):
    full = inference_table(frame, counts, zinb)
    nb = inference_table(frame, counts, zinb, zinb_method="nb")
    assert full["ols_k_se"].equals(nb["ols_k_se"])  # solo cambia la columna ZINB
    assert nb["zinb_se"].notna().sum() == 11
    with pytest.raises(ValueError, match="zinb_method"):
        inference_table(frame, counts, zinb, zinb_method="otro")


# ------------------------------------------------------------------ dos partes y tabla completa
def test_two_part_se_is_the_authors_quadrature_approximation(frame):
    res = fit_two_part(frame)
    positive = frame[frame["median_distance"] > 0]
    inf = two_part_inference(res, positive)
    pr, m = res.pr_nonzero, res.mean_nonzero
    se_logit = res.logit.bse.drop("const")
    se_ols = ols_inference(res.ols, positive).se
    expected = np.sqrt((pr * (1 - pr) * se_logit * m) ** 2 + (se_ols * pr) ** 2)
    assert inf.se.to_numpy() == pytest.approx(expected.to_numpy())
    assert inf.coef.to_numpy() == pytest.approx(res.ame.to_numpy())
    # sin cluster, el SE del OLS es el clásico
    plain = two_part_inference(res, positive, cluster=None)
    assert plain.se.to_numpy() != pytest.approx(inf.se.to_numpy())
    assert plain.n_clusters is None


def test_inference_table_structure(frame, counts, zinb):
    table = inference_table(frame, counts, zinb)
    assert list(table["variable"]) == [v for v, _, _ in config.TABLE_ROWS]
    for col in COLUMNS:
        assert {f"{col}_se", f"{col}_p", f"{col}_sig"} <= set(table.columns)
        ref = table["variable"].isin(["edad_mayor_65", "gse_ab"])
        assert table.loc[ref, f"{col}_p"].isna().all()
        assert table.loc[~ref, f"{col}_p"].between(0, 1).all()
        assert (table[f"{col}_sig"] == table[f"{col}_p"].map(stars)).all()
    # el OLS de la tabla usa el mismo SE que `ols_inference`
    direct = ols_inference(fit_ols(frame), frame).se
    shown = table.set_index("variable")["ols_k_se"].drop(["edad_mayor_65", "gse_ab"])
    assert shown.to_numpy() == pytest.approx(direct.loc[shown.index].to_numpy())
    # sin cluster también se puede calcular
    assert inference_table(frame, counts, zinb, cluster=None)["ols_k_p"].notna().sum() == 11


# ------------------------------------------------------------------ estrellas
def test_stars_use_the_authors_strict_thresholds():
    cases = {0.0005: "***", 0.001: "**", 0.0099: "**", 0.01: "*", 0.049: "*", 0.05: ".",
             0.0999: ".", 0.1: "", 0.7: "", 1.0: ""}  # fmt: skip
    for p, expected in cases.items():
        assert stars(p) == expected, p
    assert stars(float("nan")) == ""


def test_nearest_threshold_is_in_log_scale():
    assert nearest_threshold(0.0004) == 0.001
    assert nearest_threshold(0.04) == 0.05
    assert nearest_threshold(0.2) == 0.1
    assert nearest_threshold(0.0) == 0.001  # p = 0 no rompe el logaritmo


def test_compare_stars_reports_every_non_reference_cell():
    variables = [v for v, _, _ in config.TABLE_ROWS]
    ref = pd.DataFrame({"variable": variables})
    comp = pd.DataFrame({"variable": variables})
    for col in COLUMNS:
        ref[f"{col}_sig"] = "*"
        comp[f"{col}_sig"] = "*"
        comp[f"{col}_p"] = 0.03
    comp.loc[comp["variable"] == "gse_c1b", "zinb_sig"] = "**"  # una discrepancia
    report = compare_stars(comp, ref)
    assert len(report) == 11 * 4  # sin las dos categorías de referencia
    bad = report[~report["ok"]]
    assert bad[["variable", "column", "computed", "paper"]].values.tolist() == [
        ["gse_c1b", "zinb", "**", "*"]
    ]
    assert regressors(_clustered_frame()).shape[1] == 11  # sanity del marco sintético
    assert sm.add_constant(regressors(_clustered_frame())).shape[1] == 12


def test_stars_summary_counts_matches_per_column():
    from lastmile_exposure.validation.paper_tables import stars_summary

    report = pd.DataFrame(
        {
            "variable": ["a", "b"] * 4,
            "column": ["zinb"] * 2 + ["ols_k"] * 2 + ["ols_kpos"] * 2 + ["ols_logk"] * 2,
            "ok": [True, False, True, True, False, False, True, False],
        }
    )
    summary = stars_summary(report)
    assert summary["matches"].to_dict() == {"zinb": 1, "ols_k": 2, "ols_kpos": 0, "ols_logk": 1}
    assert (summary["cells"] == 2).all()


# ------------------------------------------------------------- OBSERVATION (cluster NULL de R)
def test_observation_cluster_helpers():
    from lastmile_exposure.inference.cluster import OBSERVATION, cluster_groups, count_clusters

    df = pd.DataFrame({"comuna": ["a", "a", "b"], "x": [1, 2, 3]})
    assert cluster_groups(df, OBSERVATION).tolist() == [0, 1, 2]
    assert cluster_groups(df, "comuna").tolist() == ["a", "a", "b"]
    assert count_clusters(df, OBSERVATION) == 3
    assert count_clusters(df, "comuna") == 2


def test_observation_cluster_is_the_hc1_robust_se_for_ols(frame):
    """Cada fila como su cluster = errores robustos HC1 (sin agrupar), no el cluster por comuna."""
    from lastmile_exposure.inference.cluster import OBSERVATION

    res = fit_ols(frame)
    inf = ols_inference(res, frame, cluster=OBSERVATION)
    hc1 = res.get_robustcov_results(cov_type="HC1")
    assert inf.se.to_numpy() == pytest.approx(hc1.bse[1:], rel=1e-9)
    assert inf.n_clusters == len(frame)
    by_comuna = ols_inference(res, frame, cluster="comuna").se
    assert not np.allclose(inf.se, by_comuna, rtol=0.05)  # y NO es el de la comuna
    unique_ids = frame.assign(uid=np.arange(len(frame)))
    assert ols_inference(res, unique_ids, cluster="uid").se.to_numpy() == pytest.approx(
        inf.se.to_numpy()
    )


def test_observation_cluster_for_zinb_matches_an_independent_hc1_sandwich(
    counts_inflated, zinb_inflated
):
    from lastmile_exposure.inference.cluster import OBSERVATION

    inf = zinb_inference(zinb_inflated, counts_inflated, cluster=OBSERVATION)
    model = zinb_inflated.model
    p = zinb_inflated.params.loc[list(PARAM_ORDER)].to_numpy()
    scores = approx_fprime(p, model.loglikeobs, centered=True)
    bread = np.linalg.inv(-approx_hess(p, model.loglike))
    n, k = scores.shape
    expected = n / (n - k) * bread @ (scores.T @ scores) @ bread  # HC1 de la verosimilitud
    assert inf.se.to_numpy() == pytest.approx(np.sqrt(np.diag(expected))[2:13], rel=5e-3)
    assert inf.n_clusters == len(counts_inflated)


def test_two_part_and_nb_accept_observation(frame, counts, zinb):
    from lastmile_exposure.inference.cluster import OBSERVATION

    positive = frame[frame["median_distance"] > 0]
    tp = two_part_inference(fit_two_part(frame), positive, cluster=OBSERVATION)
    assert tp.n_clusters == len(positive) and tp.se.gt(0).all()
    assert nb_inference(zinb, counts, cluster=OBSERVATION).n_clusters == len(counts)


def test_zinb_cluster_can_differ_from_the_ols_cluster(frame, counts, zinb):
    """`zinb_cluster` cambia solo la columna ZINB; `authors_script` lo usa solo en el estático."""
    from lastmile_exposure.inference.cluster import OBSERVATION
    from lastmile_exposure.reporting.significance import authors_script_inference_table

    default = inference_table(frame, counts, zinb)
    mixed = inference_table(frame, counts, zinb, zinb_cluster=OBSERVATION)
    for col in ("ols_k", "ols_kpos", "ols_logk"):
        assert default[f"{col}_se"].equals(mixed[f"{col}_se"])
    assert not np.allclose(default["zinb_se"].dropna(), mixed["zinb_se"].dropna(), rtol=0.05)
    static = authors_script_inference_table(frame, counts, zinb, static=True)
    assert static["zinb_se"].equals(mixed["zinb_se"])
    dynamic = authors_script_inference_table(frame, counts, zinb, static=False)
    assert dynamic["zinb_se"].equals(default["zinb_se"])
