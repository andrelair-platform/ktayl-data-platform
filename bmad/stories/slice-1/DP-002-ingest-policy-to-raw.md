---
id: DP-002-ingest-policy-to-raw
title: "Ingest: prod policy DB → raw (read-only role, full-refresh COPY)"
status: Done
type: Story
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 3
labels: [data-platform, backend, ingestion]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As the* **platform**, *I want* the 3 real policy tables landed 1:1 into `raw` on a schedule *so that*
downstream dbt models have a stable, isolated copy to build on.

## Acceptance criteria
- Dedicated read-only `analytics_ro` role on the prod policy DB (SELECT on the 3 tables only).
- Ingest CronJob does an atomic per-table full-refresh COPY (truncate + load) into `raw.*`.
- Runs daily (02:00 UTC); on-demand via `kubectl create job`.

## Code / deployment
Code: `ingest/ingest_policy.sh` (this repo). Deploy: `manifests/data-platform/04-pipeline.yaml`
CronJob git-clones this repo and runs the script (deployment-vs-code separation).

## Status
✅ Done — CronJob green; `raw.*` landed.
