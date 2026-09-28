-- DATA PRODUCT: Policy Portfolio (grain = one row per policy).
-- The business/serve layer Metabase reads. Measures are grounded on real source columns only.
with policies as (
    select * from {{ ref('stg_policies') }}
),
prem as (
    select
        policy_id,
        sum(amount_minor)                                   as scheduled_premium_minor,
        sum(case when is_paid then amount_minor else 0 end) as paid_premium_minor,
        sum(annualised_amount_minor)                        as annualised_premium_minor,
        count(*)                                            as premium_installments
    from {{ ref('stg_premiums') }}
    group by 1
),
cov as (
    select
        policy_id,
        sum(insured_amount_minor)  as total_insured_amount_minor,   -- TIV (exposure seed for P1/P3)
        count(*)                   as coverage_count
    from {{ ref('stg_coverages') }}
    group by 1
),
-- Slice 2 (DP-007 close): the AUTHORITATIVE rated premium from the underwriting engine.
-- binding → quote by quote_id, keyed to the policy by policy_number (one binding per policy_number).
uw as (
    select
        b.policy_number,
        q.premium_minor       as uw_premium_minor,
        q.rate_table_version
    from {{ ref('stg_uw_bindings') }} b
    join {{ ref('stg_uw_quotes') }} q on q.quote_id = b.quote_id
)
select
    p.policy_id,
    p.policy_number,
    p.product_code,
    p.status,
    p.is_active,
    p.inception_year,
    p.effective_date,
    p.expiry_date,
    coalesce(pr.scheduled_premium_minor, 0)                as scheduled_premium_minor,
    round(coalesce(pr.scheduled_premium_minor, 0)/100.0, 2) as scheduled_premium_eur,
    coalesce(pr.paid_premium_minor, 0)                    as paid_premium_minor,
    coalesce(pr.annualised_premium_minor, 0)              as annualised_premium_minor,
    round(coalesce(pr.annualised_premium_minor, 0)/100.0, 2) as annualised_premium_eur,  -- GWP PROXY (lineage/comparison; superseded by gwp_* below where a UW premium exists)
    coalesce(pr.premium_installments, 0)                  as premium_installments,
    -- Slice 2: authoritative underwriting premium (null for legacy/direct policies not bound via UW)
    uw.uw_premium_minor                                   as underwriting_premium_minor,
    round(uw.uw_premium_minor / 100.0, 2)                 as underwriting_premium_eur,
    uw.rate_table_version,
    (uw.policy_number is not null)                        as bound_via_underwriting,
    -- AUTHORITATIVE GWP: the rated UW premium when the policy was bound via underwriting, else the proxy
    coalesce(uw.uw_premium_minor, pr.annualised_premium_minor, 0)                as gwp_minor,
    round(coalesce(uw.uw_premium_minor, pr.annualised_premium_minor, 0)/100.0, 2) as gwp_eur,
    coalesce(c.total_insured_amount_minor, 0)             as total_insured_amount_minor,
    round(coalesce(c.total_insured_amount_minor, 0)/100.0, 2) as total_insured_amount_eur, -- TIV
    coalesce(c.coverage_count, 0)                         as coverage_count
from policies p
left join prem pr on pr.policy_id = p.policy_id
left join cov  c  on c.policy_id  = p.policy_id
left join uw   on uw.policy_number = p.policy_number
