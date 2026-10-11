"""Lo que se versiona en `docs/figures/` es solo lo que está autorizado, y nada más.

`docs/figures/` es la única carpeta de figuras que entra al repositorio (`outputs/` está ignorada).
- Figs. 6, 8, 9 y 10: solo COEFICIENTES, los mismos números de las Tablas 4 y 5 del paper, que ya
  están en `reference/paper_tables/`. PNG y PDF. Igual la Fig. 7, que son esos coeficientes por una
  constante (gramos de NOx y PM derivados de las barras impresas, H36).
- Fig. 1 (mapa): muestra valores por hexágono derivados de los datos confidenciales ("The data that
  has been used is confidential", paper p.19). Se publica por decisión del usuario (2026-10-10),
  porque el paper publica la misma figura, pero SOLO como PNG de resolución moderada: el PDF
  vectorial guarda el color exacto de cada hexágono y no entra.
- Sustituto de la Fig. 2 (vehículos por hexágono; no son puntos GPS): igual que la Fig. 1, por
  decisión del usuario (2026-10-11), solo como PNG de resolución moderada.
Cualquier otra figura con valores por hexágono NO está en la lista.
"""

import struct

from lastmile_exposure import config
from lastmile_exposure.figures.emissions import FIG7_NAME
from lastmile_exposure.figures.maps import FIG1_NAME, FIG2_PROXY_NAME, PUBLISH_MAX_PIXELS
from lastmile_exposure.figures.marginal_effects import FIGURES

# Figs. 6, 8, 9 y 10 + Fig. 7 (coeficientes × una constante): PNG y PDF
COEFFICIENT_FIGURES = (*FIGURES, FIG7_NAME)
MAP_FIGURES = (FIG1_NAME, FIG2_PROXY_NAME)  # solo PNG, de resolución limitada
ALLOWED = (
    {f"{name}{suffix}" for name in COEFFICIENT_FIGURES for suffix in (".png", ".pdf")}
    | {f"{name}.png" for name in MAP_FIGURES}
    | {"README.md"}
)
MAGIC = {".png": b"\x89PNG\r\n\x1a\n", ".pdf": b"%PDF-"}
WRITES_TO_FIGURES_DIR = {"config.py", "14_figures.py", "15_maps.py"}


def _published_files():
    return sorted(p for p in config.FIGURES_DIR.glob("*") if p.is_file())


def test_published_folder_holds_only_authorized_figures():
    unexpected = [p.name for p in _published_files() if p.name not in ALLOWED]
    assert not unexpected, (
        f"{unexpected} no está autorizado en docs/figures/: solo van las figuras de coeficientes y "
        "los PNG de la Fig. 1 y del sustituto de la Fig. 2. Cualquier otra figura con valores por "
        "hexágono se queda en outputs/"
    )


def test_published_files_are_real_png_and_pdf_files():
    for path in _published_files():
        if path.suffix in MAGIC:
            assert path.read_bytes()[: len(MAGIC[path.suffix])] == MAGIC[path.suffix], path.name


def test_published_maps_are_png_with_limited_resolution():
    """El mapa versionado no puede ser más fino que el del paper (ancho máximo en píxeles)."""
    for name in MAP_FIGURES:
        vector = config.FIGURES_DIR / f"{name}.pdf"
        assert not vector.exists(), f"{vector.name} (vectorial) no se versiona"
        path = config.FIGURES_DIR / f"{name}.png"
        if path.exists():
            width, height = struct.unpack(">II", path.read_bytes()[16:24])  # cabecera IHDR
            assert width <= PUBLISH_MAX_PIXELS, (name, width)
            assert height <= PUBLISH_MAX_PIXELS * 1.2, (name, height)


def test_only_the_figure_scripts_write_into_the_versioned_folder():
    """Solo `14_figures.py` y `15_maps.py` (con `--publish`) escriben en `config.FIGURES_DIR`."""
    root = config.ROOT
    offenders = [
        str(path.relative_to(root))
        for path in [*root.glob("src/**/*.py"), *root.glob("scripts/*.py")]
        if "FIGURES_DIR" in path.read_text(encoding="utf-8")
        and path.name not in WRITES_TO_FIGURES_DIR
    ]
    assert not offenders, f"Estos archivos usan config.FIGURES_DIR: {offenders}"
