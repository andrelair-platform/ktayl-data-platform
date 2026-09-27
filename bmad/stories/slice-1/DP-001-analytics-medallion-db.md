---
id: DP-001-analytics-medallion-db
title: "Analytics medallion DB (CNPG raw/curated/business)"
status: Done
type: Story
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 3
labels: [data-platform, database, devops]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As the* **platform/EA**, *I want* a dedicated analytics database with a medallion layout (`raw` →
`curated` → `business`) *so that* derived data is isolated from operational systems and organised by
refinement stage.

## Acceptance criteria
- CNPG cluster `dp-postgres` live in the `data-platform` namespace (analytics + metabase DBs).
- Schemas `raw`, `curated`, `business` present in the `analytics` DB.
- No cross-domain operational writes; sources are read-only (ADR — no shared operational DB).

## Deployment (minicloud-gitops)
`manifests/data-platform/02-postgres.yaml` (CNPG cluster + Database CR). Netpols Ingress-only
(Cilium apiserver-identity gotcha — see architecture).

## Status
✅ Done — CNPG live, schemas present.
