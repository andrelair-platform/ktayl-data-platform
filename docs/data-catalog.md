# Data catalog — ktayl Data Platform

> **Auto-generated** by `catalog/gen_catalog.py` from `lake/registry/datasets.yaml` + the dbt
> model contracts (`**/models/**/_*.yml`). **Do not edit by hand** — run
> `python3 catalog/gen_catalog.py`; CI drift-gates it (regenerate + `git diff` must be clean).
>
> This is the platform's lightweight catalog/discovery surface. A standing catalog service
> (**OpenMetadata**) is deferred until a trigger fires — see
> [ADR-013](architecture/adr/ADR-013-metadata-catalog-registry-now-openmetadata-on-trigger.md).

**At a glance:** 3 governed raw dataset(s) · 10 warehouse model(s) · 1 PII column(s) under governance.

## Lake (storage)

| Property | Value |
|---|---|
| Bucket | `minicloud-data-lake-625830750465` |
| Region | eu-west-1 |
| Encryption | SSE-S3 (AES256) |
| Versioning | enabled |
| Layout | `s3://<bucket>/<layer>/<domain>/<table>/dt=<YYYY-MM-DD>/<table>.parquet` |

## Governed datasets (raw lake)

The version-controlled registry of what lands in the lake (ADR-008 governance spine).

| Dataset | Layer | Classification | PII | Source | Producer | Retention | Serving destination |
|---|---|---|---|---|---|---|---|
| policy.policies | raw | personal-data | ⚠ yes | ktayl-core (policy module) | `dp-lake-land-policy (lake/producer/land_to_s3.py)` | indefinite-raw | `analytics.lake.policies` |
| policy.coverages | raw | internal | no | ktayl-core (policy module) | `dp-lake-land-policy` | indefinite-raw | `analytics.lake.coverages` |
| policy.premiums | raw | internal | no | ktayl-core (policy module) | `dp-lake-land-policy` | indefinite-raw | `analytics.lake.premiums` |

## Warehouse models (serving)

Derived dbt models (the serving medallion). `Project` = which dbt project builds it; PII should be
**no** for every serving model (enforced by the PII gate — a `⚠ yes` here is a governance alarm).

| Model | Project | Layer | Grain | Columns | Column tests | PII |
|---|---|---|---|---|---|---|
| policy_portfolio_lake | dbt-duckdb (lake) | mart | product_code × status × inception_year | 2 | 2 | no |
| fact_policy | dbt-duckdb (lake) | mart · fact | one policy | 5 | 5 | no |
| dim_customer | dbt-duckdb (lake) | mart · MDM dim | — | 1 | 1 | no |
| dim_lob | dbt-duckdb (lake) | mart · MDM dim | one distinct product_code | 2 | 2 | no |
| dim_period | dbt-duckdb (lake) | mart · MDM dim | — | 2 | 2 | no |
| dim_policy | dbt-duckdb (lake) | mart · MDM dim | one policy | 4 | 4 | no |
| policy_portfolio | dbt-postgres | mart | policy | 11 | 4 | no |
| dim_customer | dbt-postgres | mart · MDM dim | — | 1 | 1 | no |
| dim_lob | dbt-postgres | mart · MDM dim | one distinct product_code | 2 | 2 | no |
| dim_policy | dbt-postgres | mart · MDM dim | one policy | 4 | 4 | no |

## PII register (GDPR Art. 30 data-map · EU AI Act Art. 10 data-governance)

Every column under PII governance, where it is allowed to live, and the control that enforces it.
Direct identifiers may land in `raw`/`curated` (encrypted, private, access-gated) but are **blocked
from the served `business`/`gold` layer** by `tests/assert_no_pii_in_serving.sql` (fails the build
on violation). Formalising a golden Customer/Party record is deferred — see
[ADR-014](architecture/adr/ADR-014-customer-party-mdm-golden-record-trigger.md).

| Column | Dataset / source | Classification | Allowed layers | Enforcement |
|---|---|---|---|---|
| `holder_name` | policy.policies | personal-data | raw, curated | `assert_no_pii_in_serving` (blocks business/gold) |

