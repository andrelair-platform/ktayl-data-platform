-- dbt model (Dagster asset): policy portfolio summary over the dlt-landed raw policy.
-- Grain = product_code × status × inception_year. Feeds the ML feature asset downstream.
with src as (
    select * from {{ source('dlt_raw', 'policy') }}
)
select
    product_code,
    lower(status)                           as status,
    extract(year from effective_date)::int  as inception_year,
    count(*)                                as policy_count,
    count(*) filter (where lower(status) = 'active') as active_count
from src
group by 1, 2, 3
