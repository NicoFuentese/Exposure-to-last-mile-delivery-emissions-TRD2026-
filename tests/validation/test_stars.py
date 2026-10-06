"""Estrellas de las Tablas 4 y 5 sobre `00_data`: cuántas coinciden con el paper según la variante.

Estas pruebas FIJAN el resultado documentado (AGENTS.md H25, H26 y D3): no todas las estrellas
publicadas se reproducen con ninguna variante. Si el método cambia, el recuento cambia y la
prueba avisa. No son un criterio de aceptación de la réplica sino un registro del estado.

Resultado (estrellas iguales de 11 por columna, `scripts/06_inference.py`):

| tabla / variante      | zinb | ols_k | ols_kpos | ols_logk | total |
|-----------------------|-----:|------:|---------:|---------:|------:|
| dinámico, paper_text  |    8 |     5 |        7 |        3 |    23 |
| dinámico, script      |    8 |     5 |        7 |        3 |    23 |
| dinámico, iid         |    5 |     5 |        9 |        8 |    27 |
| estático, paper_text  |    0 |     9 |       10 |        8 |    27 |
| estático, script      |   11 |     9 |       10 |        8 |    38 |
| estático, iid         |   11 |     1 |        3 |        3 |    18 |

`paper_text` = cluster por comuna en todo; `script` = como el script de los autores (ZINB estático
sin agrupar por un error de su código, H26); `iid` = sin cluster. Con `paper_text` y `script`
suman 50/88 y 61/88: el script reproduce más estrellas, pero porque copia un error.
"""

import pytest

from lastmile_exposure.reporting.significance import (
    authors_script_inference_table,
    inference_table,
)
from lastmile_exposure.validation.paper_tables import (
    compare_stars,
    load_table4,
    load_table5,
    stars_summary,
)

EXPECTED = {
    ("dynamic", "paper_text"): {"zinb": 8, "ols_k": 5, "ols_kpos": 7, "ols_logk": 3},
    ("dynamic", "authors_script"): {"zinb": 8, "ols_k": 5, "ols_kpos": 7, "ols_logk": 3},
    ("dynamic", "iid"): {"zinb": 5, "ols_k": 5, "ols_kpos": 9, "ols_logk": 8},
    ("static", "paper_text"): {"zinb": 0, "ols_k": 9, "ols_kpos": 10, "ols_logk": 8},
    ("static", "authors_script"): {"zinb": 11, "ols_k": 9, "ols_kpos": 10, "ols_logk": 8},
    ("static", "iid"): {"zinb": 11, "ols_k": 1, "ols_kpos": 3, "ols_logk": 3},
}
REFERENCES = {"dynamic": load_table4, "static": load_table5}


def _table(variant, static, frames, zinb):
    distance, counts = frames["distance"], frames["count"]
    if variant == "paper_text":
        return inference_table(distance, counts, zinb, cluster="comuna")
    if variant == "authors_script":
        return authors_script_inference_table(distance, counts, zinb, static=static)
    return inference_table(distance, counts, zinb, cluster=None)


@pytest.mark.slow
@pytest.mark.parametrize(("tag", "variant"), list(EXPECTED))
def test_star_agreement_with_the_paper_is_the_documented_one(
    model_frames, zinb_dynamic, zinb_static, tag, variant
):
    zinb = {"dynamic": zinb_dynamic, "static": zinb_static}[tag]
    table = _table(variant, tag == "static", model_frames[tag], zinb)
    report = compare_stars(table, REFERENCES[tag]())
    assert len(report) == 44  # 11 filas no referencia x 4 columnas
    assert stars_summary(report)["matches"].to_dict() == EXPECTED[(tag, variant)]


@pytest.mark.slow
def test_authors_script_reproduces_the_static_zinb_stars(model_frames, zinb_static):
    """H26: con el cluster NULL del script, las 11 estrellas del ZINB estático (todas `***`)."""
    table = _table("authors_script", True, model_frames["static"], zinb_static)
    report = compare_stars(table, load_table5())
    zinb = report[report["column"] == "zinb"]
    assert zinb["ok"].all() and (zinb["paper"] == "***").all()


@pytest.mark.slow
def test_dynamic_cluster_zinb_stars_differ_only_in_three_cells(model_frames, zinb_dynamic):
    """Con cluster, la columna ZINB dinámica solo falla en 35-44, C1b y C2."""
    table = _table("paper_text", False, model_frames["dynamic"], zinb_dynamic)
    report = compare_stars(table, load_table4())
    wrong = report[(report["column"] == "zinb") & ~report["ok"]]
    assert set(wrong["variable"]) == {"edad_35_44", "gse_c1b", "gse_c2"}
