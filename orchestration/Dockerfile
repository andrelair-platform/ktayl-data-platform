# Dagster code-location image (ADR-010) — bundles the dlt + dbt + Dagster + ML stack.
# The dbt manifest is compiled at BUILD time (dbt parse, offline via env_var defaults) so dagster-dbt can
# load assets without a DB connection at import. Runs as non-root (Gatekeeper).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DAGSTER_HOME=/opt/dagster/home \
    DBT_PROFILES_DIR=/app/dbt_demo \
    PATH=/root/.local/bin:$PATH

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

# Compile the dbt manifest offline (profiles.yml uses env_var defaults) + prep DAGSTER_HOME.
RUN cd /app/dbt_demo && dbt parse --profiles-dir . \
    && mkdir -p /opt/dagster/home && cp /app/dagster.yaml /opt/dagster/home/dagster.yaml

# Non-root (uid 1000) + writable dirs it needs at runtime.
RUN useradd -u 1000 -m dagster \
    && chown -R 1000:1000 /app /opt/dagster
USER 1000

EXPOSE 3000
# Default: the webserver (the UI). The proof Job overrides the command with `dagster asset materialize`.
CMD ["dagster-webserver", "-h", "0.0.0.0", "-p", "3000", "-w", "/app/workspace.yaml"]
