# Contraste en R (`pscl`) del ZINB

Parámetros del ZINB estimados con `pscl::zeroinfl` (la misma función que usa el código de los autores), para contrastar nuestro ZINB en Python. **No son cifras del paper**: son resultados nuestros sobre los datos confidenciales (14 parámetros por modelo, sin filas individuales).

| Archivo | Modelo |
|---|---|
| `zinb_pscl_dynamic.csv` | ZINB con demografía dinámica (Tabla 4) |
| `zinb_pscl_static.csv` | ZINB con demografía estática (Tabla 5) |

Formato: `name,value`.
- `inflate_const`: constante de la inflación (π = logística de este valor).
- `const` y los 11 regresores: coeficientes de la componente de conteo (log μ).
- `alpha`: dispersión en la parametrización de `statsmodels` (= 1/θ de `pscl`).
- `loglik`: log-verosimilitud que reporta `pscl` en su solución.
- `ame_authors:<regresor>`: efecto marginal con la fórmula del código de los autores.

**Origen:** `scripts/r_oracle/zinb_pscl.R`, ejecutado con R 4.6.1 y `pscl` 1.5.9 el 2026-10-03:

```bash
Rscript scripts/r_oracle/zinb_pscl.R data/replication_package_v2/00_data <carpeta_de_salida>
```

Requiere `pscl` instalado en R (`install.packages("pscl")`). R solo se usa para este contraste; la réplica es Python.

## Errores estándar con cluster por comuna (`sandwich::vcovCL`)

| Archivo | Contenido |
|---|---|
| `cluster_se_dynamic.csv`, `cluster_se_static.csv` | Por regresor (y `(Intercept)`): `zinb_coef`, `zinb_se_cluster` (bloque de conteo de `vcovCL(zeroinfl)`, lo que hace el código de los autores), `zinb_se_iid` (`vcov(zeroinfl)`), `nb_coef`/`nb_se_cluster` (`MASS::glm.nb` + `vcovCL`), `ols_k_se_cluster`, `ols_logk_se_cluster`, `ols_pos_se_cluster` (`lm` + `vcovCL`: `K̃`, `log K̃` sobre `K̃>0`, y `K̃` sobre `K̃>0`). |

**Origen:** `scripts/r_oracle/cluster_se.R` (R 4.6.1, `pscl` 1.5.9, `sandwich` 3.1-3, `MASS`; 2026-10-06):

```bash
Rscript scripts/r_oracle/cluster_se.R data/replication_package_v2/00_data <carpeta_de_salida>
```

Requiere `install.packages(c("pscl", "sandwich"))` en R. Son resultados nuestros sobre los datos confidenciales (parámetros y errores estándar agregados).

**Cómo se usan:** `tests/validation/test_cluster_se_oracle.py` compara nuestro sandwich del ZINB (a ≤ 2,5 %) y de los OLS (a ≤ 0,5 %) con estas cifras. La columna `nb_se_cluster` **no** se usa como contraste de nuestra NB: `vcovCL(glm.nb)` usa la información esperada con θ fijo y no es comparable con el sandwich de máxima verosimilitud conjunta (da SE entre 0,5 y 1,1 veces los nuestros según el coeficiente).

**Qué muestran** (ver `AGENTS.md` §7, H21–H23): nuestra log-verosimilitud evaluada en estos parámetros coincide con la de R (mismo modelo), pero el máximo verdadero es algo más alto (`pscl` se detiene antes), y por eso `pscl` (ni el ZINB de `statsmodels`) reproduce la columna ZINB del paper al 4.º decimal. Lo que sí la reproduce es el máximo de la verosimilitud, que está en la frontera π = 0 (la NB; `fit_zinb_mle`): ver H23 y H29.
