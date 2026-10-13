# Entregables

Documentos (LaTeX) y presentaciones (Beamer) del proyecto, en la misma raíz para que el agente tenga todo el contexto a mano.

```
entregables/
├── README.md
├── referencias.bib            # bibliografía común a todos los entregables
├── _plantilla/                # punto de partida: main.tex (documento) y presentacion.tex (Beamer)
└── <nombre>/                  # un entregable por carpeta
    ├── presentacion.tex       # (o main.tex)
    ├── figuras/               # imágenes propias de este entregable
    ├── tablas/                # tablas .tex generadas desde los resultados (solo cifras agregadas)
    └── generar_tablas.py      # (opcional) genera tablas/*.tex desde outputs/ y reference/
```

Entregables actuales:

| Carpeta | Qué es |
|---|---|
| `replica_vs_paper/` | Presentación de los resultados replicados frente a los del paper (coincidencias, diferencias, figuras y tablas lado a lado) |

## Crear un entregable

Copiar `_plantilla/` a `entregables/<nombre>/` y editar. Las plantillas ya cargan `../referencias.bib` y buscan las figuras en `docs/figures/` (las autorizadas del repositorio, referenciadas y no copiadas) y en `figuras/` del propio entregable.

## Compilar

Desde la carpeta del entregable (MiKTeX con `latexmk` y `biber`; el aviso «unsupported version of Windows» no impide compilar):

```bash
latexmk -pdf -interaction=nonstopmode presentacion.tex   # o main.tex
latexmk -C                                               # limpia intermedios y PDF
```

## Tablas y figuras

- **Tablas:** si salen de los resultados de la réplica, se generan con un script del propio entregable (`generar_tablas.py`) que lee `outputs/` y `reference/` y escribe `tablas/*.tex`; así no se transcriben a mano. Si cambian los resultados, se vuelve a correr y se recompila.
- **Figuras de la réplica:** se referencian desde `docs/figures/` (no se copian).
- **Figuras del paper impreso:** se nombran `FiguraN_paperOriginal.png` y van en `figuras/`. Son del paper (Elsevier), por eso `.gitignore` las excluye. Para regenerarlas desde el PDF: `entregables/replica_vs_paper/extraer_figuras_paper.py` (necesita `data/Basso2026TRD.pdf`).

## Qué se versiona

Se versionan las fuentes (`.tex`, `.bib`, scripts y tablas `.tex`) y las imágenes propias. No se versionan: los intermedios de LaTeX, los PDF compilados (para uno concreto: `git add -f entregables/<nombre>/<archivo>.pdf`) ni las figuras `*_paperOriginal.*`.

## Datos confidenciales

Las presentaciones son para el grupo de trabajo que tiene los datos, pero el repositorio tiene remoto en GitHub: lo que se agregue a `entregables/` y se suba con un commit queda en el historial. Preferir figuras de `docs/figures/` y cifras agregadas; cualquier imagen o tabla con datos por hexágono, por celda o por fila va solo si se decide a propósito (regla 3 de `AGENTS.md`). No hay prueba automática que lo vigile.
