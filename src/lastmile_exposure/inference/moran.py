"""I de Moran de la distancia y los vehículos sobre hexágonos H3 vecinos.

Paper: §4.2.3, p.11 ("Moran's I ... aggregating across time through a simple average, are 0.4694
    and 0.4756"; "similarity among adjacent spatial units")
Código de los autores: (no incluido en el paquete; la matriz de pesos y la agregación en el tiempo
    no están especificadas)
Hallazgos (AGENTS.md §7): H28, D8
Estado: implementado (Fase 4C). La especificación del paper NO está identificada: la lectura
    literal no reproduce las cifras y las lecturas alternativas solo se acercan (ver H28).

Qué viene del paper y qué es una lectura nuestra:
- Del paper: I de Moran (Moran, 1950), hexágonos adyacentes, un promedio simple en el tiempo,
  las cifras 0,4694 (distancia K̃) y 0,4756 (vehículos Ỹ).
- Lectura nuestra (el paper no lo dice): "adyacentes" = anillo 1 de H3 (vecinos que comparten una
  arista, dentro de la grilla); estilo de pesos `W` (filas estandarizadas, convención de `spdep` y
  `esda`) o `B` (binaria); y qué significa "promedio simple en el tiempo" (`AGGREGATIONS`).

I de Moran:  I = (n / S0) · zᵀWz / zᵀz,  con z = x − media(x) y S0 = suma de los pesos. Los
hexágonos sin vecinos dentro de la grilla (islas) quedan en el cálculo con su fila de ceros, como
en `spdep` con `zero.policy` y en `esda` (n incluye las islas, S0 no tiene pesos de ellas).
"""

import h3
import numpy as np
import pandas as pd
import scipy.sparse as sp

STYLES = ("W", "B")  # W: filas estandarizadas; B: binaria
# "Promedio simple en el tiempo" admite tres lecturas (el paper no distingue):
#  - mean_of_hourly: I de cada hora y promedio simple de las 16 (lectura literal; la principal)
#  - mean_map: promedio de los DATOS entre horas y una sola I sobre ese mapa
#  - stacked: horas apiladas con W por bloques y cada hora centrada en su media; equivale al
#    promedio de las I horarias ponderado por la varianza de cada hora
AGGREGATIONS = ("mean_of_hourly", "mean_map", "stacked")
PRIMARY_STYLE = "W"
PRIMARY_AGGREGATION = "mean_of_hourly"


def h3_ring1_weights(hexes, *, style: str = "W") -> sp.csr_matrix:
    """Pesos de contigüidad de anillo 1 de H3 entre las celdas `hexes` (matriz dispersa n × n).

    Dos celdas son vecinas si comparten una arista (`grid_disk` de radio 1) y ambas están en
    `hexes`. `style="B"` devuelve la matriz binaria (simétrica) y `"W"` la estandariza por filas;
    las islas (sin vecinos en `hexes`) quedan con la fila en ceros.
    """
    if style not in STYLES:
        raise ValueError(f"`style` debe ser uno de {STYLES}, no {style!r}")
    hexes = list(hexes)
    index = {h: i for i, h in enumerate(hexes)}
    if len(index) != len(hexes):
        raise ValueError("`hexes` tiene celdas repetidas")
    rows, cols = [], []
    for i, cell in enumerate(hexes):
        for neighbor in h3.grid_disk(cell, 1):
            j = index.get(neighbor)
            if j is not None and j != i:
                rows.append(i)
                cols.append(j)
    n = len(hexes)
    binary = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    return binary if style == "B" else row_standardize(binary)


def row_standardize(w: sp.spmatrix) -> sp.csr_matrix:
    """Estandariza por filas; las filas sin pesos (islas) siguen en ceros."""
    sums = np.asarray(w.sum(axis=1)).ravel()
    inverse = np.divide(1.0, sums, out=np.zeros_like(sums), where=sums > 0)
    return (sp.diags(inverse) @ w).tocsr()


def n_islands(w: sp.spmatrix) -> int:
    """Nº de unidades sin ningún vecino (fila de ceros)."""
    return int((np.asarray(abs(w).sum(axis=1)).ravel() == 0).sum())


def morans_i(x: np.ndarray, w: sp.spmatrix) -> float:
    """I de Moran de `x` con la matriz de pesos `w` (n × n): (n / S0) · zᵀWz / zᵀz."""
    x = np.asarray(x, dtype=float)
    if x.ndim != 1 or w.shape != (len(x), len(x)):
        raise ValueError("`x` debe ser un vector y `w` una matriz n × n")
    z = x - x.mean()
    denominator = float(z @ z)
    if denominator == 0.0:
        raise ValueError("`x` es constante: la I de Moran no está definida")
    s0 = float(w.sum())
    if s0 == 0.0:
        raise ValueError("`w` no tiene ningún peso")
    return (len(x) / s0) * float(z @ (w @ z)) / denominator


def expected_i(n: int) -> float:
    """Valor esperado de la I de Moran bajo independencia espacial: −1 / (n − 1)."""
    return -1.0 / (n - 1)


def wide_by_hour(df: pd.DataFrame, column: str, hexes) -> pd.DataFrame:
    """Matriz hexágono × hora de `column`, con las filas en el orden de `hexes`."""
    wide = df.pivot(index="hex", columns="hour", values=column).reindex(list(hexes))
    if wide.isna().any().any():
        raise ValueError(f"`{column}` no cubre toda la grilla hexágono × hora")
    return wide


def hourly_morans_i(wide: pd.DataFrame, w: sp.spmatrix) -> pd.Series:
    """I de Moran de cada hora (columna) de `wide`."""
    return pd.Series({h: morans_i(wide[h].to_numpy(dtype=float), w) for h in wide.columns})


def aggregate_morans_i(wide: pd.DataFrame, w: sp.spmatrix, aggregation: str) -> float:
    """I de Moran agregada en el tiempo según `AGGREGATIONS` (ver la constante)."""
    if aggregation not in AGGREGATIONS:
        raise ValueError(f"`aggregation` debe ser una de {AGGREGATIONS}, no {aggregation!r}")
    values = wide.to_numpy(dtype=float)
    if aggregation == "mean_of_hourly":
        return float(hourly_morans_i(wide, w).mean())
    if aggregation == "mean_map":
        return morans_i(values.mean(axis=1), w)
    z = values - values.mean(axis=0)  # cada hora centrada en su propia media
    numerator = sum(float(z[:, j] @ (w @ z[:, j])) for j in range(z.shape[1]))
    denominator = float((z**2).sum())
    if denominator == 0.0:
        raise ValueError("Todas las horas son constantes: la I de Moran no está definida")
    return (values.shape[0] / float(w.sum())) * numerator / denominator


def morans_i_grid(wides: dict[str, pd.DataFrame], hexes) -> pd.DataFrame:
    """I de Moran para cada variable de `wides`, estilo (`STYLES`) y agregación (`AGGREGATIONS`).

    Devuelve una fila por (estilo, agregación) con una columna por variable, y `principal`
    marcando la lectura literal (promedio de las I horarias con pesos `W`); el resto son
    sensibilidades (lecturas alternativas del paper, no su metodología).
    """
    rows = []
    for style in STYLES:
        w = h3_ring1_weights(hexes, style=style)
        for aggregation in AGGREGATIONS:
            row = {"estilo": style, "agregacion": aggregation}
            for name, wide in wides.items():
                row[name] = aggregate_morans_i(wide, w, aggregation)
            row["principal"] = style == PRIMARY_STYLE and aggregation == PRIMARY_AGGREGATION
            rows.append(row)
    return pd.DataFrame(rows)
