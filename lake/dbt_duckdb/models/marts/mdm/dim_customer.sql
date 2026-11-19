-- MDM conformed dimension: Customer (INTERIM — no authoritative Customer master yet; CAP-001 GAP).
-- ktayl-core policy.policy has only holder_name (PII). Derived: customer_sk = md5(normalised holder_name),
-- a pseudonymous, STABLE join surrogate that de-dupes same-named holders; the raw name is NEVER served.
-- Replace with a real Customer/CRM source when one ships. Grain = one distinct holder.
with pol as (
    select
        coalesce(nullif(lower(trim(holder_name)), ''), '(unknown)') as customer_key,
        policy_number,
        effective_date,
        expiry_date
    from {{ ref('stg_policy') }}
)
select
    md5(customer_key)              as customer_sk,
    count(distinct policy_number)  as policy_count,
    min(effective_date)            as first_policy_date,
    max(expiry_date)               as latest_expiry_date
from pol
group by 1
