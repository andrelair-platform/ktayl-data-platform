-- Mart: policy-portfolio summary, materialised into CNPG (analytics.lake.policy_portfolio_lake) for
-- Metabase. DuckDB does the columnar aggregation over the S3 Parquet; CNPG serves the small gold result.
-- Grain = product_code × status × inception_year. NO PII (holder_name is dropped at this layer).
select
    product_code,
    status,
    inception_year,
    count(*)                                   as policy_count,
    count(*) filter (where status = 'active')  as active_count
from {{ ref('stg_policy') }}
group by 1, 2, 3
order by 1, 2, 3
