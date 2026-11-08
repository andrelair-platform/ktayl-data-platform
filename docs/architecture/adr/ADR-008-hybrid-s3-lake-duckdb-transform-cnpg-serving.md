# ADR-008 — Hybrid raw data lake: AWS S3 (lake) + DuckDB (transform) + CNPG (serving)

- **Status:** Accepted (architecture). Sub-decision *workload authentication* is OPEN (see Decisions-pending).
- **Date:** 2026-11-08
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS (organisational context — not Retrieva / not a cert deliverable)
- **Board:** Data Platform (#5)
- **Decider:** owner (architecture call)
- **Relation:** extends ADR-006 (target governed lakehouse) + ADR-007 (Data-Platform-first gating). Refines the
  **ingestion mechanism** of ADR-007's Slice 2; does **not** change its dependency ordering (MDM first, …).

## Context

ADR-007 established that the Data Platform depth + MDM is the gating foundation. This ADR decides **how the
raw→serving pipeline is built**: where raw data lands, which engine transforms it, and which engine serves BI.

**Why a cloud lake at all (honest, per `cloud-adoption.md` need-first gate).** At the current data scale
(MB→low-GB) CNPG alone would functionally suffice. S3 is adopted for three *stated* reasons, not an urgent
functional need: **(1)** a durable, cheap, **replayable raw archive** decoupled from the analytical DB
(storage/compute separation); **(2)** real **AWS/cloud data-engineering experience** (an explicit portfolio/
skill goal); **(3)** a clean landing contract that decouples producers from the warehouse. The genuine
*functional* trigger to lean harder on the lake is stated under Revisit-when.

**Why a warehouse separate from the sources, when sources are already Postgres.** Source DBs (policy, claims,
billing, ERP) are **OLTP silos** — normalized for writes, current-state, one domain, carrying production load.
The warehouse is **OLAP** — cross-domain, conformed, historical, modeled, isolated from production. The
decisive reason is **cross-domain conform**: a Combined Ratio needs earned premium (billing) + incurred claims
(claims) + expenses (ERP) + ceded RI, which live in *separate databases* and cannot be joined in place. (Same
pattern `ktayl-claims` already uses at domain level via its CQRS read-model; the warehouse is the cross-domain
version.) A warehouse is a **role**, not a technology.

**Why DuckDB for transform, not Athena/Redshift, and not CNPG-only.** DuckDB is a purpose-built columnar/
vectorized OLAP engine that **reads Parquet from S3 natively** — which *eliminates a custom S3→CNPG loader*.
Athena/Glue were deferred (no second managed SQL engine); Redshift is rejected (always-on, ~$180/mo would
exhaust the $106 credits). CNPG-only would work but is row-oriented OLTP doing OLAP and needs the bespoke
Parquet→COPY loader.

**Why CNPG for serving, not DuckDB.** DuckDB is **embedded/single-process**, not a concurrent SQL service;
**Metabase** wants a live concurrent endpoint — Postgres's home turf (the hosted DuckDB answer, MotherDuck, is
paid SaaS + a new dependency). So DuckDB is an excellent *transform* engine but a poor *serving* store.

## Decision

Adopt a **hybrid lakehouse**: **S3 = raw lake, DuckDB = transform engine, CNPG = serving store, Metabase = BI.**

```
domain extract (Parquet)
   → S3 RAW LAKE        versioned · manifest-after-upload · checksums · replayable      [AWS]
   → DuckDB + dbt-duckdb   reads S3 Parquet directly (httpfs); staging → curated → marts [ephemeral Job, on-cluster]
   → CNPG                   conformed serving marts (fact/dim, MDM-keyed)                 [on-cluster]
   → Metabase               dashboards / KPIs                                            [on-cluster]
Catalog/lineage: dbt docs (models) + a version-controlled YAML dataset registry for the S3 side. Glue deferred.
```

- **S3 raw lake** — one versioned, encrypted, private bucket; Hive-style layout
  (`raw/<domain>/<dataset>/schema_vN/ingest_date=…/batch=<uuid>/part-*.parquet` + `manifest.json`), a
  `quarantine/` prefix, per-domain prefix isolation. The **manifest is written only after all files upload +
  validate** (atomic completion marker). An **ingestion-control table** (in CNPG) tracks batch_id/dataset/
  status/counts/schema_version for **idempotent, replayable** loads — a retry must never duplicate records.
- **DuckDB transform** — runs as an **ephemeral in-cluster Job** (no always-on infra); `dbt-duckdb` reads the
  S3 raw Parquet, runs staging → curated → marts with dbt tests; **materializes the serving marts into CNPG**.
  (Curated Parquet MAY be written back to `s3://…/curated/` so that layer is also replayable — optional for MVP.)
- **CNPG serving** — holds only the conformed marts Metabase reads (thin serving layer; heavy compute is DuckDB).
- **Catalog** — **dbt docs** (warehouse model catalog + lineage) + a **YAML dataset registry** (owner/source/
  S3 prefix/format/schema version/classification/retention/destination) version-controlled in the repo. **Glue,
  Athena, Redshift, and a full metadata platform (OpenMetadata/DataHub) are DEFERRED.**
- **IaC vs runtime separation** — AWS resources via **OpenTofu in `minicloud-cloud`** (budget, data_lake, lake_iam,
  workload_identity); the DuckDB Job + ServiceAccount + config + observability via **ArgoCD** (deployment repo).
  The loader/transform **code** lives in `ktayl-data-platform` (code repo), per the repo-separation rule.

## Consequences

- **Positive:** no bespoke Parquet loader (DuckDB reads S3 directly); a real columnar engine for analytics; a
  replayable raw archive; Postgres stays the proven, Metabase-friendly serving layer; a credible, modern
  hybrid-cloud data-engineering project (storage/compute separation, idempotent ingestion, lineage) — not "an
  AWS service on a CV".
- **Accepted costs / boundaries:**
  - **Data round-trips cloud↔cluster** — producers are in-cluster → upload to S3 → DuckDB **downloads** from S3
    (billable **egress**) → CNPG. Cheap at this scale; name it (reconsider at volume).
  - **Two engines** (DuckDB transform + Postgres serve) — deliberate, each at its best layer.
  - **Cost:** S3 pennies/mo + ephemeral DuckDB (free, on-cluster). Guardrail: **AWS Budget $10/mo**, alerts at
    $5/$8/$10 + forecast (alerts are *not* hard caps — they can arrive after charges). Free-Tier is credit-based
    (no automatic 5 GB/12 mo assumption); start in S3 Standard, measure, add lifecycle tiers only when justified.
  - **DR boundary (critical):** the S3 raw lake is **NOT** the CNPG backup/DR strategy. Keep CNPG WAL archiving,
    backups, and restore drills separate; the lake enables *dataset replay*, not *database recovery*.
  - **Secrets:** **no permanent AWS keys** in manifests, Git, or OpenTofu state (see Decisions-pending).

## Decisions pending (to confirm before IaC)

- **Workload authentication (open).** The DuckDB Job needs scoped S3 read creds without static keys. Two valid
  no-static-key options:
  - **Vault AWS secrets engine** (recommended lean) — issues dynamic, short-lived STS creds; **reuses the Vault
    we already run** + ESO delivery; no new trust-anchor to stand up.
  - **IAM Roles Anywhere** — X.509-cert-based temporary creds for non-AWS workloads; fits our PKI/cert-manager,
    but more setup (trust anchor = a CA, profiles, credential helper). (EKS Pod Identity / IRSA is N/A — self-hosted k3s.)

## Alternatives considered

- **CNPG-only + a bespoke Parquet→COPY loader** — simplest/one engine, fully adequate at this scale, but builds
  and maintains a custom loader and runs OLAP on a row store. (Viable fallback.)
- **DuckDB all the way (DuckDB/MotherDuck as serving)** — one engine, but weak concurrent serving / Metabase fit;
  MotherDuck = paid SaaS. Rejected for serving.
- **Athena (SQL-on-S3)** — deferred: a second managed SQL engine with no added value given DuckDB + CNPG.
- **Redshift** — rejected: always-on ~$180/mo exhausts the credits.
- **Query sources directly / `postgres_fdw` / read-replicas** — gives load isolation at best; **no cross-domain
  conform, no history, no clean modeling** → cannot deliver the KPI roadmap. Rejected.

## Revisit when

- Multiple analytical engines need the same raw datasets, **or** cross-system discovery/governance warrants a
  real catalog (Glue/OpenMetadata), **or** Postgres serving exceeds acceptable performance/storage → promote
  DuckDB/the lake further, or add a managed warehouse.

## Related

- ADR-006 (governed lakehouse direction) · ADR-007 (Data-Platform-first gating + Slice 2 ordering).
- `minicloud-cloud` (AWS OpenTofu) · `cloud-adoption.md` (need-first gate) · the CNPG backup/DR discipline.
