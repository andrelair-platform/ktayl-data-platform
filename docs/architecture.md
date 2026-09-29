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
