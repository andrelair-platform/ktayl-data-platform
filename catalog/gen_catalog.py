#!/usr/bin/env python3
"""Generate the data catalog page from the governance registry + the dbt model contracts.

A lightweight, no-running-service catalog surface (ADR-013): it unifies the two sources of truth we
already maintain — `lake/registry/datasets.yaml` (governed raw datasets: classification/PII/owner/
retention/destination) and the committed dbt model contracts (`**/models/**/_*.yml`) — into one
discoverable page, `docs/data-catalog.md`, plus a **PII register** (the GDPR Art. 30 / EU AI Act Art. 10
data-map artefact). Deterministic (no timestamps/network) so CI can drift-gate it: regenerate + `git
diff` must be clean. OpenMetadata is the on-trigger upgrade (ADR-013), not this.

Run: `python3 catalog/gen_catalog.py` (needs PyYAML).
"""
from __future__ import annotations
import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "lake" / "registry" / "datasets.yaml"
MODEL_ROOTS = [REPO / "dbt" / "models", REPO / "lake" / "dbt_duckdb" / "models"]
OUT = REPO / "docs" / "data-catalog.md"

_GRAIN_RE = re.compile(r"[Gg]rain\s*=\s*([^.;,)\n]+)")
_LAYER_ORDER = {"staging → curated": 0, "mart": 1, "mart · fact": 2, "mart · MDM dim": 3, "—": 9}


def _load_yaml(path: Path) -> dict:
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def _project_of(path: Path) -> str:
    rel = path.relative_to(REPO).as_posix()
    return "dbt-duckdb (lake)" if rel.startswith("lake/") else "dbt-postgres"


def _layer_of(path: Path) -> str:
    rel = path.relative_to(REPO).as_posix()
    if "/staging/" in rel:
        return "staging → curated"
    if "/marts/mdm/" in rel:
        return "mart · MDM dim"
    if "/marts/facts/" in rel:
        return "mart · fact"
    if "/marts/" in rel:
        return "mart"
    return "—"


def _grain_of(description: str | None) -> str:
    if not description:
        return "—"
    m = _GRAIN_RE.search(description)
    return m.group(1).strip() if m else "—"


def _collect_models() -> list[dict]:
    models: list[dict] = []
    for root in MODEL_ROOTS:
        for yml in sorted(root.rglob("_*.yml")):
            doc = _load_yaml(yml)
            for model in doc.get("models", []) or []:
                cols = model.get("columns", []) or []
                col_tests = sum(1 for c in cols if c.get("tests"))
                has_pii = any((c.get("meta") or {}).get("pii") for c in cols)
                models.append(
                    {
                        "name": model.get("name", "?"),
                        "project": _project_of(yml),
                        "layer": _layer_of(yml),
                        "grain": _grain_of(model.get("description")),
                        "cols": len(cols),
                        "col_tests": col_tests,
                        "pii": "⚠ yes" if has_pii else "no",
                    }
                )
    models.sort(key=lambda m: (m["project"], _LAYER_ORDER.get(m["layer"], 9), m["name"]))
    return models


def _source_pii_columns() -> list[tuple[str, str, str]]:
    """(column, source.table, classification) for any dbt source column flagged meta.pii."""
    out: list[tuple[str, str, str]] = []
    for root in MODEL_ROOTS:
        for yml in sorted(root.rglob("_*.yml")):
            doc = _load_yaml(yml)
            for src in doc.get("sources", []) or []:
                for tbl in src.get("tables", []) or []:
                    for col in tbl.get("columns", []) or []:
                        meta = col.get("meta") or {}
                        if meta.get("pii"):
                            label = f"{src.get('name')}.{tbl.get('name')}"
                            out.append((col["name"], label, meta.get("classification", "personal-data")))
    return out


def _md_table(header: list[str], rows: list[list[str]]) -> str:
    line = "| " + " | ".join(header) + " |"
    sep = "|" + "|".join("---" for _ in header) + "|"
    body = ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join([line, sep, *body])


def build() -> str:
    reg = _load_yaml(REGISTRY)
    datasets = reg.get("datasets", []) or []
    models = _collect_models()

    # PII register — datasets.yaml is authoritative; add source-contract PII columns not already covered.
    pii_rows: list[list[str]] = []
    seen: set[str] = set()
    for ds in datasets:
        if not ds.get("pii"):
            continue
        for col in ds.get("pii_columns", []) or []:
            seen.add(col.lower())
            pii_rows.append(
                [f"`{col}`", ds.get("name", "?"), ds.get("classification", "personal-data"),
                 "raw, curated", "`assert_no_pii_in_serving` (blocks business/gold)"]
            )
    for col, label, classification in _source_pii_columns():
        if col.lower() in seen:
            continue
        seen.add(col.lower())
        pii_rows.append([f"`{col}`", label, classification, "raw, curated",
                         "`assert_no_pii_in_serving` (blocks business/gold)"])

    ds_rows = [
        [d.get("name", "?"), d.get("layer", "—"), d.get("classification", "—"),
         "⚠ yes" if d.get("pii") else "no", d.get("source", "—"),
         f"`{d.get('producer', '—')}`", d.get("retention", "—"), f"`{d.get('destination', '—')}`"]
        for d in datasets
    ]
    model_rows = [
        [m["name"], m["project"], m["layer"], m["grain"], str(m["cols"]), str(m["col_tests"]), m["pii"]]
        for m in models
    ]

    parts = [
        "# Data catalog — ktayl Data Platform",
        "",
        "> **Auto-generated** by `catalog/gen_catalog.py` from `lake/registry/datasets.yaml` + the dbt",
        "> model contracts (`**/models/**/_*.yml`). **Do not edit by hand** — run",
        "> `python3 catalog/gen_catalog.py`; CI drift-gates it (regenerate + `git diff` must be clean).",
        ">",
        "> This is the platform's lightweight catalog/discovery surface. A standing catalog service",
        "> (**OpenMetadata**) is deferred until a trigger fires — see",
        "> [ADR-013](architecture/adr/ADR-013-metadata-catalog-registry-now-openmetadata-on-trigger.md).",
        "",
        f"**At a glance:** {len(ds_rows)} governed raw dataset(s) · {len(model_rows)} warehouse model(s) · "
        f"{len(pii_rows)} PII column(s) under governance.",
        "",
        "## Lake (storage)",
        "",
        _md_table(
            ["Property", "Value"],
            [["Bucket", f"`{reg.get('bucket', '—')}`"], ["Region", reg.get("region", "—")],
             ["Encryption", reg.get("encryption", "—")], ["Versioning", str(reg.get("versioning", "—"))],
             ["Layout", f"`{reg.get('layout', '—')}`"]],
        ),
        "",
        "## Governed datasets (raw lake)",
        "",
        "The version-controlled registry of what lands in the lake (ADR-008 governance spine).",
        "",
        _md_table(
            ["Dataset", "Layer", "Classification", "PII", "Source", "Producer", "Retention", "Serving destination"],
            ds_rows,
        ),
        "",
        "## Warehouse models (serving)",
        "",
        "Derived dbt models (the serving medallion). `Project` = which dbt project builds it; PII should be",
        "**no** for every serving model (enforced by the PII gate — a `⚠ yes` here is a governance alarm).",
        "",
        _md_table(
            ["Model", "Project", "Layer", "Grain", "Columns", "Column tests", "PII"],
            model_rows,
        ),
        "",
        "## PII register (GDPR Art. 30 data-map · EU AI Act Art. 10 data-governance)",
        "",
        "Every column under PII governance, where it is allowed to live, and the control that enforces it.",
        "Direct identifiers may land in `raw`/`curated` (encrypted, private, access-gated) but are **blocked",
        "from the served `business`/`gold` layer** by `tests/assert_no_pii_in_serving.sql` (fails the build",
        "on violation). Formalising a golden Customer/Party record is deferred — see",
        "[ADR-014](architecture/adr/ADR-014-customer-party-mdm-golden-record-trigger.md).",
        "",
        _md_table(
            ["Column", "Dataset / source", "Classification", "Allowed layers", "Enforcement"],
            pii_rows,
        ),
        "",
    ]
    return "\n".join(parts) + "\n"


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    new = build()
    old = OUT.read_text() if OUT.exists() else ""
    if new != old:
        OUT.write_text(new)
        print(f"wrote {OUT.relative_to(REPO)}")
    else:
        print("data catalog already up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
