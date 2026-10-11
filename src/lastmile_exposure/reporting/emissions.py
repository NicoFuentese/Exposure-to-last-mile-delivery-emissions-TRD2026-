"""Conversión del efecto de distancia a gramos de NOx y PM (Fig. 7).

Paper: §5.1 (p.13) y Fig. 7 (p.14: «Average monthly extra grams of pollutant by SEG»)
Código de los autores: (no está en el paquete: ningún `.R` contiene factores de emisión)
Hallazgos (AGENTS.md §7): §5.7, D10, H36
Estado: implementado (Fase 7) como DERIVACIÓN, no como réplica de los factores de la fuente.

El paper dice que los gramos salen de las emisiones de NOx y PM «por metro» del vehículo de reparto
no eléctrico promedio de Agency (2024), pero no da cifras, categoría de vehículo ni el multiplicador
que lleva a «cada mes». Lo que sí se puede comprobar es que cada barra de la Fig. 7 es **una
constante por el efecto marginal OLS `K̃>0` de la Tabla 4** (H36): cada etiqueta impresa, con un
decimal, restringe esa constante a un intervalo, y la intersección de los seis intervalos de cada
contaminante no es vacía. Por eso `emission_factors` deriva el factor (en gramos por metro marginal
y por mes: el producto del factor de emisión y del multiplicador, que no se pueden separar) a partir
de las barras impresas, sin cifras externas. Los gramos que dibuja la Fig. 7 de la réplica son
`factor × efecto OLS K̃>0`, y por tanto reproducen la figura del paper, pero NO son una estimación
independiente de emisiones.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

ROUNDING = 0.05  # las barras se imprimen con un decimal: la cifra verdadera cae en ±0,05


@dataclass(frozen=True)
class Factor:
    """Intervalo de factores (g por metro marginal y mes) compatible con las barras impresas."""

    low: float
    high: float

    @property
    def consistent(self) -> bool:
        """True si existe una constante que reproduce todas las barras impresas."""
        return self.low <= self.high

    @property
    def value(self) -> float:
        """Punto medio del intervalo (el valor que se usa para dibujar)."""
        return (self.low + self.high) / 2


def implied_factor(effects: pd.Series, printed: pd.Series, *, rounding: float = ROUNDING) -> Factor:
    """Intervalo de `k` con `k · effects` igual a `printed` (a ±`rounding`) en cada categoría.

    `effects` y `printed` van indexados por categoría (D+E, C3, C2, C1b, C1a, AB). Las categorías
    con efecto 0 (la de referencia) no restringen `k`, pero su barra impresa debe ser 0.
    """
    low, high = -np.inf, np.inf
    for label, grams in printed.items():
        effect = float(effects[label])
        if effect == 0:
            if abs(grams) > rounding:
                raise ValueError(f"{label}: efecto 0 pero la barra impresa es {grams}")
            continue
        bounds = ((grams - rounding) / effect, (grams + rounding) / effect)
        low, high = max(low, min(bounds)), min(high, max(bounds))
    if not np.isfinite(low) or not np.isfinite(high):
        raise ValueError(
            "Ninguna categoría con efecto distinto de 0: no se puede derivar el factor"
        )
    return Factor(low, high)


def emission_factors(effects: pd.Series, bars: pd.DataFrame) -> dict[str, Factor]:
    """Factores de NOx y PM (`"nox"`, `"pm"`) derivados de las barras impresas de la Fig. 7.

    `bars` es `validation.paper_tables.load_fig7_bars()` (`label`, `nox_g`, `pm_g`) y `effects` el
    efecto OLS `K̃>0` impreso de la Tabla 4 por GSE, indexado por etiqueta.
    """
    indexed = bars.set_index("label")
    return {
        "nox": implied_factor(effects, indexed["nox_g"]),
        "pm": implied_factor(effects, indexed["pm_g"]),
    }


def emission_grams(effects: pd.Series, factors: dict[str, Factor]) -> pd.DataFrame:
    """Gramos por GSE (`label`, `nox_g`, `pm_g`) = factor × efecto OLS `K̃>0`, en ese orden."""
    return pd.DataFrame(
        {
            "label": effects.index,
            "nox_g": effects.to_numpy(dtype=float) * factors["nox"].value,
            "pm_g": effects.to_numpy(dtype=float) * factors["pm"].value,
        }
    )
