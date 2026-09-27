---
id: DP-003-dbt-staging-source-tests
title: "dbt staging over the 3 real policy tables + source tests"
status: Done
type: Story
epic: data-platform-slice-1
milestone: "Data Platform Slice 1 — Policy Portfolio"
estimate: 3
labels: [data-platform, dbt, testing]
priority: P2
assignee: AndreLiar
repo: andrelair-platform/ktayl-data-platform
project: 5
initiative: IS Foundations
---

*As the* **platform**, *I want* typed/cleaned staging models over the raw policy tables with source
tests *so that* schema drift fails loudly before it reaches the data product.

## Acceptance criteria
- `stg_policies`, `stg_coverages`, `stg_premiums` build in the `curated` schema.
- Source tests pass: `unique` / `not_null` / `accepted_values` on key columns.
- `generate_schema_name` override so custom schemas are verbatim (`curated`, not `curated_curated`).

## Code
`dbt/models/staging/*.sql` + `_sources.yml`; `dbt/macros/generate_schema_name.sql`.

## Status
✅ Done — staging builds; tests pass.
