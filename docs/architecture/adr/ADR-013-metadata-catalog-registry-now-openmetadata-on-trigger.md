# ADR-013 — Metadata catalog: registry + generated page now, OpenMetadata on trigger

- **Status:** Accepted (2026-11-21). Records that the data platform's catalog/metadata surface is, for now,
  the **version-controlled `datasets.yaml` registry + the dbt model contracts + a generated static
  catalog page** — and that a **standing catalog service (OpenMetadata)** is adopted only when a concrete
  trigger fires. A *tooling-deferred* entry (we control it), complementing ADR-011/012.
- **Date:** 2026-11-21
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS · **Board:** Data Platform (#5)
- **Decider:** owner (architecture call).

## Context

A **metadata catalog** answers, across *every* dataset and tool: *what is it, where did it come from, who
owns it, is it sensitive, what breaks if I change it, can I trust it?* It is the backbone of discovery,
impact analysis, and — for an insurer — the **GDPR Art. 30 data map / EU AI Act Art. 10 data-governance
evidence**.

Today that metadata **exists but is fragmented** across four non-intersecting places:

| Metadata | Lives in | Blind spot |
|---|---|---|
| Technical (tables/columns/types) | dbt docs + model contracts | only dbt's world |
| Lineage | dbt graph + Dagster asset graph | two *partial* graphs, no column-level, don't reach Metabase/S3 |
| Business/governance (classification, PII, owner, retention) | `lake/registry/datasets.yaml` | hand-maintained, not linked to live schema |
| Semantic | Cube model | isolated from the rest |

At the **current scale — ~2 domains, one BI consumer, one engineer who knows where everything is** — a
standing catalog service (OpenMetadata = the app **+ OpenSearch/Elasticsearch + a metadata DB +
ingestion jobs**) would be **pure operational tax with no discovery problem to solve**. Same need-first
logic as ADR-011.

## Decision

**Keep the catalog lightweight now:** `datasets.yaml` (governed raw datasets) + the dbt model contracts
(`models/**/_*.yml`) remain the source of truth, and a committed **generated catalog page**
(`docs/data-catalog.md`, built by `catalog/gen_catalog.py`) unifies them into one discoverable surface —
including a **PII register** (the compliance artefact). No running service. Adopt **OpenMetadata**
(not DataHub — it needs Kafka; we run NATS, and OpenMetadata's dbt/Dagster/Metabase connectors are
first-class and lighter) when a trigger below fires.

## Triggers (adopt OpenMetadata when ANY fires) — *tooling-deferred*

1. **Consumer-discovery friction** — more than a couple of people/teams consuming data and asking "where
   is X / can I trust X / what does this column mean?" (the generated page stops scaling to real search).
2. **Domain count ≳ 5–8 warehoused domains** — fragmentation stops being holdable in one head / one page.
3. **A compliance driver** — a defensible **data map / ROPA / PII register** is required for a GDPR or
   DORA audit at a fidelity the static page can't sustain (live lineage + classification inheritance).
4. **Column-level impact analysis** becomes a recurring real need (source schema changes keep breaking
   downstream silently; you need "what breaks if `holder_name` changes" answered across *all* tools).

None are firing today → **no service now**, by design. The generated page is the proportionate answer.

## Build-time discipline (when OpenMetadata is adopted)

- **Seed from what exists** — ingest the dbt metadata + `datasets.yaml` classifications first (don't
  re-tag by hand); the registry is the migration seed, not throwaway.
- **Classification inheritance** — configure PII tags to propagate *down* lineage (tag `holder_name` once
  → every derived column flagged) so the `assert_no_pii_in_serving` gate and the catalog agree.
- **Right-size the search backend** — OpenSearch is the heavy dependency; size it for the cluster, and
  schedule ingestion (not continuous) to keep it cheap.

## Consequences

- **Positive:** discovery + a PII register are delivered **now, with zero new running pods**; the deferral
  is an auditable, triggered decision; the registry doubles as the future OpenMetadata seed.
- **Negative / watch:** the generated page is **not** searchable, has **no live column-level lineage**, and
  only covers what's in `datasets.yaml` + the dbt contracts — if it drifts from reality it misleads, so it
  is **CI drift-gated** (regenerate + `git diff` must be clean). When the page stops answering real
  questions, that *is* trigger #1.

## Related

ADR-006 (governance spine / P-phase roadmap) · ADR-008 (Glue/OpenMetadata deferred; `datasets.yaml` is the
source of truth) · ADR-011 (need-first trigger register) · ADR-014 (MDM — a *consumer* of the catalog's
entity metadata) · `cloud-adoption.md` (need-first gate). Artefact: `docs/data-catalog.md`.
