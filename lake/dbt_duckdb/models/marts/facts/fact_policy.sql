-- CONFORMED FACT: Policy registry (grain = one policy) on LIVE ktayl-core data. Keys to the conformed
-- MDM dims (policy/customer/lob/period). This is the reworked `fact_premium` — its PREMIUM/TIV measures
-- (written/earned/UPR, GWP, exposure) are DEFERRED to ktayl-core Phase-1b (coverages + premium metadata),
-- tracked in issue #28; fact_premium extends this fact when those tables ship. For now it carries the
-- additive policy count + the active flag + the FK grain. No PII.
with pol as (
    select * from {{ ref('stg_policy') }}
)
select
    md5(policy_number)                                                 as policy_sk,
    policy_number                                                      as policy_nk,
    md5(coalesce(nullif(lower(trim(holder_name)), ''), '(unknown)'))   as customer_sk,           -- FK → dim_customer
    md5(product_code)                                                  as lob_sk,                -- FK → dim_lob
    strftime(date_trunc('month', effective_date), '%Y%m')             as inception_period_sk,   -- FK → dim_period
    status,
    effective_date,
    expiry_date,
    1                                                                  as policy_count,          -- additive measure
    case when status = 'active' then 1 else 0 end                      as active_policy_count    -- additive measure
from pol
