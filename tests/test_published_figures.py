"""Lo que se versiona en `docs/figures/` son solo figuras de COEFICIENTES, nunca datos por hexágono.

`docs/figures/` es la única carpeta de figuras que entra al repositorio (`outputs/` está ignorada).
Las Figs. 6, 8, 9 y 10 contienen los mismos números de las Tablas 4 y 5 del paper, que ya están
en `reference/paper_tables/`. Un mapa (Figs. 1 y 2) muestra valores por hexágono, derivados de
los datos confidenciales ("The data that has been used is confidential", paper p.19), y no debe
entrar aquí.
"""

from lastmile_exposure import config
from lastmile_exposure.figures.marginal_effects import FIGURES

# Figuras de coeficientes que se pueden publicar; cada una como PNG y PDF.
PUBLISHABLE = tuple(FIGURES)
ALLOWED = {f"{name}{suffix}" for name in PUBLISHABLE for suffix in (".png", ".pdf")} | {"README.md"}
MAGIC = {".png": b"\x89PNG\r\n\x1a\n", ".pdf": b"%PDF-"}


def _published_files():
    return sorted(p for p in config.FIGURES_DIR.glob("*") if p.is_file())


def test_published_folder_holds_only_coefficient_figures():
    unexpected = [p.name for p in _published_files() if p.name not in ALLOWED]
    assert not unexpected, (
        f"{unexpected} no está en la lista de figuras de coeficientes publicables: las figuras con "
        "valores por hexágono (mapas) se quedan en outputs/ porque salen de datos confidenciales"
    )


def test_published_files_are_real_png_and_pdf_files():
    for path in _published_files():
        if path.suffix in MAGIC:
            assert path.read_bytes()[: len(MAGIC[path.suffix])] == MAGIC[path.suffix], path.name


def test_no_figure_module_writes_maps_into_the_versioned_folder():
    """Solo `scripts/14_figures.py --publish` escribe en `config.FIGURES_DIR`."""
    root = config.ROOT
    offenders = [
        str(path.relative_to(root))
        for path in [*root.glob("src/**/*.py"), *root.glob("scripts/*.py")]
        if "FIGURES_DIR" in path.read_text(encoding="utf-8")
        and path.name not in {"config.py", "14_figures.py"}
    ]
    assert not offenders, f"Estos archivos usan config.FIGURES_DIR: {offenders}"
