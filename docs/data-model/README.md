# Data model — ktayl-data-platform (ERD)

> **What this is.** The entity-relationship model of the data platform's *analytical* schema —
> the 1:1 **raw landing contract** and the conformed **serving star** (MDM dims + facts + the
> `policy_portfolio` data product). This is the SA "Data design" artefact (#7) and the human-readable
> companion to the dbt model contracts. Grain, keys, and PII classification are stated per entity.

## Why this is hand-authored, not `tbls`-generated

This repo's serving store is a **dbt-derived medallion warehouse**, not a migration-owned schema. Per the
platform `schema-erd` standard (the *dbt / warehouse carve-out*), a dbt warehouse is **not** gated by
`tbls` drift — its drift gate is the **committed dbt model contracts** (`models/**/_*.yml` + `tests:`) run
by **CI `dbt parse`**, plus the enforced `tests/assert_no_pii_in_serving.sql` gate. This ERD is therefore a
**documentation artefact** that mirrors those contracts; it is kept in sync by hand when the contracts
change (the contracts remain the machine-checked source of truth).

Schemas: `raw` (1:1 landing) → `curated` (dbt staging views, ephemeral — not shown as entities) →
`business` / `lake` (table-materialised serving marts).

---

## 1. Raw landing contract (`raw.*`)

1:1 copies of the live source tables (`ktayl-core` policy module + `ktayl-underwriting`). These are the
**only real columns that exist** — the data product is a contract over exactly these fields, enforced by
dbt source tests. `holder_name` is direct-identifier PII and is **blocked from the serving layer**.

```mermaid
erDiagram
    POLICIES  ||--o{ COVERAGES : "insures (policy_id)"
    POLICIES  ||--|| PREMIUMS  : "priced by (policy_id, 1 row/policy — tripwire)"
    UW_QUOTES ||--o| UW_BINDINGS : "bound as (quote_id)"
    UW_BINDINGS }o--|| POLICIES : "policy_number crosswalk"

    POLICIES {
        bigint id PK
        string policy_number UK
        string status "draft|active|suspended|terminated"
        string product_code
        date   effective_date
        date   expiry_date
        string holder_name "PII — personal-data (GDPR); raw/curated only, NEVER served"
    }
    COVERAGES {
        bigint id PK
        bigint policy_id FK
        bigint insured_amount "minor units → TIV"
    }
    PREMIUMS {
        bigint id PK
        bigint policy_id FK "UK: one schedule row per policy (DP-007 tripwire)"
        bigint amount "minor units"
        string frequency "monthly|quarterly|annual"
    }
    UW_QUOTES {
        bigint id PK
        bigint premium_minor "authoritative rated technical premium"
    }
    UW_BINDINGS {
        bigint quote_id FK
        string policy_number UK "→ POLICIES.policy_number"
    }
```

---

## 2. Conformed serving star (`business.*` / `lake.*`)

Kimball-style star: a conformed-dimension spine (policy / customer / LOB / period) + `fact_policy`
(grain = one policy) + the `policy_portfolio` data product. **No PII** at this layer. Surrogate keys are
`md5(natural key)`; `dim_customer` is an **interim pseudonymous** dim (`md5(holder_name)`) until a real
Customer/CRM master ships (CAP-001 gap — see `dbt/models/marts/mdm/README.md`).

```mermaid
erDiagram
    DIM_POLICY   }o--|| DIM_CUSTOMER : "held by (customer_sk)"
    DIM_POLICY   }o--|| DIM_LOB      : "classified (lob_sk)"
    FACT_POLICY  ||--|| DIM_POLICY   : "registry (policy_sk)"
    FACT_POLICY  }o--|| DIM_CUSTOMER : "customer_sk"
    FACT_POLICY  }o--|| DIM_LOB      : "lob_sk"
    FACT_POLICY  }o--|| DIM_PERIOD   : "inception_period_sk"

    DIM_POLICY {
        string policy_sk PK "md5(policy_number)"
        string policy_nk UK "policy_number (crosswalk)"
        string customer_sk FK
        string lob_sk FK
    }
    DIM_CUSTOMER {
        string customer_sk PK "md5(lower(trim(holder_name))) — pseudonymous, INTERIM"
    }
    DIM_LOB {
        string lob_sk PK "md5(product_code)"
        string lob_code UK "product_code"
    }
    DIM_PERIOD {
        string period_sk PK "YYYYMM"
        date   period_start
        date   period_end
        int    period_year
        int    period_quarter
        int    period_month
        string period_label "YYYY-MM"
    }
    FACT_POLICY {
        string policy_sk PK "FK → DIM_POLICY"
        string policy_nk
        string customer_sk FK
        string lob_sk FK
        string inception_period_sk FK
        string status
        date   effective_date
        date   expiry_date
        int    policy_count "additive"
        int    active_policy_count "additive"
    }
```

### Data products (served to Metabase / Cube)

| Model | Schema | Grain | Purpose |
|---|---|---|---|
| **`policy_portfolio`** | `business` | one policy | The data product: authoritative GWP (`coalesce(underwriting rated premium, annualised proxy)`), premium, TIV. Columns: `policy_id` PK, `policy_number` UK, `status`, `scheduled_premium_minor`, `annualised_premium_eur` (proxy), `underwriting_premium_eur` (authoritative, Slice 2), `rate_table_version`, `bound_via_underwriting`, `gwp_eur`, `gwp_minor` (not-null), `total_insured_amount_eur`. |
| **`policy_portfolio_lake`** | `lake` | `product_code × status × inception_year` | Pre-aggregated summary the DuckDB→CNPG lake path materialises for the Metabase dashboard + the Cube cube. Columns: `product_code`, `status`, `inception_year`, `policy_count`, `active_count`. |

---

## Entity summary

| Entity | Layer | Schema | Grain | PII | Keys |
|---|---|---|---|---|---|
| `policies` | raw | `raw` | one policy | **yes** (`holder_name`) | `id` PK · `policy_number` UK |
| `coverages` | raw | `raw` | one coverage | no | `id` PK · `policy_id` FK |
| `premiums` | raw | `raw` | one schedule/policy | no | `id` PK · `policy_id` FK+UK |
| `uw_quotes` | raw | `raw` | one quote | no | `id` PK |
| `uw_bindings` | raw | `raw` | one binding | no | `quote_id` FK · `policy_number` UK |
| `dim_policy` | serving | `business`/`lake` | one policy | no | `policy_sk` PK · `policy_nk` UK |
| `dim_customer` | serving | `business`/`lake` | one customer | no (pseudonymous) | `customer_sk` PK |
| `dim_lob` | serving | `business`/`lake` | one LOB | no | `lob_sk` PK · `lob_code` UK |
| `dim_period` | serving | `lake` | one calendar month | no | `period_sk` PK |
| `fact_policy` | serving | `lake` | one policy | no | `policy_sk` PK + conformed FKs |
| `policy_portfolio` | product | `business` | one policy | no | `policy_id` PK · `policy_number` UK |
| `policy_portfolio_lake` | product | `lake` | product×status×year | no | composite grain |

## Deliberately NOT modelled yet (source-blocked)

`dim_broker` and `dim_location` are **not built** — no authoritative source domain ships them yet
(ADR-007: don't build on stub data). A real Customer/CRM master replaces the interim `dim_customer`
when it exists. Premium/TIV measures on `fact_policy` (written/earned/UPR, exposure) are deferred to
`ktayl-core` Phase-1b (issue #28), when the premium + coverage tables land.

## Keeping this in sync

The dbt contracts are the machine-checked source of truth:
- `dbt/models/staging/_sources.yml` — the raw landing contract (+ source tests, the premium tripwire).
- `dbt/models/marts/_policy_portfolio.yml`, `dbt/models/marts/mdm/_mdm.yml` — the serving contracts.
- `lake/dbt_duckdb/models/marts/**/_*.yml` — the lake star contracts (fact/dim relationships tests).
- `tests/assert_no_pii_in_serving.sql` — enforces that no PII column reaches `business.*`.

CI (`dbt parse`) fails on any contract break. **When a contract changes, update this ERD in the same PR.**
