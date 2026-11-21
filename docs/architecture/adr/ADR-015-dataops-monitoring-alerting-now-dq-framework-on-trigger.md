# ADR-015 — DataOps monitoring: pipeline alerting + not-empty check now, DQ framework & full L2 on trigger

- **Status:** Accepted (2026-11-21). Records that the data platform closes the **silent-failure** gap now
  with **cheap pipeline alerting + a data-product not-empty assertion** (reusing the cluster's existing
  Prometheus/Alertmanager + the dbt build), and **defers** a standing data-quality framework
  (Great Expectations/Soda) and full live/integration testing until a trigger fires. A *tooling-deferred*
  entry complementing ADR-011/013.
- **Date:** 2026-11-21
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS · **Board:** Data Platform (#5)
- **Decider:** owner (architecture call).

## Context

The platform's DataOps today is **CI/CD-strong but monitoring-thin**: L0 static CI (ruff/yamllint/
shellcheck/dbt parse), GitOps deploy, Dagster run *history*, and **data-quality gates = 3 singular dbt
tests** (`assert_no_pii_in_serving`, `assert_gwp_reconciles`, `assert_non_negative_money`) + the generic
column tests (unique/not_null/accepted_values/relationships). What is **missing**: nothing **tells** anyone
when the nightly pipeline **fails or goes stale**, there is no **not-empty** guard (a job can "succeed" and
load nothing), and there are no live/integration tests.

"DataOps monitoring" is **four distinct capabilities** with very different cost/value — judged separately
rather than lumped as "adopt Great Expectations/Soda":

| # | Capability | Cost | Value now (~tens of rows, nightly batch, 1 consumer) |
|---|---|---|---|
| **A** | Tell me when the pipeline **fails / goes stale** | low (reuse Prometheus+Alertmanager) | **high** — the real risk is a silent failure → a stale dashboard nobody notices |
| **B** | **Freshness** — "did last night actually refresh?" | low | **high** — pairs with A |
| **C** | A few more **dbt assertions** (e.g. not-empty) | very low | medium — the key invariants are already covered |
| **D** | A **DQ framework** (Great Expectations / Soda) | high (standing service + config/runtime) | **low** — adds little over dbt tests at this scale; its value is many sources + anomaly checks at volume |
| **E** | Full **L2 live/integration tests** (real throwaway DB in CI) | medium | medium — catches real DB/transform bugs, but the transforms are simple aggregations today |

The real risk is **A/B (silent failure)**, which is **cheap** to close with tools already running —
**not** the heavyweight framework (D) the generic advice names first. Same need-first logic as ADR-011.

## Decision

**Build the "now" slice (A+B+C); defer D and the full E.**

- **A+B (one rule):** a `PrometheusRule` (gitops `platform/data/data-platform/`) alerting when either
  nightly CronJob (`dp-lake-land-policy`, `dp-lake-transform-policy`) **has not had a successful run in
  >25h** — which catches *both* a failed job and a job that never ran (freshness). Mirrors the proven
  `backup-dr` staleness pattern; routes via `severity` to the existing Alertmanager. **No new service.**
- **C:** one high-value dbt assertion — **`assert_portfolio_not_empty.sql`** — so a pipeline that
  *succeeds but loads nothing* fails the build (the one silent mode the staleness alert cannot see).
- **Notification path (explicit):** the alerts are `severity: warning` → they surface in Alertmanager
  (UI + the webhook logger), **not** email/Slack (that channel is reserved for `critical` infra). This is
  deliberate: a stale *derived* analytics pipeline is warning-grade (RPO 24h is acceptable — the data is
  rebuildable). **Escalation is a one-line follow-up** (bump to `critical`, or add a data-platform
  `warning` route) — deferred until the signal proves too quiet.

## Triggers (adopt the deferred pieces when ANY fires)

- **D — Great Expectations / Soda:** **multiple** sources with complex quality rules, **non-dbt** data
  needing validation, or enough **volume** that statistical/distribution/anomaly checks earn their keep.
  (Not DuckDB/dbt-replaceable checks — those stay in dbt.)
- **E — full L2/L4-live:** the transforms grow **beyond simple aggregations**, a transform bug **reaches
  prod**, or the repo is formally promoted to Tier-A. A **lite** version (run `dbt build` + the tests
  against an ephemeral Postgres in CI) is a reasonable optional near-term if more confidence is wanted
  before then.
- **dbt source freshness (finer than CronJob staleness):** when a **per-source freshness SLA** is needed,
  add a `loaded_at` field (dlt already stamps load metadata) + a `freshness:` block + `dbt source
  freshness` in the nightly job. The CronJob-staleness alert is the coarse-but-cheap version for now.

## Consequences

- **Positive:** the **silent-failure** gap is closed now with **zero new pods**; the deferral of D/E is an
  auditable, triggered decision; the alert reuses the house Prometheus/Alertmanager pattern (one more
  `PrometheusRule`, consistent with `backup-dr`).
- **Negative / watch:** `warning` alerts are **not emailed** yet (Alertmanager UI/log only) — if a real
  stale incident is missed because no one looked, that *is* the trigger to escalate routing. The
  not-empty test guards the served data product only (not every intermediate model) — proportionate at
  this scale.

## Related

ADR-011 (need-first trigger register) · `backup-dr/00-prometheusrule.yaml` (the staleness pattern reused) ·
`testing.md` (the L0–L5 layer standard; this is the L2/L4 deferral) · `qa-gate.md` (the L5 live gate — a
separate pre-prod concern) · `docs/data-catalog.md` (the DQ/PII surface). Artefacts:
`platform/data/data-platform/10-cronjob-alerts.yaml` (gitops) + `dbt/tests/assert_portfolio_not_empty.sql`.
