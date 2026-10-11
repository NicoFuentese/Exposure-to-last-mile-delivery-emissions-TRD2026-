"""Informe de reproducción: qué se reproduce del paper, qué no y qué cambió.

Paper: Tablas 2 a 5, Figs. 1 y 6 a 10 y las cifras del texto (§4.2)
Código de los autores: (no aplica)
Hallazgos (AGENTS.md §7): H8, H23, H24, H27, H28, H29, H30, H31, H33, H35, H36
Estado: implementado (ejecutor final). Lee las salidas que dejan los scripts de `scripts/` y las
    cifras publicadas (`reference/paper_tables/`); no vuelve a ajustar ningún modelo, así que tarda
    segundos y se puede ejecutar solo (`scripts/16_run_all.py --report-only`).

Cada ítem del informe tiene un estado:
- `EXACT` (✅ exacto): idéntico al paper (las medianas reconstruidas).
- `WITHIN` (✅ dentro de la tolerancia): coincide con el paper al redondeo que imprime o dentro de
  la tolerancia acordada (D2, H27).
- `DOCUMENTED` (🟡 desviación documentada): NO coincide con el paper y la causa está documentada
  (H24, H28, H35). Se fija el valor documentado: si cambia, el ítem pasa a `FAILED`.
- `INFO` (ℹ️ informativo): resultado propio sin objetivo del paper (π̂, conclusiones con hora
  local, estrellas impresas). También se fija su valor documentado.
- `FAILED` (❌ falla): algo que debe reproducirse no coincide, un valor documentado cambió o un
  paso terminó con error.
- `SKIPPED` (⏭️ omitido): falta la salida (paso no ejecutado o sin datos); no cuenta como fallo.

El informe SOLO contiene agregados (diferencias, coeficientes, conteos), nunca filas de los datos.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import pandas as pd

from lastmile_exposure import config
from lastmile_exposure.validation.paper_tables import (
    MARGINAL_TOLERANCE,
    compare_stars,
    load_fig7_bars,
    load_table4,
    load_table5,
)


class Status(StrEnum):
    EXACT = "exact"
    WITHIN = "within"
    DOCUMENTED = "documented"
    INFO = "info"
    FAILED = "failed"
    SKIPPED = "skipped"

    @property
    def symbol(self) -> str:
        return {
            "exact": "✅",
            "within": "✅",
            "documented": "🟡",
            "info": "ℹ️",
            "failed": "❌",
            "skipped": "⏭️",
        }[self.value]

    @property
    def label(self) -> str:
        return {
            "exact": "exacto",
            "within": "dentro de la tolerancia",
            "documented": "desviación documentada",
            "info": "informativo",
            "failed": "falla",
            "skipped": "omitido",
        }[self.value]


@dataclass(frozen=True)
class Item:
    """Una fila del informe."""

    id: str
    area: str
    name: str
    target: str
    result: str
    status: Status
    ref: str = ""
    source: str = ""
    source_date: datetime | None = None
    note: str = ""


@dataclass
class Context:
    """Dónde están las salidas y de qué dependen las comprobaciones.

    `authors_reference` carga la tabla 4 (`"dynamic"`) o 5 (`"static"`) regenerada por los autores;
    es `None` si el paquete no está (las estrellas quedan omitidas).
    """

    tables_dir: Path
    figures_dir: Path
    local_dir: Path
    run_log: dict | None = None
    authors_reference: Callable[[str], pd.DataFrame] | None = None

    @classmethod
    def default(cls, run_log: dict | None = None) -> "Context":
        from lastmile_exposure.validation.paper_tables import (
            authors_reference_dir,
            load_authors_reference,
        )

        base = config.OUTPUTS_DIR / config.Variant.AS_PUBLISHED.value
        loader = load_authors_reference if authors_reference_dir().exists() else None
        return cls(
            tables_dir=base / "tables",
            figures_dir=base / "figures",
            local_dir=config.OUTPUTS_DIR / config.Variant.LOCAL_TIME.value / "tables",
            run_log=run_log,
            authors_reference=loader,
        )


# --- Valores documentados que el informe vigila (si cambian, el ítem pasa a FAILED) ----------
MORAN_DOCUMENTED = {"distancia": 0.41901, "vehiculos": 0.42966}  # H28, lectura literal
MORAN_TOLERANCE = 5e-4
WASSERSTEIN_IN_BAND = 13  # H24: 13 de 15 valores publicados dentro de la banda del 95 %
FIG1_RATIOS = {"AB": 0.9446, "C1b": 1.0105}  # H35: máximo propio / extremo de escala del paper
FIG1_TOLERANCE = 2e-3
FIGURE_DATA_TOLERANCE = 1e-4 + 1e-9  # el paper imprime 4 decimales
PI_DOCUMENTED_MAX = 1e-6  # H29: π̂ = 0 en la frontera
STAR_CELLS = 44  # 11 variables × 4 columnas por tabla


def _read(path: Path, **kwargs) -> tuple[pd.DataFrame, datetime] | None:
    """Lee un CSV de salida y su fecha de modificación; `None` si no existe."""
    if not path.exists():
        return None
    return pd.read_csv(path, **kwargs), datetime.fromtimestamp(path.stat().st_mtime)


def _skipped(item_id: str, area: str, name: str, source: str, hint: str, ref: str = "") -> Item:
    return Item(
        item_id,
        area,
        name,
        target="",
        result=f"sin salida: {hint}",
        status=Status.SKIPPED,
        ref=ref,
        source=source,
    )


def _cells(frame: pd.DataFrame) -> str:
    """`ok/total` de celdas de un resumen de `column_summary`."""
    return f"{int(frame['ok_cells'].sum())}/{int(frame['cells'].sum())}"


def _identity_result(frame: pd.DataFrame) -> str:
    worst = float(frame["max_abs_diff"].max())
    return f"{int(frame['n_rows'].iloc[0]):,} filas; dif. máx. {_fmt(worst)}"


def _fmt(value: float) -> str:
    return f"{value:.2g}" if value and abs(value) < 0.01 else f"{value:.4g}"


# ------------------------------------------------------------------ comprobaciones
def check_table2(ctx: Context) -> list[Item]:
    source = "comparison_table2.csv"
    read = _read(ctx.tables_dir / source)
    if read is None:
        return [
            _skipped(
                "table2", "Tablas", "Tabla 2 (medias y desviaciones)", source, "paso 01", "H15"
            )
        ]
    frame, date = read
    ok = bool((frame["ok_cells"] == frame["cells"]).all())
    worst = float(frame["max_abs_diff"].max())
    return [
        Item(
            "table2",
            "Tablas",
            "Tabla 2: media, desviación y porcentajes",
            "al redondeo impreso",
            f"{_cells(frame)} celdas; dif. máx. {_fmt(worst)}",
            Status.WITHIN if ok else Status.FAILED,
            "H15",
            source,
            date,
        )
    ]


def check_tables_4_5(ctx: Context) -> list[Item]:
    items = []
    for number, label in ((4, "dinámica"), (5, "estática")):
        source = f"comparison_table{number}.csv"
        name = f"Tabla {number} ({label}): 4 columnas (ZINB y 3 OLS)"
        read = _read(ctx.tables_dir / source)
        if read is None:
            items.append(_skipped(f"table{number}", "Tablas", name, source, "paso 03", "H8, H23"))
            continue
        frame, date = read
        ok = bool((frame["ok_cells"] == frame["cells"]).all())
        zinb = frame.loc[frame["column"] == "zinb", "max_abs_diff"]
        items.append(
            Item(
                f"table{number}",
                "Tablas",
                name,
                f"al redondeo impreso (≤ {MARGINAL_TOLERANCE:.0e})",
                f"{_cells(frame)} celdas; dif. máx. "
                f"{_fmt(float(frame['max_abs_diff'].max()))} (ZINB {_fmt(float(zinb.max()))})",
                Status.WITHIN if ok else Status.FAILED,
                "H8, H23",
                source,
                date,
            )
        )
    return items


def _check_identity(
    ctx: Context, source: str, item_id: str, name: str, step: str, ref: str
) -> Item:
    read = _read(ctx.tables_dir / source)
    if read is None:
        return _skipped(item_id, "Medianas", name, source, f"paso {step}", ref)
    frame, date = read
    same = bool(frame["identical"].all()) and bool((frame["n_rows"] == frame["n_expected"]).all())
    return Item(
        item_id,
        "Medianas",
        name,
        "idénticas a la base del paper",
        _identity_result(frame),
        Status.EXACT if same else Status.FAILED,
        ref,
        source,
        date,
    )


def check_medians(ctx: Context) -> list[Item]:
    return [
        _check_identity(
            ctx,
            "median_counts_check.csv",
            "median_counts",
            "Mediana de conteos (42 miércoles)",
            "04",
            "H2",
        ),
        _check_identity(
            ctx,
            "median_distance_check.csv",
            "median_distance",
            "Mediana de distancia y tiempo (41 miércoles)",
            "11",
            "H30",
        ),
    ]


def check_stars(ctx: Context) -> list[Item]:
    items = []
    # variante con la que se reproduce cada tabla (D3): cluster por comuna en la 4 y la de su
    # script en la 5
    cases = (("dynamic", "paper_text", "Tabla 4"), ("static", "authors_script", "Tabla 5"))
    for tag, variant, label in cases:
        source = f"inference_{tag}_{variant}.csv"
        name = f"Estrellas de la {label} contra las tablas de los autores"
        read = _read(ctx.tables_dir / source, keep_default_na=False)
        if read is None:
            items.append(_skipped(f"stars_{tag}", "Inferencia", name, source, "paso 06", "H31"))
            continue
        if ctx.authors_reference is None:
            items.append(
                _skipped(
                    f"stars_{tag}",
                    "Inferencia",
                    name,
                    source,
                    "falta el paquete de los autores",
                    "H31",
                )
            )
            continue
        inference, date = read
        report = compare_stars(inference, ctx.authors_reference(tag))
        matches = int(report["ok"].sum())
        items.append(
            Item(
                f"stars_{tag}",
                "Inferencia",
                name,
                f"{len(report)}/{len(report)}",
                f"{matches}/{len(report)} (variante {variant})",
                Status.EXACT if matches == len(report) else Status.FAILED,
                "H31",
                source,
                date,
            )
        )
    # las estrellas impresas en el paper no son un objetivo (H31, H32): se informan
    printed = []
    for tag, variant in (("dynamic", "paper_text"), ("static", "authors_script")):
        read = _read(ctx.tables_dir / f"stars_{tag}_{variant}.csv", keep_default_na=False)
        if read is not None:
            printed.append((int(read[0]["ok"].sum()), len(read[0]), read[1]))
    if len(printed) == 2:
        items.append(
            Item(
                "stars_printed",
                "Inferencia",
                "Estrellas impresas en el paper (no son objetivo)",
                "—",
                " y ".join(
                    f"{ok}/{n} (Tabla {t})" for (ok, n, _), t in zip(printed, (4, 5), strict=True)
                ),
                Status.INFO,
                "H31, H32",
                "stars_*.csv",
                max(printed[0][2], printed[1][2]),
                "los autores reconocen que no salen del método correcto",
            )
        )
    return items


def check_dispersion(ctx: Context) -> list[Item]:
    source = "cameron_trivedi.csv"
    read = _read(ctx.tables_dir / source)
    name = "Test de Cameron–Trivedi (dispersión 7,73)"
    if read is None:
        return [_skipped("dispersion", "Inferencia", name, source, "paso 08", "H27")]
    frame, date = read
    row = frame[frame["tabla"] == "dynamic"].iloc[0]
    ok = bool(row["abs_diff"] <= row["limit"])
    return [
        Item(
            "dispersion",
            "Inferencia",
            name,
            f"{row['paper']:g} (±1 %)",
            f"{row['dispersion']:.3f} (dif. {row['abs_diff'] / row['paper'] * 100:.2f} %)",
            Status.WITHIN if ok else Status.FAILED,
            "H27",
            source,
            date,
        )
    ]


def check_moran(ctx: Context) -> list[Item]:
    source = "moran.csv"
    read = _read(ctx.tables_dir / source)
    name = "I de Moran (0,4694 y 0,4756)"
    if read is None:
        return [_skipped("moran", "Inferencia", name, source, "paso 09", "H28")]
    frame, date = read
    principal = frame[frame["rol"] == "principal"].set_index("variable")["moran_i"]
    unchanged = all(
        abs(float(principal[k]) - v) <= MORAN_TOLERANCE for k, v in MORAN_DOCUMENTED.items()
    )
    return [
        Item(
            "moran",
            "Inferencia",
            name,
            "0,4694 / 0,4756",
            f"{principal['distancia']:.3f} / {principal['vehiculos']:.3f} (lectura literal)",
            Status.DOCUMENTED if unchanged else Status.FAILED,
            "H28",
            source,
            date,
            "la especificación no está identificada"
            if unchanged
            else "el valor cambió respecto de lo documentado",
        )
    ]


def check_wasserstein(ctx: Context) -> list[Item]:
    source = "table2_mobility_seeds.csv"
    read = _read(ctx.tables_dir / source)
    name = "Wasserstein de la Tabla 2 (200 semillas)"
    if read is None:
        return [_skipped("wasserstein", "Movilidad", name, source, "paso 12", "H24")]
    frame, date = read
    inside = int(frame["inside_band"].astype(bool).sum())
    outside = ", ".join(frame.loc[~frame["inside_band"].astype(bool), "group"])
    unchanged = inside == WASSERSTEIN_IN_BAND
    return [
        Item(
            "wasserstein",
            "Movilidad",
            name,
            "valores publicados",
            f"{inside}/{len(frame)} dentro de la banda del 95 % (fuera: {outside or 'ninguno'})",
            Status.DOCUMENTED if unchanged else Status.FAILED,
            "H24",
            source,
            date,
            "los autores muestrearon sin semilla: no es reproducible exactamente",
        )
    ]


def check_pi(ctx: Context) -> list[Item]:
    source = "zero_inflation.csv"
    read = _read(ctx.tables_dir / source)
    name = "π del ZINB (el paper no lo reporta)"
    if read is None:
        return [_skipped("pi", "Diagnóstico", name, source, "paso 10", "H29")]
    frame, date = read
    on_boundary = bool(frame["en_frontera"].astype(bool).all()) and bool(
        (frame["pi_hat"].abs() <= PI_DOCUMENTED_MAX).all()
    )
    intervals = " y ".join(f"[0, {v:.1e}]" for v in frame["ic_superior"])
    return [
        Item(
            "pi",
            "Diagnóstico",
            name,
            "—",
            f"π̂ = 0 en la frontera; IC 95 % {intervals} (dinámica y estática)",
            Status.INFO if on_boundary else Status.FAILED,
            "H29",
            source,
            date,
        )
    ]


def check_local_time(ctx: Context) -> list[Item]:
    source = "robustness.csv"
    read = _read(ctx.local_dir / source)
    name = "Conclusiones del paper con la hora local corregida"
    if read is None:
        return [_skipped("local_time", "Sensibilidad", name, source, "paso 13", "H33")]
    frame, date = read
    robust = int(frame["robusta"].astype(bool).sum())
    return [
        Item(
            "local_time",
            "Sensibilidad",
            name,
            "—",
            f"{robust}/{len(frame)} conclusiones se mantienen",
            Status.INFO if robust == len(frame) else Status.FAILED,
            "H33",
            source,
            date,
        )
    ]


def check_figures(ctx: Context) -> list[Item]:
    from lastmile_exposure.figures.marginal_effects import FIGURES, figure_data

    printed = {"dynamic": load_table4(), "static": load_table5()}
    items = []
    worst, date, missing = 0.0, None, []
    for name, (tag, group) in FIGURES.items():
        read = _read(ctx.figures_dir / f"{name}_data.csv")
        if read is None:
            missing.append(name)
            continue
        ours, when = read
        reference = figure_data(printed[tag], group)
        worst = max(
            worst,
            float((ours["zinb"] - reference["zinb"]).abs().max()),
            float((ours["ols_kpos"] - reference["ols_kpos"]).abs().max()),
        )
        date = when if date is None else max(date, when)
    label = "Figs. 6, 8, 9 y 10 (efectos marginales)"
    if missing:
        items.append(
            _skipped("figures_effects", "Figuras", label, "fig*_data.csv", "paso 14", "H34")
        )
    else:
        items.append(
            Item(
                "figures_effects",
                "Figuras",
                label,
                "mismos puntos que las Tablas 4 y 5",
                f"dif. máx. {_fmt(worst)}",
                Status.WITHIN if worst <= FIGURE_DATA_TOLERANCE else Status.FAILED,
                "H34",
                "fig*_data.csv",
                date,
                "el eje derecho está reescalado: comparan formas",
            )
        )
    # Fig. 7: las 12 etiquetas impresas
    source = "fig7_emissions_seg_data.csv"
    read = _read(ctx.figures_dir / source)
    label7 = "Fig. 7 (gramos de NOx y PM)"
    if read is None:
        items.append(_skipped("fig7", "Figuras", label7, source, "paso 14", "H36"))
    else:
        grams, when = read
        bars = load_fig7_bars().set_index("label")
        ours = grams.set_index("label")[["nox_g", "pm_g"]].round(1)
        same = int((ours.to_numpy() == bars.loc[ours.index, ["nox_g", "pm_g"]].to_numpy()).sum())
        items.append(
            Item(
                "fig7",
                "Figuras",
                label7,
                "12 etiquetas impresas",
                f"{same}/12 etiquetas iguales",
                Status.WITHIN if same == 12 else Status.FAILED,
                "H36",
                source,
                when,
                "el factor se deriva de las propias barras: no es una estimación independiente",
            )
        )
    return items


def check_fig1_scales(ctx: Context) -> list[Item]:
    source = "fig1_scales.csv"
    read = _read(ctx.tables_dir / source)
    name = "Fig. 1: escalas de color de los mapas"
    if read is None:
        return [_skipped("fig1_scales", "Figuras", name, source, "paso 15", "H35")]
    frame, date = read
    ratios = frame.set_index("group")["ratio"]
    unchanged = all(abs(float(ratios[g]) - r) <= FIG1_TOLERANCE for g, r in FIG1_RATIOS.items())
    scales = frame.set_index("group")
    detail = "; ".join(
        f"{g} {scales.loc[g, 'ours_max']:.0f} frente a {scales.loc[g, 'paper_max']:.0f}"
        for g in ratios.index
    )
    return [
        Item(
            "fig1_scales",
            "Figuras",
            name,
            "1600 (AB) y 7000 (C1b)",
            detail,
            Status.DOCUMENTED if unchanged else Status.FAILED,
            "H35",
            source,
            date,
            "el patrón se reproduce; la causa de la diferencia de escala no se conoce",
        )
    ]


def check_steps(ctx: Context) -> list[Item]:
    """Un ítem FAILED por cada paso del ejecutor que terminó con error."""
    if not ctx.run_log:
        return []
    items = []
    for step in ctx.run_log.get("steps", []):
        if step.get("status") in ("failed", "error"):
            items.append(
                Item(
                    f"step_{step['id']}",
                    "Ejecución",
                    f"Paso {step['id']} ({step['script']})",
                    "código de salida 0",
                    f"código {step.get('returncode')}; {step.get('reason', '')}".strip("; "),
                    Status.FAILED,
                    source="run_log.json",
                )
            )
    return items


CHECKS: tuple[Callable[[Context], list[Item]], ...] = (
    check_table2,
    check_tables_4_5,
    check_medians,
    check_stars,
    check_dispersion,
    check_moran,
    check_wasserstein,
    check_pi,
    check_local_time,
    check_figures,
    check_fig1_scales,
    check_steps,
)


# ------------------------------------------------------------------ informe
@dataclass
class Report:
    items: list[Item]
    meta: dict = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)

    @property
    def counts(self) -> Counter:
        return Counter(item.status for item in self.items)

    @property
    def ok(self) -> bool:
        """True si ningún ítem falla (los omitidos y las desviaciones documentadas no cuentan)."""
        return self.counts[Status.FAILED] == 0

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "id": i.id,
                    "area": i.area,
                    "name": i.name,
                    "target": i.target,
                    "result": i.result,
                    "status": i.status.value,
                    "ref": i.ref,
                    "source": i.source,
                    "source_date": i.source_date.isoformat(timespec="seconds")
                    if i.source_date
                    else "",
                    "note": i.note,
                }
                for i in self.items
            ]
        )

    def summary_line(self) -> str:
        c = self.counts
        parts = [
            f"{c[Status.EXACT] + c[Status.WITHIN]} ✅",
            f"{c[Status.DOCUMENTED]} 🟡",
            f"{c[Status.INFO]} ℹ️",
            f"{c[Status.FAILED]} ❌",
            f"{c[Status.SKIPPED]} ⏭️",
        ]
        return " · ".join(parts)

    def summary_plain(self) -> str:
        """Resumen sin emojis, para imprimir en la consola de Windows (cp1252)."""
        c = self.counts
        return (
            f"{c[Status.EXACT] + c[Status.WITHIN]} ok, {c[Status.DOCUMENTED]} documentadas, "
            f"{c[Status.INFO]} informativas, {c[Status.FAILED]} fallas, "
            f"{c[Status.SKIPPED]} omitidas"
        )

    def to_markdown(self) -> str:
        meta = self.meta
        lines = ["# Informe de reproducción", ""]
        header = [
            ("Generado", meta.get("generated_at")),
            ("Versión del código", meta.get("commit")),
            ("Modo de la ejecución", meta.get("mode")),
            ("Python y librerías", meta.get("versions")),
        ]
        for key, value in header:
            if value:
                lines.append(f"- **{key}:** {value}")
        lines += [
            "",
            f"**Resultado:** {'sin fallas' if self.ok else 'HAY FALLAS'}: {self.summary_line()}.",
            "",
            "✅ coincide con el paper (exacto o al redondeo/tolerancia acordada) · "
            "🟡 no coincide y la causa está documentada (se vigila que no cambie) · "
            "ℹ️ resultado propio sin objetivo del paper · "
            "❌ falla · ⏭️ omitido (falta la salida)",
            "",
        ]
        for area in dict.fromkeys(i.area for i in self.items):
            lines += [
                f"## {area}",
                "",
                "| Ítem | Objetivo | Resultado | Estado | Ref. |",
                "|---|---|---|---|---|",
            ]
            for i in (x for x in self.items if x.area == area):
                note = f" *({i.note})*" if i.note else ""
                stale = ""
                if is_stale(i, meta.get("run_started")):
                    stale = f" *(de una corrida anterior: {i.source_date:%Y-%m-%d %H:%M})*"
                cells = [
                    i.name,
                    i.target or "—",
                    f"{i.result}{note}{stale}".replace("|", "/"),
                    f"{i.status.symbol} {i.status.label}",
                    i.ref or "—",
                ]
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
        if self.steps:
            lines += [
                "## Pasos de la ejecución",
                "",
                "| Paso | Script | Estado | Duración | Salida | Motivo |",
                "|---|---|---|---|---|---|",
            ]
            for step in self.steps:
                command = " ".join([step["script"], *step.get("args", [])])
                seconds, code = step.get("seconds"), step.get("returncode")
                duration = f"{seconds:.0f} s" if seconds is not None else "—"
                label = " (**DIAGNÓSTICO, no es una réplica**)" if step.get("diagnostic") else ""
                reason = (step.get("reason") or "—").replace("|", "/")
                lines.append(
                    f"| {step['id']} | `{command}`{label} | {step['status']} | {duration} | "
                    f"{'—' if code is None else code} | {reason} |"
                )
            lines.append("")
        return "\n".join(lines)


def build_report(ctx: Context, meta: dict | None = None) -> Report:
    """Arma el informe con todas las comprobaciones, en orden."""
    items: list[Item] = []
    for check in CHECKS:
        items.extend(check(ctx))
    meta = dict(meta or {})
    run_log = ctx.run_log or {}
    if run_log:
        meta.setdefault("mode", run_log.get("mode"))
        if run_log.get("started") and "run_started" not in meta:
            meta["run_started"] = datetime.fromisoformat(run_log["started"])
    return Report(items=items, meta=meta, steps=list(run_log.get("steps", [])))


def write_report(report: Report, directory: Path, *, publish_to: Path | None = None) -> list[Path]:
    """Escribe `report.md` y `report.csv` en `directory` (y copia el `.md` a `publish_to`).

    Devuelve las rutas escritas. El informe solo tiene agregados, así que `publish_to` (p. ej.
    `docs/reproduction_report.md`) se puede versionar.
    """
    directory.mkdir(parents=True, exist_ok=True)
    markdown = report.to_markdown()
    paths = [directory / "report.md", directory / "report.csv"]
    paths[0].write_text(markdown, encoding="utf-8")
    report.to_frame().to_csv(paths[1], index=False)
    if publish_to is not None:
        publish_to.parent.mkdir(parents=True, exist_ok=True)
        publish_to.write_text(markdown, encoding="utf-8")
        paths.append(publish_to)
    return paths


def is_stale(item: Item, run_started: datetime | None) -> bool:
    """True si la salida del ítem es anterior al inicio de la ejecución (corrida anterior)."""
    return bool(item.source_date and run_started and item.source_date < run_started)


__all__ = [
    "CHECKS",
    "Context",
    "Item",
    "Report",
    "Status",
    "build_report",
    "check_figures",
    "is_stale",
    "write_report",
]
