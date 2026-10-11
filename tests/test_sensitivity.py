"""Comparación de versiones de las Tablas 4 y 5 y chequeo de conclusiones (Fase 5).

Usa solo las cifras publicadas (`reference/paper_tables/`), que sí se versionan: no necesita los
datos confidenciales.
"""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.reporting.sensitivity import (
    COLUMNS,
    compare_tables,
    comparison_summary,
    results_table,
    robustness_checks,
)
from lastmile_exposure.validation.paper_tables import load_table4, load_table5


@pytest.fixture
def dynamic():
    return load_table4()


@pytest.fixture
def static():
    return load_table5()


def _set(table, variable, column, value=None, stars=None):
    out = table.copy()
    row = out["variable"] == variable
    if value is not None:
        out.loc[row, column] = value
    if stars is not None:
        out.loc[row, f"{column}_sig"] = stars
    return out


def _holds(dynamic, static):
    return robustness_checks(dynamic, static).set_index("check")["holds"].to_dict()


# ------------------------------------------------------------------ conclusiones del paper
def test_the_four_conclusions_hold_in_the_published_tables(dynamic, static):
    """Las definiciones deben valer en las propias tablas del paper (si no, están mal puestas)."""
    checks = robustness_checks(dynamic, static)
    assert list(checks["check"]) == ["gse_inverted_u", "age_peak_25_34", "sex", "c1b_flip"]
    assert checks["holds"].all()
    assert checks["detail"].str.len().gt(0).all()


@pytest.mark.parametrize(
    ("check", "change"),
    [
        ("gse_inverted_u", lambda d, s: (_set(d, "gse_de", "zinb", 3.0), s)),  # D+E sobre C3
        ("gse_inverted_u", lambda d, s: (_set(d, "gse_c3", "ols_kpos", -5.0), s)),  # C3 negativo
        ("age_peak_25_34", lambda d, s: (_set(d, "edad_35_44", "zinb", 20.0), s)),
        ("age_peak_25_34", lambda d, s: (_set(d, "edad_25_34", "ols_kpos", -1.0), s)),
        ("sex", lambda d, s: (d, _set(s, "genero_masc", "zinb", 1.0))),  # no se invierte
        ("sex", lambda d, s: (_set(d, "genero_masc", "zinb", stars=""), s)),  # no significativo
        ("sex", lambda d, s: (_set(d, "genero_masc", "zinb", -1.0), s)),  # signo opuesto
        ("c1b_flip", lambda d, s: (d, _set(s, "gse_c1b", "zinb", 1.0))),
        ("c1b_flip", lambda d, s: (_set(d, "gse_c1b", "zinb", -1.0), s)),
    ],
)
def test_each_conclusion_fails_when_its_condition_is_broken(dynamic, static, check, change):
    broken = _holds(*change(dynamic, static))
    assert broken[check] is False
    assert sum(not v for v in broken.values()) >= 1  # y no se cae por casualidad todo lo demás
    assert _holds(dynamic, static)[check] is True  # el original sí la cumplía


def test_a_marginally_significant_dot_does_not_count_as_significant(dynamic, static):
    assert _holds(_set(dynamic, "genero_masc", "zinb", stars="."), static)["sex"] is False
    assert _holds(_set(dynamic, "genero_masc", "zinb", stars="*"), static)["sex"] is True


# ------------------------------------------------------------------ comparación
def test_comparing_a_table_with_itself_changes_nothing(dynamic):
    comparison = compare_tables(dynamic, dynamic)
    assert len(comparison) == 4 * 11  # 11 variables no referenciales × 4 columnas
    assert set(comparison["variable"]).isdisjoint({"edad_mayor_65", "gse_ab"})
    assert (comparison["diff"] == 0).all() and comparison["same_sign"].all()
    assert (comparison["level_change"] == 0).all()
    assert not comparison["lost_significance"].any() and not comparison["gained_significance"].any()
    summary = comparison_summary(comparison)
    assert list(summary.index) == list(COLUMNS)
    assert summary[["sign_changes", "star_changes"]].to_numpy().sum() == 0
    assert (summary["median_abs_rel_change"] == 0).all()


def test_compare_tables_flags_sign_magnitude_and_star_changes(dynamic):
    alt = _set(dynamic, "gse_c1a", "zinb", -1.4009, stars="")  # 2,8017*** → −1,4009 sin estrellas
    alt = _set(alt, "genero_masc", "ols_k", 2 * 90.6926)  # misma estrella, doble
    alt = _set(alt, "gse_c3", "ols_kpos", 124.7486, stars="***")  # gana nivel (era ***: igual)
    alt = _set(alt, "edad_55_64", "ols_kpos", 12.0917, stars="**")  # sin estrellas → **
    comparison = compare_tables(dynamic, alt).set_index(["variable", "column"])

    c1a = comparison.loc[("gse_c1a", "zinb")]
    assert c1a["diff"] == pytest.approx(-1.4009 - 2.8017)
    assert c1a["rel_change"] == pytest.approx(-1.4009 / 2.8017 - 1)
    assert not c1a["same_sign"] and c1a["level_change"] == -4 and c1a["lost_significance"]

    male = comparison.loc[("genero_masc", "ols_k")]
    assert male["rel_change"] == pytest.approx(1.0) and male["same_sign"]
    assert male["level_change"] == 0

    assert comparison.loc[("gse_c3", "ols_kpos"), "level_change"] == 0
    gained = comparison.loc[("edad_55_64", "ols_kpos")]
    assert gained["level_change"] == 3 and gained["gained_significance"]

    summary = comparison_summary(comparison.reset_index())
    assert summary.loc["zinb", "sign_changes"] == 1 and summary.loc["zinb", "star_changes"] == 1
    assert summary.loc["zinb", "lost_significance"] == 1
    assert summary.loc["ols_kpos", "gained_significance"] == 1
    assert summary.loc["ols_k", "star_changes"] == 0


def test_rel_change_is_nan_when_the_base_is_zero(dynamic):
    base = _set(dynamic, "gse_c2", "ols_k", 0.0)
    comparison = compare_tables(base, dynamic).set_index(["variable", "column"])
    assert np.isnan(comparison.loc[("gse_c2", "ols_k"), "rel_change"])
    assert not np.isnan(comparison.loc[("gse_c1a", "ols_k"), "rel_change"])


# ------------------------------------------------------------------ unión de efectos e inferencia
def test_results_table_joins_effects_with_p_values_and_stars():
    variables = [v for v, _, _ in config.TABLE_ROWS]
    effects = pd.DataFrame(
        {
            "variable": variables,
            "label": [lab for _, lab, _ in config.TABLE_ROWS],
            "group": [g for _, _, g in config.TABLE_ROWS],
            **{c: np.arange(len(variables), dtype=float) for c in COLUMNS},
        }
    )
    inference = pd.DataFrame({"variable": variables[::-1]})  # en otro orden: debe unir por nombre
    for col in COLUMNS:
        inference[f"{col}_p"] = np.linspace(0.0, 0.2, len(variables))
        inference[f"{col}_sig"] = ["***"] * (len(variables) - 1) + [""]
    out = results_table(effects, inference)
    assert out["variable"].tolist() == variables
    assert out.loc[out["variable"] == variables[-1], "zinb_sig"].iloc[0] == "***"
    assert out.loc[out["variable"] == variables[0], "zinb_sig"].iloc[0] == ""
    assert {f"{c}_{s}" for c in COLUMNS for s in ("p", "sig")} <= set(out.columns)


# ------------------------------------------------------------------ una versión (sintético)
def _synthetic_frames(structural_zeros: float, seed=0, n_comunas=30, per_comuna=100):
    """Conteos NB (con ceros estructurales opcionales) y distancia con ~30 % de ceros."""
    rng = np.random.default_rng(seed)
    n = n_comunas * per_comuna
    k = len(config.REGRESSORS)
    comuna = np.repeat(np.arange(n_comunas), per_comuna)
    x = rng.random((n, k)) / 3
    beta = np.linspace(-1.0, 1.0, k)
    mu = np.exp(0.8 + x @ beta)
    y = rng.negative_binomial(2, 2 / (2 + mu))
    y = np.where(rng.random(n) < structural_zeros, 0, y)
    base = pd.DataFrame(x, columns=list(config.REGRESSORS)).assign(comuna=comuna)
    count_df = base.assign(vehicles=y.astype(float))
    distance = 100 * (x @ beta + 1.0 + rng.normal(0, 0.8, n))
    distance_df = base.assign(median_distance=np.clip(distance, 0.0, None))
    return count_df, distance_df


def test_estimate_version_on_a_pure_negative_binomial_sits_on_the_boundary():
    from lastmile_exposure.reporting.sensitivity import estimate_version

    # Con NB pura el máximo de la muestra cae en π = 0 solo en ~la mitad de los casos (H29); con
    # la semilla 1 (determinista) cae en la frontera.
    count_df, distance_df = _synthetic_frames(structural_zeros=0.0, seed=1)
    version = estimate_version(count_df, distance_df, static=False)
    assert list(version.tables) == ["paper_text"]
    table = version.tables["paper_text"]
    assert table["variable"].tolist() == [v for v, _, _ in config.TABLE_ROWS]
    assert {f"{c}_sig" for c in COLUMNS} <= set(table.columns)
    assert version.fit["boundary"] is True and version.fit["pi"] < 1e-12
    assert version.fit["n_rows"] == len(count_df)
    # con π = 0 la fórmula de los autores y la Ec. (4) coinciden
    assert version.fit["max_abs_authors_minus_eq4"] < 1e-9
    assert version.zinb_authors.tolist() == pytest.approx(table["zinb"].tolist())


def test_estimate_version_uses_eq4_and_keeps_the_authors_formula_aside_when_pi_is_positive():
    from lastmile_exposure.reporting.sensitivity import estimate_version

    count_df, distance_df = _synthetic_frames(structural_zeros=0.3, seed=1)
    version = estimate_version(count_df, distance_df, static=False)
    pi = version.fit["pi"]
    assert version.fit["boundary"] is False and 0.1 < pi < 0.5
    eq4 = version.tables["paper_text"].set_index("variable")["zinb"]
    authors = version.zinb_authors
    # authors = eq4 · (1 − π): el factor (1 − π) se aplica dos veces en el código de los autores
    assert authors.to_numpy() == pytest.approx((eq4 * (1 - pi)).to_numpy(), abs=1e-9)
    assert version.fit["max_abs_authors_minus_eq4"] > 0.01


def test_static_version_adds_the_authors_script_variant_with_an_unclustered_zinb():
    from lastmile_exposure.reporting.sensitivity import estimate_version

    count_df, distance_df = _synthetic_frames(structural_zeros=0.0, seed=2)
    version = estimate_version(count_df, distance_df, static=True)
    assert list(version.tables) == ["paper_text", "authors_script"]
    a, b = version.tables["paper_text"], version.tables["authors_script"]
    pd.testing.assert_frame_equal(
        a.drop(columns=[c for c in a.columns if c.startswith("zinb_")]),
        b.drop(columns=[c for c in b.columns if c.startswith("zinb_")]),
    )  # los OLS no cambian entre variantes
    assert a["zinb"].tolist() == b["zinb"].tolist()  # tampoco el efecto, solo el error estándar
    assert not np.allclose(a["zinb_p"].dropna(), b["zinb_p"].dropna())
