# PRD — ktayl Data Platform (#5)

> **Backfilled (brownfield, 2026-09-27).** Slice 1 was built before this artefact existed — a Path-C
> process miss now corrected. This documents the product contract and the go-forward plan; it is the
> source doc, re-generated (not hand-patched) when the product changes.

## Problem & why
The insurer (ktayl-solution IS) has operational domains but **no analytical platform** — no way to turn
domain data into portfolio/pricing/exposure analytics. That directly blocks the two hardest industry
problems: **P2 margin** (loss/combined ratio, portfolio steering) and **P1/P3 exposure/accumulation**.
Building a heavy OLAP up-front for domains that don't exist yet is waste ("warehouse for empty
warehouses"), so the platform grows by **thin vertical slices**, one live source at a time.

## Users
- **Underwriting / portfolio** (GWP, TIV, concentration) · **Finance/actuarial** (loss/combined ratio,
  reserving — later) · **Risk** (accumulation — later) · **platform/EA** (the medallion + governance).

## Scope
- **Slice 1 (built):** Policy source → medallion → `policy_portfolio` data product → Metabase dashboard.
- **Out of scope (deferred, need-first):** ClickHouse/Kafka/Superset/OpenMetadata heavy stack; CDC;
  MDM-keyed Customer 360; multi-source marts — until a second live source ships.

## Non-functional requirements
- **Footprint:** fits the constrained 6-node cluster — CNPG 1 instance (3Gi), dbt/ingest CronJobs, Metabase
  ~1.5Gi. Namespace quota `data-platform` (req 1 CPU/1.5Gi, lim 4 CPU/4Gi).
- **Freshness:** daily (ingest 02:00 / dbt 02:30 UTC); on-demand via `kubectl create job`.
- **Availability/DR:** derived/rebuildable data → **RTO 8h / RPO 24h**, no PITR (rebuild from source). 1 instance.

## Security
- Data class: **CONFIDENTIAL** (policy/premium/exposure). Read-only `analytics_ro` role on the prod policy
  DB (SELECT on 3 tables only). Secrets via Vault→ESO; no secrets in code. Metabase gated by **Authentik
  forward-auth** at the ingress; in-cluster service ungated for the pipeline. Default-deny ingress netpols.

## Compliance
- **DORA:** an *Important supporting* ICT capability (analytics, not a CIF). **GDPR:** holds personal/
  commercial data → access-controlled + minimised. **Solvency II/IFRS 17:** the analytics layer that will
  feed reserving/portfolio metrics (later slices). Not an AI use case (no AI-Act tier) yet.

## Cost / capacity
- On-cluster only (no cloud). Light stack chosen to fit quotas; ClickHouse deferred behind a need-first gate.
- No LLM/token cost. Storage growth bounded (derived, full-refresh, small).

## KPIs / acceptance
- **Slice-1 DoD (met):** pipeline runs prod→raw→dbt→`business.policy_portfolio` with 26 passing tests; the
  data product renders in Metabase; secret-free + reproducible (committed code, idempotent provisioner).
- **Product KPI:** each new slice adds one real data product from a real live source with tests green.
