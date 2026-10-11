"""Fig. 7: factores derivados de las barras impresas y dibujo (Fase 7, H36).

Usa solo cifras publicadas (`reference/paper_tables/`): no necesita los datos confidenciales.
"""

import numpy as np
import pandas as pd
import pytest
from matplotlib.figure import Figure

from lastmile_exposure.figures.emissions import FIG7_NAME, plot_emissions
from lastmile_exposure.figures.marginal_effects import SEG_ORDER, figure_data
from lastmile_exposure.reporting.emissions import (
    Factor,
    emission_factors,
    emission_grams,
    implied_factor,
)
from lastmile_exposure.validation.paper_tables import load_fig7_bars, load_table4


@pytest.fixture(scope="module")
def printed_effects():
    return figure_data(load_table4(), "seg").set_index("label")["ols_kpos"]


@pytest.fixture(scope="module")
def bars():
    return load_fig7_bars()


# ------------------------------------------------------------------ factor
def test_implied_factor_recovers_a_known_constant_from_rounded_bars():
    effects = pd.Series({"a": -90.0, "b": 120.0, "c": 400.0, "ref": 0.0})
    k = 0.1824
    printed = (k * effects).round(1)
    factor = implied_factor(effects, printed)
    assert isinstance(factor, Factor) and factor.consistent
    assert factor.low <= k <= factor.high
    assert factor.value == pytest.approx(k, abs=(factor.high - factor.low))


def test_implied_factor_is_inconsistent_when_no_single_constant_fits():
    effects = pd.Series({"a": 100.0, "b": 200.0})
    factor = implied_factor(effects, pd.Series({"a": 10.0, "b": 50.0}))  # 0,1 g/m frente a 0,25
    assert not factor.consistent


def test_the_reference_category_must_print_zero_and_needs_one_nonzero_effect():
    with pytest.raises(ValueError, match="efecto 0"):
        implied_factor(pd.Series({"AB": 0.0, "C1b": 400.0}), pd.Series({"AB": 1.0, "C1b": 70.8}))
    with pytest.raises(ValueError, match="Ninguna categoría"):
        implied_factor(pd.Series({"AB": 0.0}), pd.Series({"AB": 0.0}))


# ------------------------------------------------------------------ las barras impresas del paper
def test_fig7_bars_file_matches_what_the_paper_prints_in_its_text(bars):
    """Las 12 etiquetas leídas de la figura; C1b (70,8 y 13,2) también está en el texto (p.13)."""
    assert bars["label"].tolist() == list(SEG_ORDER)
    assert bars.loc[bars["label"] == "C1b", ["nox_g", "pm_g"]].iloc[0].tolist() == [70.8, 13.2]
    assert bars.loc[bars["label"] == "AB", ["nox_g", "pm_g"]].iloc[0].tolist() == [0, 0]


def test_one_constant_per_pollutant_explains_all_twelve_printed_bars(printed_effects, bars):
    """H36: cada barra es una constante por el efecto OLS K>0 de la Tabla 4."""
    factors = emission_factors(printed_effects, bars)
    assert factors["nox"].consistent and factors["pm"].consistent
    assert factors["nox"].low == pytest.approx(0.18237, abs=2e-5)
    assert factors["nox"].high == pytest.approx(0.18245, abs=2e-5)
    assert factors["pm"].low == pytest.approx(0.03388, abs=2e-5)
    assert factors["pm"].high == pytest.approx(0.03394, abs=2e-5)
    grams = emission_grams(printed_effects, factors)
    assert grams[["nox_g", "pm_g"]].round(1).to_numpy() == pytest.approx(
        bars[["nox_g", "pm_g"]].to_numpy()
    )  # reproduce las 12 etiquetas


def test_the_factor_is_pinned_by_the_labels_not_only_by_the_text_anchor(printed_effects, bars):
    """El intervalo con las 12 etiquetas es más estrecho que el que da solo C1b (70,8 y 13,2)."""
    only_c1b = bars[bars["label"].isin(["C1b", "AB"])]
    wide = emission_factors(printed_effects, only_c1b)["nox"]
    narrow = emission_factors(printed_effects, bars)["nox"]
    assert narrow.high - narrow.low < (wide.high - wide.low) / 1.5
    assert wide.low <= narrow.low and narrow.high <= wide.high


def test_applying_the_factors_to_other_effects_just_rescales_them(printed_effects, bars):
    factors = emission_factors(printed_effects, bars)
    doubled = emission_grams(printed_effects * 2, factors)
    base = emission_grams(printed_effects, factors)
    assert doubled["nox_g"].to_numpy() == pytest.approx(2 * base["nox_g"].to_numpy())
    assert base["label"].tolist() == list(SEG_ORDER)


# ------------------------------------------------------------------ dibujo
@pytest.fixture(scope="module")
def fig(printed_effects, bars):
    grams = emission_grams(printed_effects, emission_factors(printed_effects, bars))
    return plot_emissions(grams), grams


def test_fig7_has_two_bar_series_with_the_printed_values(fig):
    figure, grams = fig
    assert isinstance(figure, Figure) and FIG7_NAME == "fig7_emissions_seg"
    (ax,) = figure.axes
    heights = [patch.get_height() for patch in ax.patches]
    assert heights[:6] == pytest.approx(grams["nox_g"].to_numpy())
    assert heights[6:] == pytest.approx(grams["pm_g"].to_numpy())
    assert [t.get_text() for t in ax.get_xticklabels()] == list(SEG_ORDER)
    assert ax.get_ylabel() == "Grams of Pollutant"
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["NOx", "PM"]


def test_fig7_value_labels_are_one_decimal_and_negatives_use_math_mode(fig):
    figure, _ = fig
    (ax,) = figure.axes
    texts = [t.get_text() for t in ax.texts]
    assert texts[:6] == ["$-16.1$", "22.8", "39.5", "70.8", "59.5", "0"]  # NOx
    assert texts[6:] == ["$-3$", "4.2", "7.3", "13.2", "11.1", "0"]  # PM


def test_fig7_renders_to_png(fig, tmp_path):
    figure, _ = fig
    path = tmp_path / "fig7.png"
    figure.savefig(path, dpi=50)
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert np.isfinite(path.stat().st_size)
