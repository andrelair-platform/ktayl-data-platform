# MDM conformed dimensions (Slice-2 keystone — ADR-007)

The join keys every cross-domain fact/KPI references. **Built only where a real source exists today.**

| Dimension | Status | Source | Key |
|---|---|---|---|
| `dim_policy` | ✅ real | `stg_policies` | `policy_sk = md5(policy_number)` — hub, carries `customer_sk` + `lob_sk` |
| `dim_customer` | 🟡 **interim** | `stg_policies.holder_name` (PII) | `customer_sk = md5(normalized name)` — **no Customer master exists** (CAP-001 GAP); pseudonymous surrogate, raw name never served |
| `dim_lob` | ✅ real | `stg_policies.product_code` | `lob_sk = md5(product_code)` |
| `dim_broker` | ⛔ **not built** | — | needs the **Distribution/CRM** domain (no broker source today) |
| `dim_location` | ⛔ **not built** | — | needs **site/geocode** data (Submission/exposure domain) — required for accumulation/PML |

## Why interim/absent dims are honest, not gaps-by-neglect

MDM's central entity — **Customer** — has **no authoritative source**: `ktayl-policy-service` has no
customer entity, only a `holder_name` string. So `dim_customer` is *derived* from the name as a stable,
pseudonymous join key until a real Customer/CRM domain ships. `dim_broker` and `dim_location` have **no
source at all** yet, so they are deliberately not fabricated. This is the register's finding made concrete
(CAP-001 Customer Management = GAP).

## What this unblocks (and what still waits)

- **Now:** `dim_policy`/`dim_customer`/`dim_lob` let policy/underwriting facts be grouped by conformed
  customer + LOB keys — the first step of a real warehouse.
- **Next (ADR-007 Slice-2 order):** ingest **claims / billing / finance** sources → conformed `fact_*`
  (premium/claim/commission/reinsurance) keyed on these dims → **Combined Ratio** = the first real
  cross-domain KPI. `dim_location` + `dim_broker` arrive with their domains.

## Upgrade path for `dim_customer`

When a Customer master/CRM exists: `customer_sk` keys to an authoritative Customer id (+ a salted hash),
and the `md5(name)` derivation retires. Consumers that joined on `customer_sk` keep working — the *source*
of the key changes, not the contract.
