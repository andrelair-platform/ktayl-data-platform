-- Staging: cleaned/typed policy rows read STRAIGHT from the S3 raw lake (Parquet) — dbt-duckdb reads
-- Parquet from S3 via httpfs, no intermediate load. One row per policy. Ephemeral DuckDB view.
-- Status is normalised to the warehouse's lowercase convention (ktayl-core emits UPPERCASE).
select
    id                                      as policy_id,
    policy_number,
    holder_name,                            -- PII — stays in staging, NEVER selected into a mart
    product_code,
    lower(status)                           as status,
    effective_date,
    expiry_date,
    extract(year from effective_date)::int  as inception_year
from read_parquet('{{ env_var("POLICY_GLOB") }}')
