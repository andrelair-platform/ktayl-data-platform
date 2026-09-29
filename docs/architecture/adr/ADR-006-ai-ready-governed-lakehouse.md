# ADR-006 — Target data architecture: an AI-ready governed lakehouse (direction + phased roadmap)

- **Status:** Proposed (direction-setting). Extends ADR-1 (light-first stack) and ADR-2 (thin vertical slice); supersedes nothing.
- **Date:** 2026-09-29
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS (organisational context — **not** Retrieva / not a cert deliverable)
- **Board:** Data Platform (#5)
- **Decider:** owner (architecture call)

## Context

Long-run, the insurance IS needs a **governed, clean data layer** that models and AI can be built on
(pricing/rating, fraud & SIU, churn, reserving, and RAG over documents). Today the platform is at
**Slice 1**: a thin medallion (`raw` → `curated` → `business`) in CNPG Postgres, fed from one source
(the policy service), served through Metabase (see `../architecture.md`).

The risk this ADR addresses is **not** "we lack a lake" — it is that data usable for AI must be *clean,
governed, and trustworthy by construction*. "Data lake + warehouse" is plumbing; the value comes from
the **governance/quality spine** on top of it. Garbage-in → biased-models-out is the failure this
prevents.

This is also a **compliance control**, not gold-plating — the regulatory "because":
- **EU AI Act Art. 10** mandates data governance for AI systems (relevance, representativeness,
  accuracy, bias management on training/validation data).
- **Solvency II** carries a **data-quality** directive (data must be *accurate, complete, appropriate*).
- **GDPR** governs PII in training sets (+ Art. 22 on automated decisions).
→ Evidence for cert blocs **BC02** (concevoir) / **BC03** (déployer & sécuriser).

**This ADR sets the target the slices grow toward. It does NOT authorize an upfront build.** The
need-first / thin-slice doctrine (ADR-2, `AGENTS.md`, `cloud-adoption.md`) still governs sequencing:
every phase below is triggered by a *real* source/model/volume, never a date.

## Decision

1. **One lakehouse, not a separate lake + a separate warehouse.** Running a Hadoop-style lake *and* an
   MPP warehouse on a 6-node laptop cluster is ops-suicide. The right-sized shape reuses what we run:
   - **Lake substrate** = **MinIO** (S3, already on the controller) holding **open-table** (Apache
     Iceberg) `bronze`/`silver` at scale.
   - **Warehouse serving** = **gold marts in CNPG Postgres** (what Metabase / apps / models read).
   - **Compute** = **DuckDB** (embedded, elegant at our scale) → Trino only if we outgrow it.
   - **Transform** = **dbt** (owns all transforms + tests) · **BI** = **Metabase**.
   - Postgres-only **stays the default until data volume/variety actually demands object tables** — the
     lakehouse is the *evolution* of Slice 1's medallion (phase P6), not a rewrite.

2. **Medallion is the quality ladder** (`bronze` = raw landing · `silver` = typed/cleaned/conformed ·
   `gold` = governed business marts). Already in place; formalise the **promotion gates** between layers.

3. **Ingestion = CDC + batch, standardised.** Real-time via **Debezium → NATS JetStream** (already
   built for claims); batch via git-cloned CronJobs; external feeds via the **Integration Platform
   (#25)**. Contract: *every domain DB → bronze* (read-only sources, no cross-domain writes — ADR-5).

4. **The clean-data governance spine (5 disciplines) — this is the actual requirement:**
   1. **Data contracts** — each producing domain declares schema + semantics + freshness SLA, versioned
      in *its* repo. Clean data starts at the source, not in downstream cleanup.
   2. **Quality gates** — dbt tests + Great Expectations/Soda on `silver→gold`: not-null, unique keys,
      referential integrity, freshness, **and business invariants** (premium ≥ 0, reserve ≤ limit).
      Promotion **blocked on failure** (same shape as the live QA gate; cf. the GWP `unique` tripwire).
   3. **MDM / golden records (#20)** — dedup + canonical customer/policy/claim. *The* thing that makes
      cross-domain data trustworthy for a model. Graduates from parked when a 2nd domain shares entities.
   4. **Catalog + lineage** — ownership, discoverability, PII tags, "where did this column come from."
      **dbt docs** gives lineage + catalog for free first; OpenMetadata/DataHub only if it earns it.
   5. **PII classification for training data** — reuse Presidio + the P0–P3 data classes + default-deny
      egress; mask/pseudonymise PII in the gold/feature layer and log provenance.

5. **AI serving layer (built last, on top of governed gold):** governed gold marts → a **feature store**
   (Feast) *when a model needs it* → ML models + RAG (reuse the Retrieva / `rag-ingest` / Qdrant
   pattern). Never before a real model exists.

6. **Stay light (reaffirms ADR-1).** No Spark / Kafka / ClickHouse / heavy managed catalog until a real
   source or scale demands it. The need-first gate is the guard against over-building.

## Phased roadmap (dependency- and value-ordered; each phase is independently useful — trigger on need, not date)

| Phase | Increment | Trigger |
|---|---|---|
| **P0** ✅ | Slice 1 — policy medallion + GWP/TIV mart + Metabase | done |
| **P1** | Land **claims CDC** into `bronze` (events already emitted by the strangler) + persist/catalog | claims CDC is live |
| **P2** | **Quality gates** — dbt tests + freshness + business invariants on `silver→gold`; block promotion | ≥1 mart consumed for a decision |
| **P3** | **Catalog + lineage** via dbt docs (ownership, PII tags) | ≥2 sources/marts to navigate |
| **P4** | **Data contracts** — per-domain schema + SLA, versioned; CI check producer↔contract | a source schema change breaks a mart |
| **P5** | **MDM / golden records** (#20) | a 2nd domain shares an entity (customer/policy/claim) |
| **P6** | **Object-table lakehouse** — Iceberg on MinIO + DuckDB/Trino | volume/variety (unstructured, history) exceeds CNPG comfort |
| **P7** | **Feature store** (Feast) + first ML model | a model is actually being built |
| **P8** | **PII governance for training** — mask/pseudonymise + provenance in gold/feature layer | first model trains on personal data |

## Consequences

**Positive**
- A trustworthy, governed, **AI-ready** data layer that grows with the IS; clean data *by construction*
  (contracts + gates + MDM), not by after-the-fact cleanup.
- Reuses existing primitives (MinIO, Debezium/NATS CDC, dbt, CNPG, Metabase, Presidio) — minimal new
  heavy systems.
- Named compliance controls in place (AI Act Art. 10, Solvency II data quality, GDPR) → cert evidence.

**Negative / costs**
- Governance is **ongoing** work (contracts, tests, catalog upkeep) — a discipline, not a one-off.
- Ops discipline required to **not** over-build — the need-first gate must be enforced each phase.

**Risk if the spine is skipped** (why it matters): biased/garbage models, **PII leaking into a model**,
silent source schema drift breaking marts, stale features. The gates above exist to prevent exactly these.

## Alternatives considered

- **Separate Hadoop-style lake + MPP warehouse** — rejected: ops-suicide on 6 laptops; two platforms to
  run for one job.
- **Postgres-only, forever** — fine *now* (Slice 1 is this), but won't scale to multi-source /
  unstructured / ML-volume data. The lakehouse (P6) is the escape hatch, **deferred until needed**.
- **Heavy managed governance upfront** (DataHub/OpenMetadata, a full Great-Expectations platform) —
  deferred: dbt docs (lineage/catalog) + dbt tests (quality) cover the early need at a fraction of the ops.

## Links

- Extends: ADR-1 (light-first stack), ADR-2 (thin vertical slice). Reaffirms the need-first gate.
- Rules: `cloud-adoption.md` (need-first), `conventions.md` (deployment-vs-code), `llmops.md`,
  `testing.md` / `qa-gate.md` (quality-gate shape), `project-governance.md` (SA artefact set).
- **Org-site pairing (TODO):** add an overview page on `minicloud-platform-docs` pointing to this ADR
  (per `documentation.md` *mandatory pairing*) once P1 lands.
- Numbering note: continues the `architecture.md` ADR list (1–4); ADR-5 ("no shared operational DB") is
  the inline reference on `architecture.md` line 16.
