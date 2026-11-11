-- MDM conformed dimension: Line of Business (LOB). Grain = one row per distinct product_code.
-- Slice-2 MDM (ADR-007): a reference dimension facts/dims key on. Surrogate lob_sk = md5(product_code).
-- `lob_name` is the product_code verbatim for now — a product_code → human LOB-name crosswalk is a
-- future reference seed (don't fabricate names here). No PII.
with pol as (
    select distinct product_code
    from {{ ref('stg_policies') }}
    where product_code is not null
)
select
    md5(product_code)  as lob_sk,
    product_code       as lob_code,
    product_code       as lob_name   -- TODO: enrich via a product_code→LOB-name seed
from pol
