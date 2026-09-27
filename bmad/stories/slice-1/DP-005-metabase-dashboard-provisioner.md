---
id: DP-005-metabase-dashboard-provisioner
title: "Metabase + Policy Portfolio dashboard (idempotent provisioner)"
status: Done
type: Story
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 3
labels: [data-platform, bi, python]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As* **underwriting / portfolio**, *I want* the `policy_portfolio` data product rendered as a Metabase
dashboard, provisioned as code *so that* the BI layer is reproducible, not click-built.

## Acceptance criteria
- Metabase deployed (app DB on CNPG); dashboard renders `policy_portfolio` (6 cards).
- Provisioner is idempotent (login-first session logic) and re-runnable.
- Provisioner targets the in-cluster service (`metabase.data-platform.svc:3000`) since the ingress is
  SSO-gated; reads creds from Vault; secret-free.

## Code
`metabase/provision_dashboard.py` (this repo). Deploy: `manifests/data-platform/05-metabase.yaml`.

## Status
✅ Done — dashboard id 2 renders; provisioner re-runnable.
