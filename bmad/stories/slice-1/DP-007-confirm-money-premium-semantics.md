---
id: DP-007-confirm-money-premium-semantics
title: "Confirm money/premium semantics with the Policy domain"
status: Ready
type: Story
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 2
labels: [data-platform, domain-logic]
priority: P3
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As* **finance/actuarial**, *I want* the GWP/premium figures confirmed against the Policy domain's real
semantics *so that* `policy_portfolio.gwp` can be promoted from a **proxy** to an authoritative measure.

## Context
The mart currently assumes: money columns are BIGINT **minor units** (÷100 → EUR), and premium
annualisation assumes installments. Both are **unconfirmed** with the Policy domain (see AGENTS.md).

## Acceptance criteria
- Confirm the minor-units assumption + the annualisation rule with the Policy service owner.
- Update `dbt/models/marts/policy_portfolio.sql` if the semantics differ; keep tests green.
- Rename/re-document `gwp` from *proxy* to authoritative; note the decision in an ADR.

## Status
⬜ Open — the one remaining slice-1 story.
