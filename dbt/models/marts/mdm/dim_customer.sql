-- MDM conformed dimension: Customer (INTERIM — no authoritative Customer master exists yet).
-- ktayl-policy-service has NO customer entity; the only identifier is `holder_name`, a PII string
-- (CAP-001 Customer Management = GAP, no CRM). So this dim is derived, not sourced:
--   customer_sk = md5(normalized holder_name) → a pseudonymous, STABLE join surrogate that de-dupes
--   same-named holders across policies. The raw name is NOT carried to the business/serve layer
--   (GDPR / EU AI Act Art. 10; see tests/assert_no_pii_in_serving). Grain = one row per distinct holder.
--
-- REPLACE WITH A REAL SOURCE when a Customer/CRM/MDM domain ships (ADR-007 Slice-2 keystone): at that
-- point customer_sk keys to an authoritative Customer id + a salted hash, and this derivation retires.
-- Caveat: md5(name) is pseudonymous (derived from PII), not anonymised — adequate as an internal join
-- key, upgrade to a salted key with the real Customer master.
-- normalise the (PII) name to a key; null/blank holders collapse into one '(unknown)' member so the
-- dimension is complete and referential integrity with dim_policy.customer_sk holds (no null keys).
with pol as (
    select
        coalesce(nullif(lower(trim(holder_name)), ''), '(unknown)')  as customer_key,
        policy_number,
        effective_date,
        expiry_date
    from {{ ref('stg_policies') }}
),
customers as (
    select
        md5(customer_key)              as customer_sk,
        count(distinct policy_number)  as policy_count,
        min(effective_date)            as first_policy_date,
        max(expiry_date)               as latest_expiry_date
    from pol
    group by 1
)
select * from customers
