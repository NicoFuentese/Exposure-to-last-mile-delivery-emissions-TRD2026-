"""Extrae las figuras del paper impreso a `figuras/FiguraN_paperOriginal.png`.

Las imágenes incrustadas (Figs. 2, 6, 8, 9 y 10) salen de `pdfimages`; la Fig. 1 y la Fig. 7 son
vectoriales y se recortan de la página renderizada a 300 dpi (coordenadas medidas a 150 dpi, x2).
Necesita `data/Basso2026TRD.pdf`, `pdfimages` y `pdftoppm` (vienen con MiKTeX) y Pillow.
Las imágenes son del paper (Elsevier): están en `.gitignore` y no se versionan.

Uso, desde la raíz del repositorio:
    .venv/Scripts/python.exe entregables/replica_vs_paper/extraer_figuras_paper.py
"""

import pathlib
import shutil
import subprocess
import tempfile

from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
PDF = HERE.parents[1] / "data" / "Basso2026TRD.pdf"
OUT = HERE / "figuras"

# Orden de `pdfimages -f 8 -l 16`: img-000 = Fig. 2 (p. 8); img-001 y -002 son diagramas
# (Figs. 3 y 5); img-003 a -006 = Figs. 6, 8, 9 y 10 (pp. 13 a 16).
EMBEDDED = {2: "img-000", 6: "img-003", 8: "img-004", 9: "img-005", 10: "img-006"}
# Recortes (página, caja en píxeles a 150 dpi).
CROPS = {1: (6, (170, 100, 960, 1050)), 7: (14, (320, 110, 810, 480))}


def main():
    if not PDF.exists():
        raise SystemExit(f"No está {PDF}")
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        subprocess.run(
            ["pdfimages", "-png", "-f", "8", "-l", "16", str(PDF), str(tmp / "img")], check=True
        )
        for fig, name in EMBEDDED.items():
            shutil.copy(tmp / f"{name}.png", OUT / f"Figura{fig}_paperOriginal.png")
        for fig, (page, box) in CROPS.items():
            prefix = tmp / f"p{page}"
            subprocess.run(
                [
                    "pdftoppm",
                    "-r",
                    "300",
                    "-png",
                    "-f",
                    str(page),
                    "-l",
                    str(page),
                    str(PDF),
                    str(prefix),
                ],
                check=True,
            )
            image = Image.open(next(tmp.glob(f"p{page}-*.png")))
            image.crop(tuple(v * 2 for v in box)).save(OUT / f"Figura{fig}_paperOriginal.png")
    for path in sorted(OUT.glob("*_paperOriginal.png")):
        print(path.name)


if __name__ == "__main__":
    main()
