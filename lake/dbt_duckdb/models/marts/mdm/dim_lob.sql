-- MDM conformed dimension: Line of Business (LOB). Grain = one distinct product_code. lob_sk =
-- md5(product_code). lob_name is the product_code verbatim for now — a code→human-name crosswalk is a
-- future reference seed (don't fabricate names). No PII.
with pol as (
    select distinct product_code
    from {{ ref('stg_policy') }}
    where product_code is not null
)
select
    md5(product_code) as lob_sk,
    product_code      as lob_code,
    product_code      as lob_name
from pol
