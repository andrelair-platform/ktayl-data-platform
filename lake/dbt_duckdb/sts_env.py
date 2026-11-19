#!/usr/bin/env python3
"""Print `export AWS_*` lines with short-lived STS read creds from Vault (ADR-008).

Used by entrypoint.sh (`eval "$(python3 sts_env.py)"`) so dbt-duckdb's profiles.yml can pick the S3
creds up from env_var(). Keyless: pod SA → Vault k8s-auth (role=data-lake-reader) → aws/sts/data-lake-read.
"""
import json
import os
import urllib.request

SA_TOKEN = "/var/run/secrets/kubernetes.io/serviceaccount/token"


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Vault-Token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


addr = os.environ["VAULT_ADDR"].rstrip("/")
with open(SA_TOKEN, encoding="utf-8") as f:
    jwt = f.read().strip()
tok = _req(f"{addr}/v1/auth/kubernetes/login",
           {"role": os.environ.get("VAULT_ROLE", "data-lake-reader"), "jwt": jwt})["auth"]["client_token"]
d = _req(f"{addr}/v1/{os.environ.get('VAULT_AWS_PATH', 'aws/sts/data-lake-read')}", token=tok)["data"]
print(f"export AWS_ACCESS_KEY_ID='{d['access_key']}'")
print(f"export AWS_SECRET_ACCESS_KEY='{d['secret_key']}'")
print(f"export AWS_SESSION_TOKEN='{d['security_token']}'")
