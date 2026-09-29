-- GOVERNANCE GATE (authoritative-GWP contract): gwp_minor MUST equal the underwriting rated premium
-- when the policy was bound via underwriting, else the annualised proxy, else 0 — i.e. exactly the
-- coalesce(uw_premium, annualised, 0) rule in policy_portfolio.sql. This pins the "authoritative GWP"
-- semantics so a future refactor of the mart can't silently change which figure is served as GWP.
-- (Passes when it returns 0 rows.)
select
    policy_id,
    gwp_minor,
    underwriting_premium_minor,
    annualised_premium_minor
from {{ ref('policy_portfolio') }}
where gwp_minor <> coalesce(underwriting_premium_minor, annualised_premium_minor, 0)
