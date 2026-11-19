# S3 raw-lake runtime (ADR-008)

The OLAP half of the Data Platform: **storage/compute separation** on top of the CNPG serving store.

```
source DB → producer → S3 raw lake (Parquet)  →  DuckDB transform  →  CNPG serving → Metabase
            (STS write)   (private, SSE-S3,         (vectorized           (gold marts)
                           versioned, eu-west-1)     columnar OLAP;
                                                     reads Parquet direct)
```

Postgres (CNPG) stays the **serving** tier; **DuckDB is the OLAP engine** (reads Parquet from S3 via
httpfs, no custom loader). The lake is **AWS S3** (`minicloud-data-lake-625830750465`, eu-west-1) — the
one deliberate cloud dependency (ADR-008): real columnar storage/compute separation + portfolio AWS
experience, at ~S3-pennies/mo under a $10 budget guardrail.

## Keyless auth (no static AWS keys anywhere)

Each workload's ServiceAccount logs into **Vault Kubernetes auth** and reads short-lived **STS** creds
from the Vault aws secrets engine (`assumed_role`), scoped by IAM:

| Workload | SA | Vault role | Vault path | S3 scope |
|---|---|---|---|---|
| producer (`lake/producer/land_to_s3.py`)   | `dp-ingest` | `data-lake-writer` | `aws/sts/data-lake-write` | PutObject/Get on `raw/*` |
| transform (`lake/transform/transform_s3_to_cnpg.py`) | `dp-duckdb` | `data-lake-reader` | `aws/sts/data-lake-read` | read-only, whole bucket |

AWS side (bucket, IAM policies/roles, Vault principal) is OpenTofu in `minicloud-cloud`
(`data-lake.tf` + `data-lake-vault-auth.tf`); the Vault engine is configured by
`minicloud-cloud/scripts/configure-vault-aws-engine.sh`. Deployment (CronJobs/SAs) is in
`minicloud-gitops/platform/data/data-platform/06-lake-producer.yaml` + `07-lake-transform.yaml`.

## Status

Runtime **built + verified end-to-end** (keyless `S3 → DuckDB → CNPG` proven via a probe object). The
CronJobs are **suspended** until the policy source is repointed: the old source (`ktayl-prod` policy DB)
died when policy folded into `ktayl-core` (ADR-014/015) and prod `ktayl-core` has no policy data yet.
To go live: repoint `POLICY_PG_HOST/DB/SRC_SCHEMA` at `ktayl-core`, then unsuspend both CronJobs.

Datasets + PII/retention classification: `lake/registry/datasets.yaml`.
Next: port the transform to **dbt-duckdb** (staging→curated→marts) on the same connection pattern.
