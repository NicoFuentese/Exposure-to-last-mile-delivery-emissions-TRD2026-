"""Contraste con las Tablas 4 y 5 regeneradas por los autores (`00_out/reference_tables_42wed/`).

Los autores reconocieron (2026-10-09) que las estrellas impresas en el paper no salen del método
correcto (cluster por comuna sobre la base de 42 miércoles) y pidieron comparar contra estas tablas.
Se saltan si el paquete vigente o su carpeta de referencia no están.

Lo que fijan:
- Coeficientes: las columnas OLS del paper son idénticas a las de la referencia; la columna "ZINB"
  del paper es la columna NB de la referencia (no la ZINB de `pscl`, que se detiene antes del
  máximo; H23), y nuestro máximo (`fit_zinb_mle`) la reproduce a la precisión impresa.
- Estrellas: nuestras variantes reproducen las 88 de la referencia (44 por tabla); el paper, solo
  23/44 (dinámica) y 38/44 (estática). En la estática la referencia tiene el ZINB sin agrupar, así
  que la variante del script (error de los autores, H26) coincide y la de cluster por comuna no.
"""

import pytest

from lastmile_exposure import config
from lastmile_exposure.models.marginal_effects import zinb_marginal_effects
from lastmile_exposure.reporting.significance import (
    authors_script_inference_table,
    inference_table,
)
from lastmile_exposure.validation.paper_tables import (
    MARGINAL_TOLERANCE,
    STAR_COLUMNS,
    authors_reference_dir,
    compare_stars,
    load_authors_reference,
    load_table4,
    load_table5,
    stars_summary,
)

PAPER = {"dynamic": load_table4, "static": load_table5}
REFERENCE_ROWS = ("edad_mayor_65", "gse_ab")
PRINTED_DIFF = 2 * MARGINAL_TOLERANCE  # dos cifras redondeadas a 4 decimales pueden diferir 1e-4
MEAN_POSITIVE_DISTANCE = 490.52  # media de K̃>0: escala de la columna log dinámica de la referencia


@pytest.fixture(scope="module")
def reference(panel):
    if not authors_reference_dir().exists():
        pytest.skip("Faltan las tablas de referencia de los autores (reference_tables_42wed)")
    return {tag: load_authors_reference(tag) for tag in PAPER}


def _by_variable(table):
    return table.set_index("variable").drop(index=list(REFERENCE_ROWS))


@pytest.mark.parametrize("tag", ["dynamic", "static"])
def test_reference_tables_have_the_expected_shape(reference, tag):
    ref = reference[tag]
    assert len(ref) == 13
    assert set(ref["variable"]) == {v for v, _, _ in config.TABLE_ROWS}
    assert {"nb", "zinb", "ols_k", "ols_kpos", "ols_logk"} <= set(ref.columns)


@pytest.mark.parametrize("tag", ["dynamic", "static"])
def test_paper_ols_columns_are_the_references(reference, tag):
    paper, ref = _by_variable(PAPER[tag]()), _by_variable(reference[tag])
    for col in ("ols_k", "ols_kpos"):
        diff = (paper[col] - ref.loc[paper.index, col]).abs().max()
        assert diff <= MARGINAL_TOLERANCE, col


def test_static_log_column_is_the_same_and_the_dynamic_one_is_scaled(reference):
    """H9: la referencia dinámica trae el log como `coef × media(K̃>0)`; la estática, el crudo."""
    paper_s, ref_s = _by_variable(load_table5()), _by_variable(reference["static"])
    assert (paper_s["ols_logk"] - ref_s.loc[paper_s.index, "ols_logk"]).abs().max() <= (
        MARGINAL_TOLERANCE
    )
    paper_d, ref_d = _by_variable(load_table4()), _by_variable(reference["dynamic"])
    # los coeficientes muy chicos pierden cifras al escalar: se omiten
    big = paper_d[paper_d["ols_logk"].abs() > 0.15].index
    ratio = ref_d.loc[big, "ols_logk"] / paper_d.loc[big, "ols_logk"]
    assert ratio.to_numpy() == pytest.approx(MEAN_POSITIVE_DISTANCE, rel=1e-3)


@pytest.mark.parametrize("tag", ["dynamic", "static"])
def test_paper_zinb_column_is_the_references_nb_column_not_its_pscl_zinb(reference, tag):
    paper, ref = _by_variable(PAPER[tag]()), _by_variable(reference[tag])
    to_nb = (paper["zinb"] - ref.loc[paper.index, "nb"]).abs().max()
    to_pscl = (paper["zinb"] - ref.loc[paper.index, "zinb"]).abs().max()
    assert to_nb <= PRINTED_DIFF
    assert to_pscl > 10 * PRINTED_DIFF  # 0,0027 (T4) y 0,0038 (T5)


@pytest.mark.slow
@pytest.mark.parametrize("tag", ["dynamic", "static"])
def test_our_zinb_maximum_reproduces_the_references_nb_column(
    reference, zinb_dynamic, zinb_static, tag
):
    result = {"dynamic": zinb_dynamic, "static": zinb_static}[tag]
    assert result.boundary  # el máximo está en la frontera π = 0 (H29)
    ours = zinb_marginal_effects(result, "authors")
    ref = reference[tag].set_index("variable")["nb"]
    diff = (ours - ref.loc[ours.index]).abs().max()
    assert diff <= PRINTED_DIFF, diff


def _table(variant, static, frames, zinb):
    distance, counts = frames["distance"], frames["count"]
    if variant == "paper_text":
        return inference_table(distance, counts, zinb, cluster="comuna")
    return authors_script_inference_table(distance, counts, zinb, static=static)


@pytest.mark.slow
def test_dynamic_stars_match_the_reference_in_all_44_cells(reference, model_frames, zinb_dynamic):
    """Tabla 4: el cluster por comuna del paper reproduce las 44 estrellas de la referencia."""
    table = _table("paper_text", False, model_frames["dynamic"], zinb_dynamic)
    report = compare_stars(table, reference["dynamic"])
    assert len(report) == 44
    assert report["ok"].all(), report[~report["ok"]]


@pytest.mark.slow
def test_static_stars_match_the_reference_only_with_the_scripts_unclustered_zinb(
    reference, model_frames, zinb_static
):
    """Tabla 5: coinciden las 44 con la variante del script (ZINB sin agrupar, H26); con cluster
    por comuna en todo, el ZINB no coincide en ninguna celda y las otras 33 sí."""
    frames = model_frames["static"]
    script = compare_stars(_table("authors_script", True, frames, zinb_static), reference["static"])
    assert script["ok"].all(), script[~script["ok"]]
    text = compare_stars(_table("paper_text", True, frames, zinb_static), reference["static"])
    assert stars_summary(text)["matches"].to_dict() == {
        "zinb": 0,
        "ols_k": 11,
        "ols_kpos": 11,
        "ols_logk": 11,
    }


@pytest.mark.parametrize(("tag", "expected"), [("dynamic", 23), ("static", 38)])
def test_papers_printed_stars_do_not_match_the_reference(reference, tag, expected):
    """Los autores lo reconocen (Tabla 4); en la Tabla 5 coinciden 38 de 44."""
    paper, ref = _by_variable(PAPER[tag]()), _by_variable(reference[tag])
    matches = sum(
        int((paper[f"{col}_sig"] == ref.loc[paper.index, f"{col}_sig"]).sum())
        for col in STAR_COLUMNS
    )
    assert matches == expected
