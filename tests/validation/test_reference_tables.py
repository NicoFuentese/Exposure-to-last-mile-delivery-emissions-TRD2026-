"""Las cifras publicadas de reference/paper_tables/ están completas y bien leídas.

Estas pruebas no validan la réplica todavía: validan que el objetivo contra el que se
comparará la réplica (Tablas 2 a 5 del paper) se cargó correctamente.
"""

import pandas as pd
import pytest

from lastmile_exposure import config

MODELS = ("zinb", "ols_k", "ols_kpos", "ols_logk")
STARS = {"", "*", "**", "***"}


def _read(name, keep_empty_as_text=True):
    # Tablas 4-5: las estrellas vacías deben quedar como "" (no NaN).
    # Tablas 2-3: las celdas vacías deben quedar como NaN para que las columnas sean numéricas.
    return pd.read_csv(config.REFERENCE_DIR / f"{name}.csv", keep_default_na=not keep_empty_as_text)


@pytest.mark.parametrize("name", ["table4_dynamic", "table5_static"])
def test_marginal_effects_tables_shape_and_references(name):
    df = _read(name)
    assert len(df) == 13
    keys = set(df["variable"])
    assert set(config.REGRESSORS) <= keys
    assert {"edad_mayor_65", "gse_ab"} <= keys
    refs = df[df["variable"].isin(["edad_mayor_65", "gse_ab"])]
    for m in MODELS:
        assert (refs[m] == 0).all()
        assert (refs[f"{m}_sig"] == "").all()
    for m in MODELS:
        assert set(df[f"{m}_sig"]) <= STARS


def test_table4_known_cells():
    df = _read("table4_dynamic").set_index("variable")
    assert df.loc["gse_c1b", "ols_kpos"] == pytest.approx(388.3212)
    assert df.loc["gse_c1b", "ols_kpos_sig"] == "***"
    assert df.loc["gse_c1a", "zinb"] == pytest.approx(2.8017)
    assert df.loc["gse_c1b", "zinb_sig"] == ""  # C1b no es significativo en el ZINB
    assert df.loc["edad_25_34", "ols_logk"] == pytest.approx(1.6696)


def test_table5_known_cells():
    df = _read("table5_static").set_index("variable")
    assert df.loc["gse_c1b", "zinb"] == pytest.approx(-14.2813)
    assert df.loc["genero_masc", "zinb"] == pytest.approx(-3.0814)
    assert df.loc["genero_masc", "ols_k"] == pytest.approx(-1288.2834)


def test_table2_consistency():
    df = _read("table2_floating_population", keep_empty_as_text=False).set_index("variable")
    total = df.loc["Avg Population", "mean"]
    assert total == pytest.approx(472.78)
    for group, members in {
        "sex": ["Male", "Female"],
        "seg": ["AB", "C1a", "C1b", "C2", "C3", "D", "E"],
    }.items():
        assert df.loc[members, "mean"].sum() == pytest.approx(total, abs=0.05), group
    assert df.loc["AB", "wasserstein"] == pytest.approx(1.33703)


def test_table3_values():
    df = _read("table3_vehicle_dataset", keep_empty_as_text=False).set_index("description")["value"]
    assert df["analysis_period_wednesdays"] == 41
    assert df["p90_time_between_pings_min"] == pytest.approx(5.45)
