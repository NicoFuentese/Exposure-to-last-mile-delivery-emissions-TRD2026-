# Cifras publicadas del paper

Valores de las Tablas 2 a 5 de Basso et al. (2026), usados como objetivo de validación. Son cifras ya publicadas (no datos confidenciales) y sí se versionan.

| Archivo | Tabla | Origen |
|---|---|---|
| `table2_floating_population.csv` | Tabla 2 (p. 7) | Transcrita del PDF; Mean y Std verificados contra `miercoles_rm.csv` (AGENTS.md H15) |
| `table3_vehicle_dataset.csv` | Tabla 3 (p. 7) | Transcrita del PDF |
| `table4_dynamic.csv` | Tabla 4 (p. 12) | Extraída de la capa de texto del PDF con `pdftotext` |
| `table5_static.csv` | Tabla 5 (p. 15) | Extraída de la capa de texto del PDF con `pdftotext` |

Formato de las Tablas 4 y 5: una fila por regresor (`variable` = nombre de columna del paquete, `label` = nombre en el paper, `group` = sex/age/seg) y, para cada modelo (`zinb`, `ols_k`, `ols_kpos`, `ols_logk`), el valor y sus estrellas (`*_sig`). Las categorías de referencia (`edad_mayor_65`, `gse_ab`) valen 0 sin estrellas. Los valores son los efectos marginales publicados, no coeficientes (en `ols_logk` sí son coeficientes crudos, ver H8).
