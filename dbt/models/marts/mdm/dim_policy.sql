-- MDM conformed dimension: Policy. Grain = one row per policy. No PII.
-- Slice-2 MDM (ADR-007): the HUB dimension — carries the surrogate FKs (customer_sk, lob_sk) that make
-- cross-domain facts join-able on conformed keys. Surrogate policy_sk = md5(policy_number); the natural
-- key (policy_nk) is retained as the crosswalk from source rows.
with pol as (
    select * from {{ ref('stg_policies') }}
)
select
    md5(policy_number)              as policy_sk,          -- surrogate (conformed)
    policy_number                  as policy_nk,           -- natural key (crosswalk to source)
    -- FK → dim_customer (interim, name-derived); same normalisation as dim_customer so nulls/blanks
    -- map to the shared '(unknown)' member → referential integrity holds, no null keys.
    md5(coalesce(nullif(lower(trim(holder_name)), ''), '(unknown)')) as customer_sk,
    md5(product_code)              as lob_sk,              -- FK → dim_lob
    status,
    is_active,
    effective_date,
    expiry_date,
    inception_year
from pol
