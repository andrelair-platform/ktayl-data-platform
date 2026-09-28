#!/usr/bin/env sh
# Slice-2 ingestion: full-refresh copy of the 2 live underwriting tables (quote + binding) →
# analytics.raw.uw_*. Same decoupled full-refresh COPY pattern as ingest_policy.sh — the data
# platform keeps its own copy so it never couples to the operational source. Explicit column
# lists (not SELECT *) so the raw schema is a stable contract independent of source drift.
# All connection params via env (ESO-injected). CDC (Debezium→NATS) is a later upgrade.
set -eu

: "${UW_PG_HOST:?}" "${UW_PG_USER:?}" "${UW_PG_PASSWORD:?}" "${UW_PG_DB:?}"
: "${ANALYTICS_PG_HOST:?}" "${ANALYTICS_PG_USER:?}" "${ANALYTICS_PG_PASSWORD:?}" "${ANALYTICS_PG_DB:?}"

SRC="postgresql://${UW_PG_USER}:${UW_PG_PASSWORD}@${UW_PG_HOST}:${UW_PG_PORT:-5432}/${UW_PG_DB}"
DST="postgresql://${ANALYTICS_PG_USER}:${ANALYTICS_PG_PASSWORD}@${ANALYTICS_PG_HOST}:${ANALYTICS_PG_PORT:-5432}/${ANALYTICS_PG_DB}"

echo "[ingest-uw] ensuring raw schema + tables"
psql "$DST" -v ON_ERROR_STOP=1 <<'SQL'
CREATE SCHEMA IF NOT EXISTS raw;
-- ids are text (string uuids) in the underwriting source; premium_minor is BIGINT eurocents.
CREATE TABLE IF NOT EXISTS raw.uw_quotes   (id text, submission_id text, premium_minor bigint, currency text, rate_table_version int, created_by text, created_at timestamptz);
CREATE TABLE IF NOT EXISTS raw.uw_bindings (id text, submission_id text, quote_id text, policy_number text, pas_policy_id text, status text, event_published boolean, bound_at timestamptz, bound_by text);
SQL

# quote → raw.uw_quotes (breakdown JSON intentionally NOT ingested — not needed for the mart)
echo "[ingest-uw] refreshing raw.uw_quotes"
psql "$DST" -v ON_ERROR_STOP=1 -c "TRUNCATE raw.uw_quotes;"
psql "$SRC" -v ON_ERROR_STOP=1 -c "\copy (SELECT id, submission_id, premium_minor, currency, rate_table_version, created_by, created_at FROM quote) TO STDOUT WITH (FORMAT csv)" \
  | psql "$DST" -v ON_ERROR_STOP=1 -c "\copy raw.uw_quotes FROM STDIN WITH (FORMAT csv)"
psql "$DST" -tAc "SELECT '[ingest-uw] raw.uw_quotes rows=' || count(*) FROM raw.uw_quotes;"

# binding → raw.uw_bindings
echo "[ingest-uw] refreshing raw.uw_bindings"
psql "$DST" -v ON_ERROR_STOP=1 -c "TRUNCATE raw.uw_bindings;"
psql "$SRC" -v ON_ERROR_STOP=1 -c "\copy (SELECT id, submission_id, quote_id, policy_number, pas_policy_id, status, event_published, bound_at, bound_by FROM binding) TO STDOUT WITH (FORMAT csv)" \
  | psql "$DST" -v ON_ERROR_STOP=1 -c "\copy raw.uw_bindings FROM STDIN WITH (FORMAT csv)"
psql "$DST" -tAc "SELECT '[ingest-uw] raw.uw_bindings rows=' || count(*) FROM raw.uw_bindings;"

echo "[ingest-uw] done"
