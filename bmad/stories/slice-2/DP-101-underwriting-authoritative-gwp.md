---
id: DP-101
title: "Slice 2: underwriting as a 2nd live source → authoritative GWP (closes DP-007)"
status: Ready
type: Story
epic: data-platform-slice-2
milestone: "Data Platform Slice 2 — Underwriting premium"
estimate: 5
labels: [data-platform, dbt, ingestion]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As* **finance/actuarial + underwriting portfolio**, *I want* the Policy Portfolio's **GWP** to come from
the **underwriting rating engine's authoritative technical premium** (not the policy-service annualised
*proxy*) *so that* the number is the real rated premium — the payoff of the doctrine's "generalise from a
2nd real live pipeline," and the real close of **DP-007**.

## Doctrine
Slice 1 proved one live source → medallion → one product. Slice 2 is the **2nd real pipeline** (the
need-first trigger): underwriting now emits real premiums (`quote.premium_minor`) and links them to bound
policies (`binding.policy_number`), so we can promote the GWP proxy to authoritative — not a generic
connector framework, just the second concrete source.

## Scope
- **2nd source: the underwriting DB** (dev `underwriting` ns, CNPG `underwriting-postgres`, db `underwriting`).
  Ingest **`quote`** + **`binding`** 1:1 → `raw.uw_quotes`, `raw.uw_bindings` (same full-refresh COPY
  pattern as `ingest_policy.sh`; a dedicated read-only role on the underwriting DB).
- **Staging:** `stg_uw_quotes` (premium_minor, currency, rate_table_version), `stg_uw_bindings`
  (policy_number, quote_id, status) + source tests.
- **Mart (`policy_portfolio`) — the DP-007 close:** join `binding` → `quote` by `quote_id`, keyed to the
  policy by **`policy_number`**. Add `underwriting_premium_minor/eur` (authoritative rated premium),
  `rate_table_version`, `bound_via_underwriting` (bool). Promote GWP:
  **`gwp_eur = coalesce(underwriting authoritative premium, annualised proxy)`** — authoritative for
  underwriting-originated policies, proxy fallback for legacy/direct ones. Keep the old proxy column too
  (labelled) for lineage/comparison.

## Out of scope (need-first, later)
- CDC (Debezium→NATS) over the full-refresh COPY; consuming the NATS bound-risk event directly; MDM-keyed
  Customer 360; ingesting underwriting *prod* (only dev exists). Metabase card polish beyond the GWP source.

## Acceptance criteria
- Ingest lands `raw.uw_quotes` + `raw.uw_bindings`; source tests pass (unique quote id, binding policy_number
  unique + not_null, premium_minor not_null).
- `policy_portfolio` gains the authoritative GWP columns; for a policy bound via underwriting the
  `gwp_eur` equals the underwriting quote premium (verified against the live bound policy
  `UW-369188ABE405` = €400), and equals the proxy for non-underwriting policies.
- dbt build green (existing + new tests); ingest+dbt CronJobs run clean; no secrets in code.
- Deploy (gitops): read-only role + creds (Vault→ESO), a data-platform→underwriting-postgres netpol, and the
  ingest CronJob extended with the underwriting source. Deployment-vs-code separation kept.

## Notes
- Join key is `policy_number` (underwriting `binding.policy_number` = policy_portfolio `policy_number`);
  premium via `binding.quote_id → quote.premium_minor`. Money = eurocents.
- This makes underwriting the authoritative premium origin for the portfolio — the through-line from the
  bind work (ADR-006) to the analytics layer.
