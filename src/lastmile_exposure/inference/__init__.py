"""Inferencia y autocorrelación espacial.

Paper: §4.2.3
Código de los autores: 02_estimation/
Hallazgos (AGENTS.md §7): H11, H12, H25, H27–H29
Estado: parcial (Fase 4). Implementados `cluster.py` (SE por comuna de los OLS, NB equivalente y
    dos partes), `zinb_sandwich.py` (sandwich del ZINB completo) y `dispersion.py`
    (Cameron–Trivedi), `moran.py` (I de Moran; especificación no identificada, H28) y
    `zero_inflation.py` (π del ZINB: perfil de verosimilitud y test de frontera; H29).
"""
