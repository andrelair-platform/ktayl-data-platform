# ADR-009 — Semantic layer: Cube (self-hosted) over the dbt Semantic Layer; Metabase-native interim

- **Status:** Accepted. Engine chosen (Cube). **Minimal proof stood up on DEV (2026-11-19)** — a
  single-pod Cube over the gold mart serving the `policy_portfolio` cube; validated the Metabase-native
  SQL-API path (11 total / 8 active / 0.727 active-ratio). This is a **spike ahead of the trigger**
  (de-risks the choice), **not** the production build — the triggered prod build (Cube Store + HA + SSO
  ingress + Metabase wiring + the cross-domain metrics) still waits on the adoption trigger below.
- **Date:** 2026-11-19
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS (organisational context — not Retrieva / not a cert deliverable)
- **Board:** Data Platform (#5)
- **Decider:** owner (architecture call)
- **Relation:** implements **ADR-007 step 5** ("Serving + semantic layer"); sits on top of the
  ADR-008 serving store (CNPG gold marts). Does not change ADR-006/007/008.

## Context

The data platform now has a dimensional warehouse in CNPG (`analytics.lake`: `fact_policy` +
`dim_policy/customer/lob/period`, built by the dbt-duckdb medallion over the S3 lake) served to
**Metabase**. What it does **not** have is a **semantic layer** — a governed place where each business
metric (GWP, loss ratio, combined ratio, active-policy-count, …) is defined **once**, decoupled from the
physical tables, so every consumer gets the *same* number. Today a metric like "active policies" is
re-derived inside each Metabase question — the exact drift a semantic layer exists to prevent.

ADR-007 step 5 named this as the next layer and left the implementation open between **the dbt Semantic
Layer** and **Cube**. This ADR resolves that choice. The decision is dominated by **three platform
constraints**, not by which tool is "best" in the abstract:

1. **Sovereignty / self-hosted.** The platform runs no cloud SaaS in its data path (the thesis). The
   semantic layer's **serving endpoint** — what BI tools and apps query — must be self-hostable.
2. **Metabase is the BI consumer.** The layer must be consumable by Metabase **natively**, not via a
   connector we'd have to build.
3. **Resource-constrained + solo + need-first.** A standing service has a real cost on a 5-node cluster
   with tight quotas; we don't stand one up before a second consumer justifies it (`cloud-adoption.md`).

**Verified fact that drives the decision (2026-11, re-verify at build time):** MetricFlow (the dbt
Semantic Layer engine) was **relicensed Apache-2.0 in Oct 2025**, so the *engine* is now open and
standalone — but the **governed Semantic Layer *API* (the gateway BI tools connect to) still requires dbt
Cloud**. Self-hosted, dbt-SL gives you CLI/compile only, plus an **unofficial community REST wrapper**
(`metricflow-server`) — and **Metabase has no native connector to that wrapper** (its dbt-SL integration
targets dbt Cloud). So on *this* stack, dbt-SL cannot deliver "one governed definition of GWP, consumed
by Metabase" without either a US SaaS or a connector we'd build and maintain.

## Decision

1. **Target engine = Cube (self-hosted).** When the platform needs a real semantic layer, it is **Cube**,
   deployed on-cluster over the **CNPG gold marts** (ADR-008 serving store). Metabase consumes it
   **natively via Cube's SQL (Postgres-wire) API** — Cube presents as a database; no custom connector.
   Cube also exposes **REST + GraphQL** for apps and the AI layer, so a future second/third consumer
   reuses the *same* metric definitions.

2. **dbt Semantic Layer is REJECTED as the serving engine** — not because it's weak (metrics-as-code next
   to the dbt models is genuinely attractive for a dbt shop), but because its **self-hosted serving path
   to Metabase is dbt-Cloud-bound / immature**, which fails constraints 1 + 2. (Secondary: MetricFlow's
   **DuckDB adapter support is limited/community**, whereas Cube has mature Postgres + DuckDB drivers and
   would read the CNPG marts directly.)

3. **Interim (now) = Metabase-native semantic definitions.** Until the adoption trigger fires, the
   "semantic layer" is **Metabase Models + Metrics** — governed metric/dimension definitions held in
   Metabase, **zero new service**. This is exactly what ADR-007 step 5 literally prescribes
   ("Metabase models/dashboards"), and it is proportionate while there is **one** consumer (Metabase) and
   the headline metrics are still blocked on data (issue #28).

## Adoption trigger (when to stand up Cube — any one)

- A **second metric consumer** appears beyond Metabase — a custom app/API, a notebook, or the **AI layer**
  needing governed metrics (e.g. a RAG/agent answering "what was Q3 GWP?" must hit *one* definition).
- Metric logic starts **duplicating / drifting** across Metabase questions (the pain the layer removes).
- **Cross-domain metrics land** — Combined Ratio / loss ratio / RoRAC — after ktayl-core Phase-1b ships
  premiums/coverages (issue #28) and claims data is in the warehouse. These are *definitional* metrics
  that benefit most from a single source of truth.

Until then: **do not build it** (need-first). Define each real metric once in Metabase as we go, so the
definitions are ready to port to Cube cubes when the trigger fires.

## Consequences

- **Positive:** the serving endpoint stays **sovereign + self-hosted**; Metabase integration is **native**
  (no connector to build/maintain); one definition becomes reusable across BI **and** apps **and** AI via
  Cube's multi-protocol API; the interim path adds **no** service and matches ADR-007 verbatim; the
  decision is driven by stated, verified constraints (auditable).
- **Accepted cost:** Cube, when adopted, is **a new always-on service** (Node app + optional Cube Store
  for pre-aggregations) on a tight cluster — it passes the `cloud-adoption.md`/quota gate at that time.
  We **give up metrics-as-code-next-to-dbt-models** (dbt-SL's nicest property); Cube's data model is its
  own YAML/JS, a second modelling surface alongside dbt — accepted, because dbt still owns the
  **transforms** and Cube owns the **metrics/serving** (clean split), and Cube can reference the dbt
  models as its base tables.
- **Reversibility / exit:** Cube is open-source + self-hosted; the cubes are version-controlled YAML; a
  teardown is deleting the Deployment (metrics fall back to Metabase-native). The dbt marts underneath are
  untouched, so the exit is a no-op to the warehouse.
- **Re-verify-at-build-time:** the dbt-SL serving limitation is the crux; confirm it hasn't changed (dbt
  Labs shipping an official self-hosted serving gateway, or a native Metabase↔MetricFlow connector) before
  implementing — if it has, re-open this ADR.

## Alternatives considered

- **dbt Semantic Layer (MetricFlow)** — metrics-as-code, versioned/reviewed next to the dbt models,
  lineage-aware; the natural pick *if* dbt Cloud were acceptable. **Rejected** here: self-hosted serving to
  Metabase is dbt-Cloud-bound (official) or an unofficial REST wrapper with no Metabase connector; limited
  DuckDB adapter support. Would leave metrics defined in Metabase anyway → not a real semantic layer on
  this stack.
- **Metabase-native only (Models + Metrics), permanently** — lightest, no new service. **Adopted as the
  interim, rejected as the end state**: metric definitions are **locked inside Metabase** (not consumable
  by apps/APIs/notebooks/AI), governance is weaker (no code review/versioning of the metric graph), and it
  doesn't serve the cross-consumer goal once a second consumer exists.
- **No semantic layer (status quo — ad-hoc metrics per dashboard)** — rejected: it *is* the drift problem;
  acceptable only while there's a single dashboard author and trivial metrics, which the interim formalises.

## Related

- ADR-007 (step 5 = this layer) · ADR-008 (CNPG gold = what Cube queries) · ADR-006 (governed-lakehouse direction).
- Issue **#28** (Phase-1b premium/coverage marts — unblocks the definitional metrics that most justify Cube).
- `cloud-adoption.md` (need-first + the standing-service gate) · `platform-vs-information-system.md`
  (the semantic layer = a Platform *capability*; the metric *definitions* = IS).

**Sources (dbt-SL serving/self-hosting state, verified 2026-11-19):**
[MetricFlow Apache-2.0 relicense (Atlan)](https://atlan.com/know/ai-agent/semantic-layer/metricflow-apache-2-license-dbt-semantic-layer/) ·
[Self-hosted MetricFlow REST API (community)](https://github.com/AlexBoutou/metricflow-server) ·
[dbt Semantic Layer vs Cube (unwinddata)](https://unwinddata.com/dbt-semantic-layer-vs-cube) ·
[MetricFlow commands (dbt docs)](https://docs.getdbt.com/docs/build/metricflow-commands) ·
[State of semantic layers 2025 (altertable)](https://altertable.ai/blog/2025-07-01-state-semantic-layers-2025).
