#!/bin/sh
# dbt-duckdb lake transform entrypoint (ADR-008). Installs dbt-duckdb, fetches short-lived S3 STS creds
# from Vault, then runs the medallion (staging over S3 Parquet → marts materialised into CNPG).
set -eu
pip install --quiet --no-cache-dir --user dbt-duckdb==1.9.1
export PATH="${HOME}/.local/bin:${PATH}"

# short-lived S3 read creds → env (profiles.yml reads them via env_var)
eval "$(python3 /repo/lake/dbt_duckdb/sts_env.py)"

cd /repo/lake/dbt_duckdb
dbt run  --profiles-dir . --project-dir . --no-use-colors
dbt test --profiles-dir . --project-dir . --no-use-colors
