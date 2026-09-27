-- Cleaned premiums. amount is BIGINT eurocents — CONFIRMED against the source domain model
-- (ktayl-policy-service internal/domain/premium.go: `Amount int64 // eurocents`); exposed as _minor + _eur.
-- annualised = amount x cadence multiplier. OPEN (DP-007): this treats each premium row as a *recurring
-- schedule* at its frequency. If the domain instead stores one row *per installment* (the table has
-- per-row due_date/paid_at and the service has no auto-scheduler → caller-determined), the correct annual
-- GWP is sum(amount) within a term, and x-multiplier over-counts. Keep GWP labelled a *proxy* until the
-- Policy domain fixes the row cardinality. See issue #7.
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
