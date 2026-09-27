---
title: Data Model
sidebar_position: 3
---

# Data Model

The data model is the medallion — three schemas in the `analytics` database — with the
`policy_portfolio` data product as its serve-layer output.

## Medallion layers

| Layer | Schema | Materialisation | Role |
|---|---|---|---|
| Raw | `raw` | landed tables | 1:1 landing of the policy source (`policies`, `coverages`, `premiums`) |
| Curated | `curated` | dbt **views** | typed / cleaned staging: `stg_policies`, `stg_premiums`, `stg_coverages` |
| Business | `business` | dbt **table** | the data product `policy_portfolio` (what Metabase reads) |

### Source contract (raw)

The raw layer lands exactly the columns that exist in the live policy source; the data product is a
contract over those fields, enforced by dbt tests:

- `policies` — `id`, `policy_number`, `status` (`draft` / `active` / `suspended` / `terminated`),
  `product_code`, `effective_date`, `expiry_date`.
- `coverages` — `id`, `policy_id`, `insured_amount`.
- `premiums` — `id`, `policy_id`, `amount`, `frequency` (`monthly` / `quarterly` / `annual`).

## `policy_portfolio` — the data product

**Grain = one row per policy.** Measures are grounded on real source columns only. Columns:

| Column | Meaning |
|---|---|
| `policy_id`, `policy_number` | keys (unique, not null) |
| `product_code`, `status`, `is_active`, `inception_year`, `effective_date`, `expiry_date` | dimensions |
| `scheduled_premium_minor` / `scheduled_premium_eur` | sum of premium installment amounts |
| `paid_premium_minor` | sum of paid installments |
| `annualised_premium_minor` / `annualised_premium_eur` | **GWP proxy** — seeds P2 (margin / portfolio) |
| `premium_installments` | count of premium rows |
| `total_insured_amount_minor` / `total_insured_amount_eur` | **TIV** — seeds P1/P3 (exposure / accumulation) |
| `coverage_count` | count of coverage rows |

### Money units — confirmed

Money source columns are `BIGINT` **eurocents** — **confirmed** (DP-007) against the source domain model
(`ktayl-policy-service` `internal/domain/premium.go` and `coverage.go`, where `Amount`, `InsuredAmount`
and `Deductible` are `int64 // eurocents`). The `*_eur` columns are the minor-unit values divided by 100
and rounded to 2 decimals.

### GWP is still a proxy — annualisation cadence

`annualised_premium_eur` is the sum of premium amounts multiplied by a cadence multiplier
(monthly ×12, quarterly ×4, annual ×1), divided by 100. This treats each `premiums` row as a **recurring
schedule** at its `frequency`. The `premiums` table, however, carries a per-row `due_date`/`paid_at` and
the service has **no auto-scheduler** (rows are caller-created), so it could equally represent **individual
installments** — in which case the correct annual GWP is `sum(amount)` within a term and the ×multiplier
would over-count. The **money units are confirmed**; only this **row-cardinality** decision remains, so
`annualised_premium_eur` stays labelled a **proxy** (tracked as DP-007) until the Policy domain fixes it.

## dbt schema naming

dbt's default `generate_schema_name` concatenates the target schema with the custom schema, which would
produce `business_business` / `business_curated`. A macro override (`dbt/macros/generate_schema_name.sql`)
uses the custom schema name **verbatim** instead, so:

- staging models land in `curated`
- marts land in `business`

This is safe because the platform is a single-target, single-owner analytics database. Do not remove the
override, or the marts move to `business_business`.
