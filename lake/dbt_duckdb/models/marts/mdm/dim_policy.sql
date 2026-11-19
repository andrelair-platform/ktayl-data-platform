-- MDM conformed dimension: Policy (hub). Grain = one policy. Built on LIVE ktayl-core data (via the S3
-- lake). Carries the surrogate FKs (customer_sk, lob_sk) that make cross-domain facts join-able on
-- conformed keys. policy_sk = md5(policy_number); policy_nk is the crosswalk to source. No PII.
with pol as (
    select * from {{ ref('stg_policy') }}
)
select
    md5(policy_number)                                                  as policy_sk,
    policy_number                                                       as policy_nk,
    md5(coalesce(nullif(lower(trim(holder_name)), ''), '(unknown)'))    as customer_sk,  -- FK → dim_customer
    md5(product_code)                                                   as lob_sk,       -- FK → dim_lob
    status,
    (status = 'active')                                                 as is_active,
    effective_date,
    expiry_date,
    inception_year
from pol
