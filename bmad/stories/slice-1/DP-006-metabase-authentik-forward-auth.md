---
id: DP-006-metabase-authentik-forward-auth
title: "Authentik forward-auth gate on Metabase"
status: Done
type: Story
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 2
labels: [data-platform, security]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As the* **security engineer**, *I want* Metabase gated by Authentik at the ingress *so that* BI over
CONFIDENTIAL policy data is behind SSO+MFA (Metabase OSS has no native OIDC).

## Acceptance criteria
- Ingress carries the Authentik forward-auth annotations (embedded outpost, provider `metabase`).
- Unauthenticated request → 302 to `…/outpost.goauthentik.io/start?rd=/`.
- In-cluster service stays ungated so the provisioner/pipeline can reach it.

## Deployment
`manifests/data-platform/05-metabase.yaml` (ingress annotations). Authentik provider pk 23.

## Status
✅ Done — ingress 302 → Authentik confirmed; svc ungated.
