---
id: DP-004-policy-portfolio-mart
title: "policy_portfolio mart (GWP proxy, TIV, counts)"
status: Done
type: Story
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 5
labels: [data-platform, dbt, domain-logic]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As* **underwriting / portfolio**, *I want* a `policy_portfolio` data product (grain = policy) with GWP
proxy, TIV, premiums and counts *so that* I can steer the book (P2 margin, P1/P3 exposure).

## Acceptance criteria
- `business.policy_portfolio` builds from the curated staging models.
- 26 dbt tests pass; verified rows (seeded `[TEST]` policy → GWP proxy €12k / TIV €1M).
- Money handled as BIGINT minor units (÷100 → EUR); GWP is a **proxy** until DP-007 confirms semantics.

## Code
`dbt/models/marts/policy_portfolio.sql` + `_policy_portfolio.yml`.

## Status
✅ Done — mart built, tests pass, rows verified.
