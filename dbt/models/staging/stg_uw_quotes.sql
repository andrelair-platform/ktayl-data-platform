-- Cleaned/typed view of raw underwriting quotes. One row per quote.
-- premium_minor is BIGINT eurocents (ktayl-underwriting app/rating/models.py: `premium_minor` eurocents);
-- exposed as _minor + _eur. This is the AUTHORITATIVE rated technical premium (vs the policy-service proxy).
with src as (
    select * from {{ source('underwriting_raw', 'uw_quotes') }}
)
select
    id                                   as quote_id,
    submission_id,
    premium_minor,
    round(premium_minor / 100.0, 2)      as premium_eur,
    currency,
    rate_table_version
from src
