-- Cleaned/typed view of raw underwriting bindings. One row per bound risk (unique policy_number).
-- policy_number is the join key to policy_portfolio; quote_id links to the authoritative quote premium.
with src as (
    select * from {{ source('underwriting_raw', 'uw_bindings') }}
)
select
    id                                   as binding_id,
    policy_number,
    quote_id,
    status,
    bound_at
from src
