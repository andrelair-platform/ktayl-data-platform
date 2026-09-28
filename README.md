# ktayl-data-platform

Board **#5 (Data Platform)** — the **code** for the ktayl analytical data platform (dbt transforms +
ingestion + Metabase provisioning). This is a **code repo**; it is **deployed by `minicloud-gitops`**
(`manifests/data-platform/` — CNPG, ESO, netpols, CronJobs, Metabase, ArgoCD app), which git-clones this
repo and runs the code. (App source here / deployment config there — the platform's two-repo convention.)

Slice 1 = the **first thin vertical slice** per the [EA blueprint doctrine](https://andrelair-platform.github.io/minicloud-platform-docs/insurance-platform/enterprise-architecture-blueprint):
**one real live source → just-enough medallion → one data product → BI.** Deliberately *not* a generic
connector framework or an OLAP cluster for sources that don't exist yet.

> Two-layer model: this is the **ktayl-solution IS** (the insurer). Not Retrieva, not a certification deliverable.

## Layout

```
dbt/       dbt project (dbt_project.yml, profiles.yml, macros/, models/staging, models/marts)
ingest/    ingest_policy.sh        (live policy DB → analytics.raw, full-refresh COPY)
           ingest_underwriting.sh  (Slice 2: live underwriting DB → analytics.raw.uw_*, full-refresh COPY)
metabase/  provision_dashboard.py  (idempotent, secret-free: creates the analytics DB source + cards + dashboard)
```

## What Slice 1 delivers

```
ktayl-policy-service (LIVE Postgres — the only fully-live business source)
        │  ingest/ingest_policy.sh  (full-refresh COPY; CDC later)
        ▼
   raw.*              →  dbt staging (curated schema)  →  dbt marts (business schema)
   policies/coverages/   stg_policies / stg_premiums /     policy_portfolio  ◄── the data product
   premiums              stg_coverages
        ▼
   Metabase dashboard: Policy Portfolio (GWP proxy · TIV · counts by LOB/status/inception)
```

**Data product `policy_portfolio`** (grain = policy) — grounded on real source columns only:
- `gwp_eur` — **authoritative GWP** (Slice 2): `coalesce(underwriting rated premium, annualised proxy)`. *Seeds P2 (margin/portfolio).*
- `underwriting_premium_eur`, `rate_table_version`, `bound_via_underwriting` — the authoritative UW-origin columns (null for legacy/direct policies).
- `annualised_premium_eur` — GWP proxy, kept for lineage/comparison.
- `total_insured_amount_eur` — TIV. *Seeds P1/P3 (exposure/accumulation).*
- `scheduled_premium_eur`, `paid_premium_eur`, `coverage_count`, dims: `product_code`, `status`, `inception_year`.

## Slice 2 — underwriting as the authoritative GWP source (closes DP-007)

The **second real live pipeline** (need-first, not a generic connector framework). The underwriting
rating engine now emits real premiums (`quote.premium_minor`, eurocents) and links them to bound
policies (`binding.policy_number`), so the GWP proxy is promoted to the **authoritative rated premium**:

```
ktayl-underwriting (LIVE Postgres — 2nd real source: quote + binding)
        │  ingest/ingest_underwriting.sh  (full-refresh COPY, explicit column lists)
        ▼
   raw.uw_quotes / raw.uw_bindings  →  stg_uw_quotes / stg_uw_bindings (curated)
        ▼
   policy_portfolio (business): binding → quote by quote_id, keyed to the policy by policy_number
        → gwp_eur = coalesce(underwriting_premium_eur, annualised_premium_eur)
```

- **Join:** `binding.policy_number` = `policy_portfolio.policy_number`; premium via `binding.quote_id → quote.premium_minor`.
- **Authoritative for** underwriting-originated policies; **proxy fallback** for legacy/direct ones.
- The old proxy column (`annualised_premium_eur`) is kept, labelled, for lineage/comparison.

## Stack (light-first, fits the constrained cluster)

| Layer | Tool | Note |
|---|---|---|
| Storage (medallion) | **Postgres** (CNPG `analytics`), schemas `raw`/`curated`/`business` | own DB (no shared operational DB — ADR-005) |
| Ingestion | **CronJob** `ingest/ingest_policy.sh` (pg_dump→psql COPY) | full-refresh; CDC (Debezium→NATS) is Slice-2 |
| Transform | **dbt-postgres** (`dbt/`) — staging→marts + schema tests | run via CronJob after ingest |
| BI / serve | **Metabase** | Authentik SSO, reads `business` schema |

ClickHouse/Trino deferred until a real volume/perf need (need-first gate).

## Run locally (against a dev analytics Postgres)

```bash
# env: ANALYTICS_PG_* + POLICY_PG_* + UW_PG_*
sh ingest/ingest_policy.sh                 # land raw.policies/coverages/premiums
sh ingest/ingest_underwriting.sh           # Slice 2: land raw.uw_quotes/uw_bindings
cd dbt && dbt deps && dbt build            # staging→marts + tests (build = run + test)
```

## Provision the Metabase dashboard (idempotent, secret-free)

```bash
# reads Vault secret/platform/data-platform for creds; safe to re-run / run on a fresh cluster
VAULT_TOKEN=... python3 metabase/provision_dashboard.py
```

## Run the pipeline in-cluster (on demand, not just the 02:00/02:30 cron)

```bash
kubectl create job -n data-platform dp-ingest-manual --from=cronjob/dp-ingest-policy   # prod → raw
kubectl create job -n data-platform dp-dbt-manual    --from=cronjob/dp-dbt-build        # raw → staging → business.policy_portfolio
kubectl exec -n data-platform dp-postgres-1 -- psql -U postgres -d analytics \
  -c "SELECT * FROM business.policy_portfolio;"                                          # verify
```

## Metabase — one-time UI setup (SSO is a follow-up; internal Tailscale-gated for now)

URL: **https://metabase.10.0.0.200.nip.io** (needs Tailscale + the minicloud CA trusted). The pod runs
in `data-platform`; its own metadata DB is the `metabase` database on the `dp-postgres` CNPG cluster
(auto-created via the `Database` CR, creds from Vault `secret/platform/data-platform`).

1. **First visit** → create the admin account (Metabase's own login for now).
2. **Add the analytics database** as a data source:
   - Type **PostgreSQL** · Host `dp-postgres-rw.data-platform.svc.cluster.local` · Port `5432`
   - Database `analytics` · User `analytics` · Password = Vault `secret/platform/data-platform` → `analytics-password`
   - Schemas to expose: **`business`** (the serve layer; `curated`/`raw` are internal).
3. **Build the Policy Portfolio dashboard** over `business.policy_portfolio` (grain = policy):
   - GWP proxy = `sum(annualised_premium_eur)` · TIV = `sum(total_insured_amount_eur)`
   - policy count by `status` / `product_code` / `inception_year`
4. The seeded demo row `TEST-DP-SLICE1-001` (GWP €12,000 · TIV €1,000,000) is kept so the dashboard has data before real prod policies exist.

**TODO (hardening):** put Metabase behind Authentik SSO (forward-auth or Metabase OIDC) instead of its
local admin; re-add restricted egress via a CiliumNetworkPolicy (`toEntities: [kube-apiserver, world]`).

## Assumptions to confirm with the Policy domain (before treating metrics as authoritative)

1. **Minor units** — `amount`/`insured_amount` are BIGINT; assumed **cents** (÷100 → EUR). Confirm.
2. **Premium semantics** — are `premiums` rows **installments** (annualise = ×cadence) or a single annual figure? The GWP-proxy annualisation assumes installments; confirm before it's the official GWP.

## Next (Slice 1 → deployable → Slice 2)

- **Deploy (next PR):** `data-platform` namespace + quota · CNPG `analytics` cluster (+ AppProject sourceRepos/destination/namespaceResourceWhitelist + the cnpg ingress netpol — see [[feedback_cnpg_onboarding_gotchas]]) · ESO secrets (policy + analytics creds) · ingest + dbt CronJobs · Metabase Helm app · ArgoCD apps. Then verify raw→marts→dashboard live.
- **Slice 2:** add a second real source when the next domain ships; generalise the ingestion from 2–3 real pipelines (never a generic framework up-front). CDC over batch. Add MDM-keyed Customer 360 once MDM exists.
