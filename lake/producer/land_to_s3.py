#!/usr/bin/env python3
"""Producer — land a source domain's tables into the S3 raw lake as Parquet (ADR-008).

Auth is keyless: the pod's ServiceAccount token logs into Vault's Kubernetes auth
(role=data-lake-writer) and reads short-lived STS write creds from the aws secrets engine
(aws/sts/data-lake-write, scoped to s3:PutObject on raw/*). No static AWS key in k8s or Git.

DuckDB does both halves: postgres_scanner reads the live source DB, httpfs writes Parquet to S3.
Layout: s3://<bucket>/raw/<domain>/<table>/dt=<YYYY-MM-DD>/<table>.parquet  (Hive-style, replayable).
"""
import datetime
import json
import os
import sys
import urllib.request

SA_TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"


def _post(url: str, payload: dict | None = None, token: str | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def vault_sts_creds() -> tuple[str, str, str]:
    """Vault k8s-auth login (pod SA) → read assumed-role STS creds from the aws engine."""
    addr = os.environ["VAULT_ADDR"].rstrip("/")
    role = os.environ["VAULT_ROLE"]
    sts_path = os.environ["VAULT_AWS_PATH"]  # e.g. aws/sts/data-lake-write
    with open(SA_TOKEN, encoding="utf-8") as f:
        jwt = f.read().strip()
    login = _post(f"{addr}/v1/auth/kubernetes/login", {"role": role, "jwt": jwt})
    client_token = login["auth"]["client_token"]
    sts = _post(f"{addr}/v1/{sts_path}", token=client_token)["data"]
    return sts["access_key"], sts["secret_key"], sts["security_token"]


def main() -> int:
    ak, sk, st = vault_sts_creds()
    print("[land] obtained short-lived STS write creds from Vault", flush=True)

    import duckdb  # imported after auth so a cred failure fails fast/cheap

    con = duckdb.connect()
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_region='{os.environ['AWS_REGION']}';")
    con.execute(
        f"SET s3_access_key_id='{ak}'; SET s3_secret_access_key='{sk}'; SET s3_session_token='{st}';"
    )

    bucket = os.environ["LAKE_BUCKET"]

    # SELFTEST mode — prove the keyless S3-write path (STS + httpfs) without the source DB.
    # Writes a synthetic Parquet to raw/_selftest/ and reads it back. Used to verify step 2 in isolation
    # while the real policy source is being (re)pointed. Set SELFTEST=1.
    if os.environ.get("SELFTEST") == "1":
        dest = f"s3://{bucket}/raw/_selftest/dt={datetime.date.today().isoformat()}/probe.parquet"
        con.execute(f"COPY (SELECT i AS n, i * 2 AS double FROM range(10) t(i)) TO '{dest}' (FORMAT parquet, OVERWRITE_OR_IGNORE)")
        back = con.execute(f"SELECT count(*), sum(double) FROM read_parquet('{dest}')").fetchone()
        print(f"[selftest] wrote + read back {dest}: rows={back[0]} sum_double={back[1]}", flush=True)
        print("[selftest] OK — keyless S3 write/read verified", flush=True)
        return 0

    con.execute("INSTALL postgres; LOAD postgres;")
    src = (
        f"host={os.environ['POLICY_PG_HOST']} port={os.environ.get('POLICY_PG_PORT', '5432')} "
        f"dbname={os.environ['POLICY_PG_DB']} user={os.environ['POLICY_PG_USER']} "
        f"password={os.environ['POLICY_PG_PASSWORD']}"
    )
    con.execute(f"ATTACH '{src}' AS src (TYPE postgres, READ_ONLY)")

    bucket = os.environ["LAKE_BUCKET"]
    domain = os.environ.get("DOMAIN", "policy")
    src_schema = os.environ.get("SRC_SCHEMA", "public")
    tables = [t.strip() for t in os.environ.get("TABLES", "policies,coverages,premiums").split(",") if t.strip()]
    dt = datetime.date.today().isoformat()

    for t in tables:
        dest = f"s3://{bucket}/raw/{domain}/{t}/dt={dt}/{t}.parquet"
        n = con.execute(f"SELECT count(*) FROM src.{src_schema}.{t}").fetchone()[0]
        con.execute(f"COPY (SELECT * FROM src.{src_schema}.{t}) TO '{dest}' (FORMAT parquet, OVERWRITE_OR_IGNORE)")
        print(f"[land] {t}: {n} rows -> {dest}", flush=True)

    print(f"[land] done — {len(tables)} table(s) landed for domain '{domain}' @ dt={dt}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
