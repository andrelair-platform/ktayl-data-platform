-- GOVERNANCE GATE (EU AI Act Art. 10 · GDPR): the served / gold layer must expose NO
-- direct-identifier PII. Personal data (e.g. holder_name) stays in raw/curated only and must
-- never reach business.policy_portfolio (what Metabase, apps and future models/features read).
-- Today that exclusion happens by omission in the mart SELECT; this test turns it into an
-- ENFORCED control — the daily `dbt build` FAILS if a PII-named column ever lands in the mart.
-- (A singular test: passes when it returns 0 rows.)
select column_name
from information_schema.columns
where table_schema = 'business'
  and table_name   = 'policy_portfolio'
  and lower(column_name) in (
      'holder_name', 'email', 'phone', 'address',
      'date_of_birth', 'dob', 'nir', 'ssn'
  )
