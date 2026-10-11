"""Construcción de la variable resultado (exposición) por hexágono-hora.

Paper: §4.1
Código de los autores: 01_building_data/
Hallazgos (AGENTS.md §7): H2, H4, H30
Estado: parcial. Implementados `aggregate.py` y `vehicles_counts.py` (mediana de conteos desde
    los 42 archivos diarios) y `vehicles_distance.py` (mediana de distancia y tiempo desde los 41
    archivos diarios del paquete v2); `K_hi` por día desde el GPS crudo no es reconstruible (H4,
    D7); `noise.py` (Fase 8).
"""
