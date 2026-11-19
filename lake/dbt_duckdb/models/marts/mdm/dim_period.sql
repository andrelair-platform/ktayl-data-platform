-- MDM conformed dimension: Period (calendar month). Grain = one month over the live portfolio term
-- range (min effective_date → max expiry_date). The TIME key for time-series KPIs and (once premium
-- ships, issue #28) earned/unearned premium. Generated calendar, no PII. period_sk = 'YYYYMM'.
with bounds as (
    select
        date_trunc('month', min(effective_date)) as start_month,
        date_trunc('month', max(expiry_date))    as end_month
    from {{ ref('stg_policy') }}
),
months as (
    select unnest(generate_series(start_month, end_month, interval '1 month'))::date as month_start
    from bounds
)
select
    strftime(month_start, '%Y%m')                               as period_sk,
    month_start                                                 as period_start,
    (month_start + interval '1 month' - interval '1 day')::date as period_end,
    extract(year    from month_start)::int                      as period_year,
    extract(quarter from month_start)::int                      as period_quarter,
    extract(month   from month_start)::int                      as period_month,
    strftime(month_start, '%Y-%m')                              as period_label
from months
