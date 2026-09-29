"""Construcción de la variable resultado (exposición) por hexágono-hora.

Paper: §4.1
Código de los autores: 01_building_data/
Hallazgos (AGENTS.md §7): H2, H4
Estado: pendiente. `vehicles_counts.py` y `aggregate.py` (Fase 3); `vehicles_distance.py` no es
    reconstruible con los datos actuales (H4, D7); `noise.py` (Fase 8). Hoy se usan las medianas
    ya calculadas del paquete (`io/panel.py`).
"""
