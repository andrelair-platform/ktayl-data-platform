# ADR-010 — Ingestion = dlt; Orchestration = Dagster (ML via Dagster assets + MLflow)

- **Status:** Accepted. Engines chosen (dlt + Dagster). **Minimal proof stood up on DEV (2026-11-19)** —
  a full `dlt → dbt → Dagster → sklearn → MLflow` asset graph materialized end-to-end (RUN_SUCCESS);
  dlt_raw.policy=11, dlt_marts.portfolio=10, MLflow registered model `ktayl-policy-active-demo` v1.
  This is a **spike ahead of the trigger** (de-risks the choice), **not** the production build.
- **Date:** 2026-11-19
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS (organisational context — not Retrieva)
- **Board:** Data Platform (#5)
- **Decider:** owner (architecture call)
- **Relation:** replaces the custom psql/DuckDB ingest scripts + the k8s-CronJob scheduling with
  industry-standard tools. Composes with ADR-006/007/008 (lake + warehouse) + ADR-009 (Cube semantic layer).

## Context

The data platform's **ingestion** was hand-written scripts (`ingest_*.sh` psql COPY + `land_to_s3.py`
DuckDB→Parquet) and its **orchestration** was four chained **k8s CronJobs**. That is fine at toy volume
but (a) means writing/maintaining a bespoke script per source, and (b) gives no dependency graph,
backfills, retries-with-lineage, or run observability. We want industry-standard tooling that still fits a
**sovereign, self-hosted, resource-constrained** cluster and carries **portfolio/CV** value.

Two **separate** decisions (often conflated): the **EL/ingestion** tool and the **orchestrator**.

**Verified 2026 landscape (sources below):**
- *Ingestion:* **Airbyte** (700+ connectors, heavy self-host) · **Meltano** (Singer, lighter) · **dlt** (a
  **Python library**, code-native, schema inference + incremental, no platform to run).
- *Orchestration:* **Airflow** (#1 by install base / job-postings, heaviest) · **Dagster** (asset-centric,
  **best for dbt-heavy stacks** — one asset per dbt model + partition-aware backfills; winning greenfield)
  · **Prefect** (lightest; ML/lightweight lane). *(Prefect acquired Dagster Labs, July 2026.)*

## Decision

1. **Ingestion = `dlt`.** A library (zero standing infra — runs in the existing CronJob/Job or under
   Dagster), with incremental load + schema evolution + state, and **native DuckDB/Postgres/S3
   destinations** = our exact stack. It directly **replaces the custom COPY/DuckDB scripts**.

2. **Orchestration = Dagster.** Its **software-defined assets** model fits our dbt-heavy stack best
   (dagster-dbt = one asset per dbt model, lineage + partition backfills), it is **lighter than Airflow**,
   and it is where new platform teams are placing bets. It natively orchestrates **both dlt and dbt** as
   one asset graph.

3. **ML stays in this stack — no Prefect needed.** Dagster expresses ML as **assets**
   (`features → model → evaluation`) with full data→model **lineage**, and composes with the platform's
   existing **MLflow** (tracking + model registry). Retraining = partitions + sensors + backfills. (Prefect's
   edge — highly dynamic/imperative graphs — isn't our shape; and post-acquisition it's the same company.)

4. **Target combined stack:** `dlt (ingest) → dbt (transform) → Dagster (orchestrate) → MLflow (ML)` on
   DuckDB + CNPG + S3 — the reference modern self-hosted lakehouse+ML stack, every piece designed to compose.

## Adoption trigger (prod graduation)

The minimal proof runs today; **graduate to the production orchestrator** when any holds: the pipeline DAG
outgrows simple CronJob chaining (real dependencies/backfills), you need the lineage UI + run observability
day-to-day, or a real ML retraining cadence appears. Until then dlt can also run under the existing CronJobs.

## Consequences

- **Positive:** stop hand-writing ingest scripts (dlt, maintained); one **asset lineage graph** across
  ingest+transform+ML; governed ML/MLOps (reproducible, auditable — a **EU AI Act / DORA** asset);
  self-hosted + sovereign; strong modern-data/ML-engineer CV signal. dlt adds **~zero** infra.
- **Accepted cost:** Dagster is a **standing service** (webserver [+ daemon in prod]) — a modest footprint
  on a tight cluster; adopt need-first. The proof uses webserver-only + in-process runs + SQLite storage;
  **prod** = own namespace + the daemon + CNPG run storage (dagster-postgres) + K8sRunLauncher + SSO ingress.
- **Reversibility:** all OSS + self-hosted; the Dagster code is version-controlled; teardown = delete the
  Deployment (the dlt pipelines + dbt still run standalone). The warehouse underneath is untouched.

## Alternatives considered

- **Airbyte** (ingest) — rejected for now: heavy self-host footprint, over-provisioned for our volume; pick
  only if broad **SaaS**-connector coverage becomes the need. **Meltano** — viable lighter Singer option;
  dlt chosen for being code-native + lightest + native to DuckDB/Postgres.
- **Airflow** (orchestrate) — rejected for now: most job-postings but the **heaviest** to run here, and
  task-centric (less dbt-native than Dagster). **Prefect** — lightest, but less dbt-asset-native; ML lane
  covered by Dagster+MLflow for our asset-shaped ML.
- **Keep k8s CronJobs** — fine at current scale; kept as the fallback until the Dagster trigger fires.

## Related

- ADR-006/007/008 (lake + warehouse) · ADR-009 (Cube semantic layer) · `cloud-adoption.md` (need-first +
  standing-service gate) · `wire-llmops` / the platform MLflow.

**Sources (verified 2026-11-19):**
[Orchestration in 2026 (Airflow 3 vs Dagster vs Prefect)](https://datalakehousehub.com/blog/orchestration-in-2026/) ·
[Dagster vs Prefect vs Airflow 2026 (Orchestra)](https://www.getorchestra.io/blog/dagster-vs-prefect-vs-airflow-complete-data-orchestration-comparison-2026) ·
[Best open-source ELT tools 2026 (Bruin)](https://getbruin.com/blog/best-open-source-elt-tools-2026/) ·
[Data pipeline/ETL platforms — dlt/Airbyte/Meltano](https://www.vibereference.com/backend-and-data/data-pipeline-etl-platforms).
