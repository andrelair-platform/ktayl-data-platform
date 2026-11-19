#!/usr/bin/env python3
"""DuckDB OLAP transform — read Parquet from the S3 raw lake and materialise into CNPG (ADR-008).

This is the OLAP-engine half: storage/compute separation, a vectorized columnar engine (DuckDB) that
reads Parquet from S3 directly (httpfs) and writes the serving result into CloudNativePG (the serving
store Metabase reads). Keyless auth: the pod SA logs into Vault (role=data-lake-reader) → short-lived STS
read creds (aws/sts/data-lake-read). No static AWS key.

    S3 raw (Parquet)  →  DuckDB (read + transform)  →  CNPG analytics.<schema>.<table>  →  Metabase

MVP: a straight materialise (SELECT * FROM read_parquet(glob) → CNPG table). dbt-duckdb models layer on
top of exactly this connection pattern (staging → curated → marts) — this proves the chain end-to-end.
"""
import json
import os
import sys
import urllib.request

SA_TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"


def _req(url: str, payload: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def vault_sts_creds(role: str, sts_path: str) -> tuple[str, str, str]:
    """Vault k8s-auth login (pod SA) → read assumed-role STS creds from the aws engine."""
    addr = os.environ["VAULT_ADDR"].rstrip("/")
    with open(SA_TOKEN, encoding="utf-8") as f:
        jwt = f.read().strip()
    tok = _req(f"{addr}/v1/auth/kubernetes/login", {"role": role, "jwt": jwt})["auth"]["client_token"]
    d = _req(f"{addr}/v1/{sts_path}", token=tok)["data"]
    return d["access_key"], d["secret_key"], d["security_token"]


def main() -> int:
    role = os.environ.get("VAULT_ROLE", "data-lake-reader")
    sts_path = os.environ.get("VAULT_AWS_PATH", "aws/sts/data-lake-read")
    ak, sk, st = vault_sts_creds(role, sts_path)
    print("[transform] obtained short-lived STS read creds from Vault", flush=True)

    import duckdb

    region = os.environ["AWS_REGION"]
    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs; INSTALL postgres; LOAD postgres;")
    con.execute(f"SET s3_region='{region}'; SET s3_endpoint='s3.{region}.amazonaws.com';")
    con.execute(
        f"SET s3_access_key_id='{ak}'; SET s3_secret_access_key='{sk}'; SET s3_session_token='{st}';"
    )

    dsn = (
        f"host={os.environ['ANALYTICS_PG_HOST']} port={os.environ.get('ANALYTICS_PG_PORT', '5432')} "
        f"dbname={os.environ['ANALYTICS_PG_DB']} user={os.environ['ANALYTICS_PG_USER']} "
        f"password={os.environ['ANALYTICS_PG_PASSWORD']}"
    )
    con.execute(f"ATTACH '{dsn}' AS pg (TYPE postgres)")

    source_glob = os.environ["SOURCE_GLOB"]
    schema = os.environ.get("DEST_SCHEMA", "lake")
    table = os.environ["DEST_TABLE"]

    con.execute(f"CREATE SCHEMA IF NOT EXISTS pg.{schema}")
    con.execute(f"DROP TABLE IF EXISTS pg.{schema}.{table}")
    con.execute(f"CREATE TABLE pg.{schema}.{table} AS SELECT * FROM read_parquet('{source_glob}')")
    n = con.execute(f"SELECT count(*) FROM pg.{schema}.{table}").fetchone()[0]
    print(f"[transform] materialised pg.{schema}.{table}: {n} rows from {source_glob}", flush=True)
    print("[transform] OK — S3 → DuckDB → CNPG chain verified", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
