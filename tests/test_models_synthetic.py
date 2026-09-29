"""Pruebas de los modelos y tablas con datos sintéticos (no necesitan los datos confidenciales)."""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.demographics.shares import add_gse_de, regressors
from lastmile_exposure.demographics.static import static_shares
from lastmile_exposure.models.marginal_effects import ols_marginal_effects, two_part_ame
from lastmile_exposure.models.ols import fit_ols
from lastmile_exposure.models.two_part import fit_two_part
from lastmile_exposure.reporting.table2 import table2


def _synthetic(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(rng.random((n, len(config.REGRESSORS))), columns=list(config.REGRESSORS))
    beta = np.arange(1, len(config.REGRESSORS) + 1, dtype=float)
    latent = df.to_numpy() @ beta + rng.normal(0, 5.0, n)
    df["median_distance"] = np.where(latent > np.median(latent) - 2, latent * 100, 0.0)
    return df, beta


def test_add_gse_de_and_regressors():
    df = pd.DataFrame({"gse_d": [0.3, 0.1], "gse_e": [0.2, 0.05]})
    out = add_gse_de(df)
    assert out["gse_de"].tolist() == pytest.approx([0.5, 0.15])
    assert "gse_de" not in df.columns  # no muta la entrada
    with pytest.raises(KeyError):
        regressors(df)


def test_static_shares_converts_percent_to_proportion():
    raw = pd.DataFrame(
        {"gse_ab": [4.0], "gse_c1a": [10.0], "gse_c1b": [10.0], "gse_c2": [15.0],
         "gse_c3": [30.0], "gse_d": [26.0], "gse_e": [5.0], "genero_masc": [0.5]}
    )  # fmt: skip
    out = static_shares(raw)
    assert out.loc[0, "gse_ab"] == pytest.approx(0.04)
    assert out.loc[0, "gse_de"] == pytest.approx(0.31)
    assert out.loc[0, "genero_masc"] == 0.5  # lo que ya es proporción no se toca


def test_ols_recovers_exact_linear_relationship():
    df, beta = _synthetic()
    df["median_distance"] = df[list(config.REGRESSORS)].to_numpy() @ beta + 7.0  # sin ruido
    params = fit_ols(df).params
    assert params["const"] == pytest.approx(7.0)
    assert ols_marginal_effects(params).to_numpy() == pytest.approx(beta)


def test_ols_log_positive_uses_only_positive_rows():
    df, _ = _synthetic()
    res = fit_ols(df, log_positive=True)
    assert int(res.nobs) == int((df["median_distance"] > 0).sum())


def test_two_part_ame_formula_limits():
    b = pd.Series({"a": 2.0, "b": -1.0})
    zero = pd.Series({"a": 0.0, "b": 0.0})
    assert two_part_ame(zero, b, pr_nonzero=0.7, mean_nonzero=100.0).tolist() == pytest.approx(
        [1.4, -0.7]
    )
    assert two_part_ame(b, zero, pr_nonzero=0.5, mean_nonzero=10.0).tolist() == pytest.approx(
        [5.0, -2.5]
    )


def test_two_part_invariants():
    """Con constante, el logit ajusta la frecuencia observada y el OLS la media de los positivos."""
    df, _ = _synthetic()
    res = fit_two_part(df)
    positive = df["median_distance"] > 0
    assert res.pr_nonzero == pytest.approx(positive.mean(), abs=1e-9)
    assert res.mean_nonzero == pytest.approx(df.loc[positive, "median_distance"].mean())
    assert list(res.ame.index) == list(config.REGRESSORS)


def test_table2_definitions_on_tiny_panel():
    panel = pd.DataFrame(
        {
            "poblacion_flotante": [100.0, 300.0, 0.0],
            "genero_masc": [0.5, 0.25, 0.0],
            "genero_fem": [0.5, 0.75, 0.0],
        }
    )
    for col in ("edad_menor_25", "edad_25_34", "edad_35_44", "edad_45_54", "edad_55_64",
                "edad_mayor_65", "gse_ab", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3",
                "gse_d", "gse_e"):  # fmt: skip
        panel[col] = 0.1
    t = table2(panel).set_index("variable")
    assert t.loc["Avg Population", "mean"] == pytest.approx(400 / 3)
    male_counts = np.array([50.0, 75.0, 0.0])
    assert t.loc["Male", "mean"] == pytest.approx(male_counts.mean())
    assert t.loc["Male", "std"] == pytest.approx(male_counts.std(ddof=1))
    assert t.loc["Male", "mean_pct"] == pytest.approx(100 * male_counts.mean() / (400 / 3))
    # Std (%) ponderada por población sobre filas con población > 0 (pesos 100 y 300)
    mu = np.average([0.5, 0.25], weights=[100, 300])
    expected = 100 * np.sqrt(np.average(([0.5, 0.25] - mu) ** 2, weights=[100, 300]))
    assert t.loc["Male", "std_pct"] == pytest.approx(expected)
    assert t["wasserstein"].isna().all()  # aún no implementado (D10)


def test_compare_columns_flags_missing_and_nan_cells():
    """La comparación nunca omite en silencio una celda que la réplica no calculó."""
    from lastmile_exposure.validation.paper_tables import compare_columns

    reference = pd.DataFrame({"variable": ["a", "b"], "x": [1.0, 2.0]})
    good = pd.DataFrame({"variable": ["a", "b"], "x": [1.00001, 2.0]})
    report = compare_columns(good, reference, {"x": 1e-4})
    assert len(report) == 2 and report["ok"].all()

    bad = pd.DataFrame({"variable": ["a", "b"], "x": [1.0, 2.5]})
    assert compare_columns(bad, reference, {"x": 1e-4})["ok"].tolist() == [True, False]

    nan = pd.DataFrame({"variable": ["a", "b"], "x": [1.0, float("nan")]})
    report = compare_columns(nan, reference, {"x": 1e-4})
    assert len(report) == 2 and report["ok"].tolist() == [True, False]  # NaN no pasa

    with pytest.raises(ValueError, match="faltan filas"):
        compare_columns(good.iloc[:1], reference, {"x": 1e-4})

    # Si el paper no reporta la celda (NaN), se omite
    ref_nan = pd.DataFrame({"variable": ["a", "b"], "x": [1.0, float("nan")]})
    assert len(compare_columns(nan, ref_nan, {"x": 1e-4})) == 1
