-- MONITORING GATE (DataOps, ADR-015): the served data product must never be EMPTY. An empty
-- policy_portfolio means the nightly pipeline ran but loaded nothing — a *silent success* the CronJob
-- staleness alert cannot see (the job completes 0-rows and looks "fresh"). Fail the build so a blank
-- dashboard never passes for live data. (A dbt singular test fails when the query returns rows.)
select 'policy_portfolio is empty — pipeline produced no served rows' as failure
where not exists (select 1 from {{ ref('policy_portfolio') }})
