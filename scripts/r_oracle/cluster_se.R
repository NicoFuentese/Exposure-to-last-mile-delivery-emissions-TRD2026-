# Contraste en R: errores estándar con cluster por comuna, replicando la ruta de los autores
# (summary_results_cluster.R / summary_results_static_cluster.R):
#   ZINB: sandwich::vcovCL(pscl::zeroinfl(...), cluster = comuna), bloque de conteo
#   NB  : sandwich::vcovCL(MASS::glm.nb(...), cluster = comuna)  (informativo: usa la
#         información esperada con theta fijo; no es comparable con una NB de ML conjunta)
#   OLS : sandwich::vcovCL(lm(...), cluster = comuna) para K y log K (el código de los autores
#         usa fixest::feols; aquí solo se contrasta la fórmula del sandwich)
# Salida: parámetros y errores estándar agregados (sin filas individuales).
lib <- Sys.getenv("R_LIBS_USER")
.libPaths(c(lib, .libPaths()))
suppressMessages({
  library(pscl)
  library(MASS)
  library(sandwich)
})

args <- commandArgs(trailingOnly = TRUE)
root <- args[1]   # .../data/replication_package/00_data
out  <- args[2]   # carpeta de salida

vars <- c("genero_masc", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3", "gse_de",
          "edad_menor_25", "edad_25_34", "edad_35_44", "edad_45_54", "edad_55_64")
rhs <- paste(vars, collapse = " + ")

counts <- read.csv(file.path(root, "hexagon_model_median_wednesdays_RM.csv"), fileEncoding = "UTF-8")
counts$vehicles <- round(counts$median_vehicles, 0)       # round() de R: mitades al par
dist <- read.csv(file.path(root, "hexagon_model_median_wednesday_alternative_metrics_RM.csv"),
                 fileEncoding = "UTF-8")
dist$log_distance <- ifelse(dist$median_distance > 0, log(dist$median_distance), NA)

prep_dynamic <- function(d) { d$gse_de <- d$gse_d + d$gse_e; d }
st <- read.csv(file.path(root, "datosxhexagono.csv"), fileEncoding = "UTF-8")
for (g in c("gse_ab", "gse_c1a", "gse_c1b", "gse_c2", "gse_c3", "gse_d", "gse_e")) st[[g]] <- st[[g]] / 100
st$gse_de <- st$gse_d + st$gse_e
prep_static <- function(d, cols) merge(d[, cols], st[, c("hex", vars)], by = "hex", all.x = TRUE)

run <- function(cdat, ddat, tag) {
  t0 <- Sys.time()
  cl_c <- cdat$comuna
  zi <- zeroinfl(as.formula(paste("vehicles ~", rhs, "| 1")), dist = "negbin", data = cdat)
  nb_names <- paste0("count_", c("(Intercept)", vars))
  v_cl <- vcovCL(zi, cluster = cl_c)
  v_iid <- vcov(zi)
  nb <- glm.nb(as.formula(paste("vehicles ~", rhs)), data = cdat)
  v_nb <- vcovCL(nb, cluster = cl_c)
  ols <- lm(as.formula(paste("median_distance ~", rhs)), data = ddat)
  v_ols <- vcovCL(ols, cluster = ddat$comuna)
  ddp <- ddat[!is.na(ddat$log_distance), ]
  lg <- lm(as.formula(paste("log_distance ~", rhs)), data = ddp)
  v_lg <- vcovCL(lg, cluster = ddp$comuna)
  pos <- ddat[ddat$median_distance > 0, ]
  olp <- lm(as.formula(paste("median_distance ~", rhs)), data = pos)
  v_olp <- vcovCL(olp, cluster = pos$comuna)
  nm <- c("(Intercept)", vars)
  res <- data.frame(
    name = nm,
    zinb_coef = as.numeric(coef(zi, model = "count")[nm]),
    zinb_se_cluster = sqrt(diag(v_cl)[nb_names]),
    zinb_se_iid = sqrt(diag(v_iid)[nb_names]),
    nb_coef = as.numeric(coef(nb)[nm]),
    nb_se_cluster = sqrt(diag(v_nb)[nm]),
    ols_k_se_cluster = sqrt(diag(v_ols)[nm]),
    ols_logk_se_cluster = sqrt(diag(v_lg)[nm]),
    ols_pos_se_cluster = sqrt(diag(v_olp)[nm])
  )
  write.csv(res, file.path(out, paste0("cluster_se_", tag, ".csv")), row.names = FALSE)
  info <- data.frame(
    tag = tag, n_clusters = length(unique(cl_c)), n_obs = nrow(cdat),
    zero_intercept = as.numeric(coef(zi, model = "zero")[1]), theta_zinb = zi$theta,
    theta_nb = nb$theta,
    seconds = as.numeric(difftime(Sys.time(), t0, units = "secs"))
  )
  write.csv(info, file.path(out, paste0("cluster_se_", tag, "_info.csv")), row.names = FALSE)
  print(info)
}

run(prep_dynamic(counts), prep_dynamic(dist), "dynamic")
run(prep_static(counts, c("hex", "hour", "vehicles", "comuna")),
    prep_static(dist, c("hex", "hour", "median_distance", "log_distance", "comuna")), "static")
