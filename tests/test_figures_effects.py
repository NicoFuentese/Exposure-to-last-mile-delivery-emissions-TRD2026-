"""Figs. 6, 8, 9 y 10: datos, eje doble y dibujo (Fase 7). No necesitan los datos confidenciales.

Los puntos se comparan con las Tablas 4 y 5 impresas (`reference/paper_tables/`), que sí se
versionan.
"""

import numpy as np
import pytest
from matplotlib.figure import Figure

from lastmile_exposure.figures.marginal_effects import (
    AGE_ORDER,
    BLUE_LABEL,
    FIGURES,
    RED_LABEL,
    SEG_ORDER,
    dual_axis_scaling,
    figure_data,
    plot_effects,
    save_figure,
)
from lastmile_exposure.validation.paper_tables import load_table4, load_table5

TABLES = {"dynamic": load_table4, "static": load_table5}


@pytest.fixture(scope="module")
def paper():
    return {tag: load() for tag, load in TABLES.items()}


# ------------------------------------------------------------------ datos
@pytest.mark.parametrize(("name", "spec"), list(FIGURES.items()), ids=list(FIGURES))
def test_figure_data_follow_the_authors_order_and_the_printed_tables(paper, name, spec):
    tag, group = spec
    data = figure_data(paper[tag], group)
    order = SEG_ORDER if group == "seg" else AGE_ORDER
    assert data["label"].tolist() == list(order)
    indexed = paper[tag].set_index("label")
    for label, zinb, ols in zip(data["label"], data["zinb"], data["ols_kpos"], strict=True):
        assert zinb == indexed.loc[label, "zinb"] and ols == indexed.loc[label, "ols_kpos"]
    reference = "AB" if group == "seg" else "65+"
    row = data[data["label"] == reference].iloc[0]
    assert row["zinb"] == 0 and row["ols_kpos"] == 0


def test_figure_6_points_are_the_ones_printed_in_table_4(paper):
    data = figure_data(paper["dynamic"], "seg").set_index("label")
    assert data.loc["C1b", "zinb"] == pytest.approx(2.6735)
    assert data.loc["C1b", "ols_kpos"] == pytest.approx(388.3212)  # el máximo rojo
    assert data.loc["C1a", "zinb"] == pytest.approx(2.8017)  # el máximo azul
    assert data.loc["D+E", "ols_kpos"] == pytest.approx(-88.3825)  # el mínimo rojo


def test_figure_data_rejects_unknown_group_missing_labels_and_empty_cells(paper):
    with pytest.raises(ValueError, match="group"):
        figure_data(paper["dynamic"], "sex")
    with pytest.raises(KeyError, match="C1b"):
        figure_data(paper["dynamic"][paper["dynamic"]["label"] != "C1b"], "seg")
    broken = paper["dynamic"].copy()
    broken.loc[broken["label"] == "C2", "zinb"] = np.nan
    with pytest.raises(ValueError, match="vac"):
        figure_data(broken, "seg")


# ------------------------------------------------------------------ eje doble
def test_dual_axis_puts_the_range_of_the_red_series_on_the_range_of_the_blue_one():
    rng = np.random.default_rng(0)
    for _ in range(20):
        blue, red = rng.normal(0, 5, 6), rng.normal(0, 800, 6)
        scale, offset = dual_axis_scaling(blue, red)
        mapped = red * scale + offset
        assert mapped.min() == pytest.approx(blue.min()) and mapped.max() == pytest.approx(
            blue.max()
        )
        assert scale > 0  # el orden de la serie roja se conserva


def test_dual_axis_matches_the_formula_of_the_authors_code(paper):
    """`scale_factor = diff(range_nb) / diff(range_ols)` y `offset = min_nb − min_ols · scale`."""
    data = figure_data(paper["dynamic"], "seg")
    blue, red = data["zinb"].to_numpy(), data["ols_kpos"].to_numpy()
    scale, offset = dual_axis_scaling(blue, red)
    assert scale == pytest.approx((2.8017 - 0.0) / (388.3212 - (-88.3825)))
    assert offset == pytest.approx(0.0 - (-88.3825) * scale)


def test_dual_axis_rejects_a_constant_red_series():
    with pytest.raises(ValueError, match="constante"):
        dual_axis_scaling([0.0, 1.0, 2.0], [5.0, 5.0, 5.0])


# ------------------------------------------------------------------ dibujo
@pytest.mark.parametrize(("name", "spec"), list(FIGURES.items()), ids=list(FIGURES))
def test_plot_has_the_blue_and_red_series_with_the_authors_style(paper, name, spec):
    tag, group = spec
    fig = plot_effects(paper[tag], group)
    assert isinstance(fig, Figure)
    (ax,) = fig.axes
    blue_line, red_line = ax.lines
    data = figure_data(paper[tag], group)
    scale, offset = dual_axis_scaling(data["zinb"], data["ols_kpos"])
    assert blue_line.get_ydata() == pytest.approx(data["zinb"].to_numpy())
    assert red_line.get_ydata() == pytest.approx(data["ols_kpos"].to_numpy() * scale + offset)
    assert (blue_line.get_color(), blue_line.get_marker(), blue_line.get_linestyle()) == (
        "blue",
        "o",
        "-",
    )
    assert (red_line.get_color(), red_line.get_marker(), red_line.get_linestyle()) == (
        "red",
        "^",
        "--",
    )
    assert [t.get_text() for t in ax.get_xticklabels()] == data["label"].tolist()
    assert ax.get_ylabel() == BLUE_LABEL
    (secondary,) = ax.child_axes
    assert secondary.yaxis.label.get_text() == RED_LABEL


def test_right_axis_is_the_inverse_rescaling_of_the_left_one(paper):
    """Un punto rojo dibujado a la altura y se lee en el eje derecho como su valor en metros."""
    fig = plot_effects(paper["dynamic"], "seg")
    fig.canvas.draw()
    (ax,) = fig.axes
    (secondary,) = ax.child_axes
    data = figure_data(paper["dynamic"], "seg")
    scale, offset = dual_axis_scaling(data["zinb"], data["ols_kpos"])
    low, high = ax.get_ylim()
    assert secondary.get_ylim() == pytest.approx(((low - offset) / scale, (high - offset) / scale))


def test_title_is_optional_and_the_figure_renders_to_png_and_pdf(paper, tmp_path):
    assert plot_effects(paper["static"], "age").axes[0].get_title() == ""
    titled = plot_effects(paper["static"], "age", title="Marginal Effects by Age Group")
    assert titled.axes[0].get_title() == "Marginal Effects by Age Group"
    png, pdf = save_figure(titled, tmp_path / "sub" / "fig10", dpi=60)
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert pdf.read_bytes()[:5] == b"%PDF-"
