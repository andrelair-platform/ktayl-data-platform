# SPRINT-OVERVIEW — Data Platform Slice 1 (Policy Portfolio)

Product: **ktayl Data Platform (#5)** · Home repo: `ktayl-data-platform` · Deploy: `minicloud-gitops`
Status: **Slice 1 LIVE (2026-09-27)**. Stories backfilled (brownfield) — built work marked Done.

> Process note: Slice 1 was built before these artefacts existed (a Path-C BMAD-gate miss). Backfilled +
> the `deployment-vs-code` rule added so it isn't repeated. PRD: `docs/prd.md` · Architecture: `docs/architecture.md`.

## Epic: DP-E1 — Policy Portfolio thin vertical slice
One live source (Policy) → medallion → one data product → BI, on a light-first stack.

| Story | Title | Status | DoD |
|---|---|---|---|
| DP-001 | Analytics medallion DB (CNPG raw/curated/business) | ✅ Done | CNPG live, schemas present |
| DP-002 | Ingest: prod policy DB → `raw` (read-only role, full-refresh COPY) | ✅ Done | CronJob green; raw.* landed |
| DP-003 | dbt staging over the 3 real policy tables + source tests | ✅ Done | stg_* build; accepted_values/unique/not_null pass |
| DP-004 | `policy_portfolio` mart (GWP proxy, TIV, counts) | ✅ Done | mart built, 26 tests pass, verified rows |
| DP-005 | Metabase + Policy Portfolio dashboard (idempotent provisioner) | ✅ Done | dashboard renders; provisioner re-runnable |
| DP-006 | Authentik forward-auth gate on Metabase | ✅ Done | ingress 302→Authentik; svc ungated |
| DP-007 | Confirm money/premium semantics with Policy domain | ✅ Done | units confirmed eurocents; GWP annualisation authoritative under a `unique(policy_id)` interim contract + tripwire (premium mgmt is a future domain) |

## Slice 2+ (planned — not started; need-first)
- DP-101 Second live source when the next domain ships → generalise ingestion from 2–3 real pipelines.
- DP-102 CDC (Debezium→NATS) over batch. · DP-103 MDM-keyed Customer 360 (once MDM exists).
- DP-104 Metabase→Postgres app-DB hardening already done; add SSO auto-login only if Metabase Enterprise.

## Follow-ups (tech debt from the backfill)
- Wire the per-product BMAD sync (thin caller `.github/workflows/bmad-sync.yml`) so these stories create issues on board #5.
- Repo standardisation remainder: CONTRIBUTING.md, CI (dbt build + yamllint), release-please, Docusaurus `website/`.
