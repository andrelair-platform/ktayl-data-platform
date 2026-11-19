# Semantic layer (Cube) — ADR-009

Governed metric definitions over the Data Platform gold marts (CNPG `analytics.lake`). Cube is the
**semantic layer**: each business metric is defined **once** here and consumed by **Metabase** (via Cube's
Postgres-wire **SQL API**, natively — Cube looks like a database) and by apps/AI (REST + GraphQL). This
replaces metrics being re-derived per Metabase question.

```
S3 lake → dbt-duckdb → CNPG gold marts (analytics.lake)  →  Cube (this model)  →  Metabase / apps / AI
          (transforms)        (physical tables)              (governed metrics)      (consumers)
```

- **Model** = `model/cubes/*.yml` — cubes with `measures` + `dimensions` over a `sql_table`.
- **Deployment** = `minicloud-gitops/platform/data/data-platform/08-cube.yaml` (the Cube Deployment clones
  this repo for the model at pod start, same deploy-vs-code split as the lake jobs).
- **Status** = **minimal proof on dev** (ADR-009 is trigger-gated; this spike de-risks the Cube choice).
  First cube: `policy_portfolio` over `lake.policy_portfolio_lake` (total/active policies, active ratio).

**Growth path:** add cubes over `fact_policy` + the `dim_*` (joins → LOB/customer/period views), and the
definitional metrics (GWP, loss ratio, combined ratio) once ktayl-core Phase-1b data lands (issue #28).

## Verify (SQL API — the Metabase path)
```sql
-- psql to Cube's pg-wire SQL API (port 15432), user `cube`:
SELECT product_code, MEASURE(total_policies), MEASURE(active_policies), MEASURE(active_ratio)
FROM policy_portfolio GROUP BY product_code ORDER BY 2 DESC;
```
