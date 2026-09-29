-- GOVERNANCE GATE (business invariant): money & exposure measures in the served data product
-- must never be negative. A premium, GWP or TIV below zero means a source or transform bug — block
-- the daily build before a wrong figure reaches Metabase or a model. (Passes when 0 rows return.)
select
    policy_id,
    scheduled_premium_minor,
    annualised_premium_minor,
    gwp_minor,
    underwriting_premium_minor,
    total_insured_amount_minor
from {{ ref('policy_portfolio') }}
where scheduled_premium_minor < 0
   or annualised_premium_minor < 0
   or gwp_minor < 0
   or coalesce(underwriting_premium_minor, 0) < 0
   or total_insured_amount_minor < 0
