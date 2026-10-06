"""DIAGNOSTICO de las estrellas con data_base. NO ES UNA REPLICA (AGENTS.md H26).

Uso (con el entorno activo, desde la raíz del repositorio):
    python scripts/07_stars_diagnosis.py     # ajusta el ZINB sobre data_base (~3 min en total)

ADVERTENCIA: este script NO reproduce el paper y sus resultados NO sirven como inferencia. Usa
`00_out/data_base`, cuyos conteos son la mediana de solo los DOS primeros miércoles de 2024 (no los
41-42 del paper). Existe únicamente para probar la hipótesis de que las estrellas publicadas se
generaron con esa base (los scripts de los autores la leen por defecto): con ella coinciden
78 de 88 estrellas frente a 61 de 88 con `00_data`. No usar sus salidas en tablas ni figuras.

Entrada: data/replication_package/00_out/data_base/ (datos confidenciales, no versionados)
Salida:  outputs/diagnostics/DIAGNOSTICO_data_base_*.csv (nunca en outputs/as_published/)
Código:  src/lastmile_exposure/validation/stars_diagnosis.py
Termina siempre con código 0.
"""

import sys

from lastmile_exposure.validation import stars_diagnosis as diag


def main() -> int:
    print(diag.BANNER)
    results = diag.run_diagnosis()
    for tag, (_, report) in results.items():
        print(f"\n{tag}: estrellas iguales {int(report['ok'].sum())}/{len(report)}")
        bad = diag.residual_cells(report)
        bad = bad.assign(p=bad["p"].map(lambda v: f"{v:.4f}"))
        if len(bad):
            print("  celdas que siguen distintas del paper:")
            print(bad.to_string(index=False))
    print("\nEstrellas iguales por tabla y columna (de 11 por columna):")
    print(diag.summarize(results).to_string())
    print(f"\n-> {diag.diagnostics_dir()}  (SOLO DIAGNOSTICO)")
    print(diag.BANNER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
