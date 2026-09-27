---
id: DP-E1-policy-portfolio-slice
title: "Epic — Policy Portfolio thin vertical slice"
status: In Progress
type: Epic
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 13
labels: [data-platform, epic]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

# Epic — Policy Portfolio thin vertical slice

One live source (Policy) → just-enough medallion (raw → curated → business) → one data product
(`business.policy_portfolio`) → BI (Metabase), on a light-first stack (dbt + CNPG + Metabase).

**Doctrine:** thin vertical slice per live source — NOT a generic connector framework or heavy OLAP
(ClickHouse/Kafka) for sources that don't exist yet (need-first gate). See `docs/prd.md`,
`docs/architecture.md`.

## Child stories
- DP-001 Analytics medallion DB (CNPG raw/curated/business)
- DP-002 Ingest: prod policy DB → `raw` (read-only role, full-refresh COPY)
- DP-003 dbt staging over the 3 real policy tables + source tests
- DP-004 `policy_portfolio` mart (GWP proxy, TIV, counts)
- DP-005 Metabase + Policy Portfolio dashboard (idempotent provisioner)
- DP-006 Authentik forward-auth gate on Metabase
- DP-007 Confirm money/premium semantics with Policy domain

## Definition of Done (epic)
Pipeline runs prod → raw → dbt → `business.policy_portfolio` with tests green; the data product renders
in Metabase behind Authentik; code is secret-free + reproducible (committed code, idempotent provisioner).
