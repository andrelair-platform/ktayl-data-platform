# Architecture — ktayl Data Platform (#5)

> Backfilled spine (brownfield, 2026-09-27). Records the conventions the built code already follows.

## System boundaries
```
ktayl-policy-service (prod Postgres, SoR)         [source — read-only via analytics_ro]
        │  ingest CronJob: pg COPY (full-refresh)
        ▼
CNPG dp-postgres / db=analytics:  raw ─► curated ─► business     [medallion, this platform owns it]
        │  dbt build (staging→marts + tests)
        ▼
Metabase (business schema)                        [serve — Authentik forward-auth at the edge]
```
- **Owns:** the `analytics` DB (raw/curated/business) + Metabase. **Reads:** the policy DB (read-only).
  **No** cross-domain DB writes; sources are read-only (ADR-005 no shared operational DB).

## Data model / SoR
- Source of truth stays the **domain services** (Policy). The platform holds **derived** copies only.
- `raw.*` = 1:1 landing; `curated` (stg_*) = typed/cleaned; `business.policy_portfolio` = the data product
  (grain = policy: GWP proxy, TIV, premiums, counts). Canonical model: `minicloud-platform-docs` → Canonical Data Model.
- **ERD (entity model + grain + PII + keys):** [`data-model/README.md`](data-model/README.md) — the raw
  landing contract + the conformed serving star (MDM dims / `fact_policy` / `policy_portfolio`). Kept in
  sync with the dbt model contracts (the machine-checked drift gate; dbt-warehouse carve-out, no `tbls`).
- **Data catalog + PII register:** [`data-catalog.md`](data-catalog.md) — auto-generated
  (`catalog/gen_catalog.py`, CI drift-gated) from `datasets.yaml` + the dbt contracts; the lightweight
  discovery surface + the GDPR Art. 30 / EU AI Act Art. 10 PII register. OpenMetadata deferred (ADR-013).

## Deployment (in minicloud-gitops, not here)
- `manifests/data-platform/`: namespace+quota, CNPG cluster, ESO secrets, netpols, ingest+dbt CronJobs,
  Metabase, ArgoCD app. CronJobs **git-clone this repo** to run the code (deployment-vs-code separation).

## AuthN/Z & secrets
- Vault `secret/platform/data-platform` → ESO → k8s secrets (CNPG roles, policy RO creds, Metabase).
- Metabase: Authentik forward-auth (embedded outpost, provider `metabase`); local admin behind it (OSS has
  no native OIDC). Provisioner uses the in-cluster service (ungated).

## Observability / failure modes
- CNPG PodMonitor; dbt source tests fail loudly on schema drift; ingest is atomic per table (truncate+load).
- **Failure:** policy DB down → ingest fails, marts keep last data. dbt test fail → build fails (no bad data
  served). Analytics DB loss → rebuild from source (RPO 24h acceptable — derived).

## ADRs (decisions)
- **ADR-1 Light-first stack** (dbt+CNPG+Metabase) over ClickHouse/Kafka — need-first on a constrained cluster.
- **ADR-2 Thin vertical slice** per live source — not a generic connector framework.
- **ADR-3 Code repo (`ktayl-data-platform`) ≠ deploy repo (`minicloud-gitops`)** — conventions.md.
- **ADR-4 Metabase forward-auth** (not native OIDC — OSS limitation).
- **ADR-6 Target: AI-ready governed lakehouse** — the direction the slices grow toward (lakehouse evolution of the medallion + the 5-discipline governance spine) + a need-first phased roadmap. Full ADR: [`architecture/adr/ADR-006-ai-ready-governed-lakehouse.md`](architecture/adr/ADR-006-ai-ready-governed-lakehouse.md).
- **ADR-7..11** (full set in [`architecture/adr/`](architecture/adr/)): gating-foundation · hybrid S3-lake/DuckDB/CNPG · Cube semantic layer · Dagster+dlt orchestration · the deferred-capability trigger register.
- **ADR-12 Lakehouse table format: Parquet now, Iceberg on trigger** — names the plain-Parquet→Iceberg gap as a *triggered* decision (CDC / time-travel / schema-evolution / scale-out engine), so "lakehouse pattern vs transactional lakehouse" reads as intent. Full ADR: [`architecture/adr/ADR-012-lakehouse-table-format-iceberg-trigger.md`](architecture/adr/ADR-012-lakehouse-table-format-iceberg-trigger.md).
- **ADR-13 Metadata catalog: registry + generated page now, OpenMetadata on trigger** (*tooling-deferred*) — the `datasets.yaml` registry + dbt contracts + the generated [`data-catalog.md`](data-catalog.md) are the catalog surface; a standing catalog service waits for a discovery/compliance/scale trigger. [`architecture/adr/ADR-013-metadata-catalog-registry-now-openmetadata-on-trigger.md`](architecture/adr/ADR-013-metadata-catalog-registry-now-openmetadata-on-trigger.md).
- **ADR-14 Customer/Party MDM: interim pseudonymous key now, golden record when a Party domain ships** (*data-blocked*, ADR-011 #4) — `dim_customer = md5(holder_name)` is a labelled interim join key, not a golden record; real match/merge/survivorship waits on a source Party domain. [`architecture/adr/ADR-014-customer-party-mdm-golden-record-trigger.md`](architecture/adr/ADR-014-customer-party-mdm-golden-record-trigger.md).
