"""Pruebas sintéticas de `reporting.paper_format` (corren sin datos)."""

import numpy as np
import pandas as pd
import pytest

from lastmile_exposure import config
from lastmile_exposure.reporting.paper_format import (
    COLUMN_TITLES,
    STARS_MARK,
    VALUE_MARK,
    agreement,
    format_cell,
    format_value,
    side_by_side,
    to_markdown,
)
from lastmile_exposure.reporting.significance import COLUMNS

REFERENCE_ROWS = ("edad_mayor_65", "gse_ab")


def _tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """`values`, `inference` y `reference` idénticos entre sí (todo coincide)."""
    variables = [v for v, _, _ in config.TABLE_ROWS]
    base = pd.DataFrame(
        {
            "variable": variables,
            "label": [lab for _, lab, _ in config.TABLE_ROWS],
            "group": [g for _, _, g in config.TABLE_ROWS],
        }
    )
    values, reference = base.copy(), base.copy()
    inference = pd.DataFrame({"variable": variables})
    for i, col in enumerate(COLUMNS):
        number = np.arange(len(variables)) * 1.5 + i
        number[[variables.index(v) for v in REFERENCE_ROWS]] = 0.0
        values[col] = number
        reference[col] = number
        is_reference = pd.Series(np.isin(variables, REFERENCE_ROWS))
        reference[f"{col}_sig"] = np.where(is_reference, "", "**")
        # como sale de un CSV: las estrellas vacías son NaN
        inference[f"{col}_sig"] = pd.Series("**", index=inference.index).mask(is_reference)
        inference[f"{col}_p"] = pd.Series(0.005, index=inference.index).mask(is_reference)
    return values, inference, reference


def test_format_value_drops_trailing_zeros_like_the_paper():
    assert format_value(0.313) == "0.313"
    assert format_value(-0.3130) == "-0.313"
    assert format_value(1446.0004) == "1446.0004"
    assert format_value(260.8360) == "260.836"
    assert format_value(12.0) == "12"
    assert format_value(0.0) == "0"
    assert format_value(-0.0) == "0"
    assert format_value(-0.00001) == "0"


def test_format_cell_appends_stars_and_ignores_missing():
    assert format_cell(3.5569, "***") == "3.5569***"
    assert format_cell(-0.0038, "") == "-0.0038"
    assert format_cell(-0.0038, np.nan) == "-0.0038"
    assert format_cell(90.6926, ".") == "90.6926."


def test_side_by_side_when_everything_agrees():
    values, inference, reference = _tables()
    table = side_by_side(values, inference, reference)
    assert list(table["variable"]) == [v for v, _, _ in config.TABLE_ROWS]
    for col in COLUMNS:
        assert table[f"{col}_value_ok"].all()
        assert table[f"{col}_stars_ok"].all()
        assert (table[f"{col}_replica"] == table[f"{col}_paper"]).all()
    # la categoría de referencia queda en "0" sin estrellas, aun con NaN en el CSV de inferencia
    assert table.loc[table["variable"] == "gse_ab", "zinb_replica"].item() == "0"


def test_side_by_side_flags_a_star_difference_but_not_a_value_difference():
    values, inference, reference = _tables()
    inference.loc[inference["variable"] == "gse_c1b", "ols_k_sig"] = "*"
    table = side_by_side(values, inference, reference)
    row = table[table["variable"] == "gse_c1b"].iloc[0]
    assert row["ols_k_value_ok"] and not row["ols_k_stars_ok"]
    assert row["zinb_stars_ok"]
    summary = agreement(table).set_index("column")
    assert summary.loc["ols_k", "stars_ok"] == 10 and summary.loc["ols_k", "stars"] == 11
    assert summary.loc["ols_k", "values_ok"] == 13 and summary.loc["ols_k", "values"] == 13


def test_side_by_side_flags_a_value_difference_beyond_the_last_printed_digit():
    values, inference, reference = _tables()
    values.loc[values["variable"] == "gse_c2", "zinb"] += 0.0001  # una unidad: redondeo
    values.loc[values["variable"] == "gse_c3", "zinb"] += 0.0003  # tres unidades: discrepancia
    table = side_by_side(values, inference, reference)
    flags = table.set_index("variable")["zinb_value_ok"]
    assert flags["gse_c2"] and not flags["gse_c3"]
    assert agreement(table).set_index("column").loc["zinb", "values_ok"] == 12


def test_markdown_marks_differences_and_reports_totals():
    values, inference, reference = _tables()
    values.loc[values["variable"] == "gse_c3", "zinb"] += 0.01
    inference.loc[inference["variable"] == "gse_c1a", "ols_logk_sig"] = ""
    table = side_by_side(values, inference, reference)
    text = to_markdown(table, "Tabla de prueba", "paper_text")
    assert text.startswith("# Tabla de prueba")
    for col in COLUMNS:
        assert f"{COLUMN_TITLES[col]} réplica" in text
        assert f"{COLUMN_TITLES[col]} paper" in text
    assert VALUE_MARK in text.split("| Columna")[0].split("C3")[1].split("\n")[0]
    c1a_line = [line for line in text.splitlines() if line.startswith("| C1a")][0]
    assert STARS_MARK in c1a_line
    assert "| **Total** | 51/52 | 43/44 |" in text


def test_markdown_rejects_an_unknown_star_variant():
    values, inference, reference = _tables()
    table = side_by_side(values, inference, reference)
    with pytest.raises(KeyError):
        to_markdown(table, "x", "otra_variante")
