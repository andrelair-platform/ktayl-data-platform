# Orchestration — Dagster (dlt + dbt + ML) — ADR-010

The modern self-hosted data+ML stack as **one Dagster asset graph**:

```
raw_policy (dlt)  →  portfolio (dbt)  →  policy_features → policy_model → model_evaluation
ktayl-core policy    analytics.dlt_marts   pandas            sklearn→MLflow    MLflow metric
```

- **Ingest = dlt** — replaces the hand-written COPY/DuckDB scripts (schema inference + incremental). `assets.py:raw_policy`.
- **Transform = dbt** — one Dagster asset per dbt model via dagster-dbt (`dbt_demo/`), lineage-linked to the dlt source.
- **Orchestrate = Dagster** — asset graph + lineage UI + backfills; `ktayl_orchestration/definitions.py`.
- **ML = scikit-learn + MLflow** — trained/tracked/registered in the platform's MLflow (ns `ai`). *Demo model on tiny data — proves the path, not a production model.*

**Image:** `orchestration/Dockerfile` → `ghcr.io/andrelair-platform/ktayl-data-platform-orchestration`
(dbt manifest compiled offline at build). **Deploy:** `minicloud-gitops/platform/data/data-platform/09-dagster.yaml`.

## Status
Minimal proof (ADR-010 is need-first/trigger-gated). First run headless via `dagster asset materialize
--select "*"`; the standing webserver gives the lineage UI. Prod graduation = own namespace, Postgres
(CNPG) run storage, K8sRunLauncher, SSO ingress, schedules/sensors, + the real feature/retrain pipelines.

## Run headless
```bash
dagster asset materialize -m ktayl_orchestration.definitions --select "*"
```
Env: `SOURCE_PG_*` (ktayl-core policy), `ANALYTICS_PG_*` (CNPG analytics), `MLFLOW_TRACKING_URI`.
