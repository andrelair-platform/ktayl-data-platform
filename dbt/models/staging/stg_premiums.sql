-- Cleaned premiums. amount is BIGINT eurocents — CONFIRMED against the source domain model
-- (ktayl-policy-service internal/domain/premium.go: `Amount int64 // eurocents`); exposed as _minor + _eur.
-- annualised = amount x cadence multiplier under the DP-007 *interim contract*: ONE premium row per
-- policy = the recurring schedule at its frequency. That contract is ENFORCED by a `unique` test on
-- premiums.policy_id (see _sources.yml) — premium management is a future domain, and if it later ships
-- per-installment rows the test fails the build → this annualisation must switch to sum(amount) first.
with src as (
    select * from {{ source('policy_raw', 'premiums') }}
)
select
    id                                   as premium_id,
    policy_id,
    amount                               as amount_minor,
    round(amount / 100.0, 2)             as amount_eur,
    frequency,
    case frequency
        when 'monthly'   then 12
        when 'quarterly' then 4
        when 'annual'    then 1
    end                                  as annual_multiplier,
    amount * case frequency
        when 'monthly'   then 12
        when 'quarterly' then 4
        when 'annual'    then 1
    end                                  as annualised_amount_minor,
    due_date,
    paid_at,
    (paid_at is not null)                as is_paid
from src
