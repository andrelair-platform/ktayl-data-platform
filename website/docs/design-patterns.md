---
title: Design Patterns
sidebar_position: 4
---

# Design Patterns

The concrete patterns this codebase uses. Each entry states the pattern, the problem it solves, and where
it lives in the repo — so an interviewer or auditor can trace intent to code.

## Medallion architecture (raw → curated → business)

**Problem:** raw operational data is not directly fit for analytics; mixing landing, cleaning and business
logic in one step makes lineage and testing impossible.

**Pattern:** layered refinement across three schemas — `raw` (landing), `curated` (typed / cleaned), and
`business` (the serve layer). Each layer has a single responsibility.

**Where:** the schemas are set in `dbt/dbt_project.yml` — `staging` models `+schema: curated`
(materialised as views), `marts` models `+schema: business` (materialised as tables). `raw` is created by
the ingest script (`ingest/ingest_policy.sh`).

## ELT, not ETL

**Problem:** transforming data in a separate engine before loading couples the pipeline to that engine and
loses the ability to re-transform history cheaply.

**Pattern:** **load raw first, transform in-warehouse.** The ingest step only lands 1:1 copies; all
transformation is dbt SQL that runs inside the analytics database.

**Where:** `ingest/ingest_policy.sh` (load only) then the dbt models in `dbt/models/` (transform in the
warehouse).

## Thin vertical slice

**Problem:** building a generic connector framework or a heavy OLAP cluster ahead of demand is waste when
most source domains do not exist yet.

**Pattern:** one live source → just-enough medallion → one data product. The anti-pattern deliberately
avoided is the generic connector framework / pre-built heavy OLAP — deferred behind a need-first gate.

**Where:** the doctrine is stated in `dbt/dbt_project.yml` header comments and `AGENTS.md` (*Doctrine*);
Slice 1 is exactly one source (Policy) → one product (`policy_portfolio`).

## Idempotent full-refresh ingestion

**Problem:** an ingestion that appends or partially updates can leave the target in an inconsistent state
if a run is interrupted or repeated.

**Pattern:** **atomic per-table truncate + COPY** so any re-run converges to the same state. The trade-off
against CDC (lower latency, incremental) is accepted for now — CDC (Debezium -> NATS) is the deferred
Slice-2 upgrade.

**Where:** `ingest/ingest_policy.sh` — per table it runs `TRUNCATE raw.<t>` then streams the source via
`\copy ... TO STDOUT` piped into `\copy raw.<t> FROM STDIN`.

## Idempotent provisioning (upsert-by-name)

**Problem:** a provisioning script that only "creates" produces duplicates on re-run and is not
reproducible on a fresh cluster.

**Pattern:** **login-first, then get-or-create by name.** The provisioner logs in first (the reliable
test that an instance is already set up), then ensures the DB source, each card, and the dashboard by
matching on name and only creating what is missing — safe to run repeatedly.

**Where:** `metabase/provision_dashboard.py` — login-first session handling, then match-by-name for the
`ktayl analytics` DB source, the cards, and the `Policy Portfolio (ktayl)` dashboard.

## Deployment-vs-code separation / git-clone-at-runtime

**Problem:** mixing application code with Kubernetes deployment config in one repo blurs ownership and
breaks the GitOps model.

**Pattern:** **code lives here; deployment config lives in `minicloud-gitops`.** The gitops CronJobs
**git-clone this repo** at runtime to run the ingest / dbt code — they do not vendor it. This follows the
org rule (`conventions.md` — *Deployment repo vs code repo*), which was written after this exact code was
first wrongly placed in the gitops repo and then moved here.

**Where:** the k8s manifests are in `minicloud-gitops/manifests/data-platform/`; the CronJobs clone this
repo and run `ingest/ingest_policy.sh` / `dbt build` from repo root (see `AGENTS.md` — *Command-catches*).

## Edge authentication (forward-auth)

**Problem:** Metabase OSS has no native OIDC, so it cannot join the Authentik SSO estate on its own.

**Pattern:** **gate at the ingress with Authentik forward-auth** (an embedded outpost, provider
`metabase`), leaving a local admin behind it. The in-cluster service stays **ungated** so the pipeline /
provisioner can reach it directly.

**Where:** the ingress config is deployment-side; the provisioner targets the in-cluster service
`http://metabase.data-platform.svc.cluster.local:3000` (see `AGENTS.md` — *Command-catches*).

## Least-privilege read replica role

**Problem:** reading a source system with a broad role widens the blast radius if the analytics side is
compromised.

**Pattern:** a **dedicated read-only `analytics_ro` role** on the source policy DB with SELECT on the three
source tables only — blast-radius containment. It can never write back to the operational store.

**Where:** the role is provisioned deployment-side; the ingest script connects with these read-only creds
(`POLICY_PG_*` env in `ingest/ingest_policy.sh`).

## Externalised secrets (Vault → ESO)

**Problem:** secrets in code or images leak and cannot be rotated.

**Pattern:** **no secrets in code** — runtime creds are injected. Vault `secret/platform/data-platform`
feeds ESO, which renders the k8s secrets (CNPG roles, policy read-only creds, Metabase creds).

**Where:** every connection param in `dbt/profiles.yml` and `ingest/ingest_policy.sh` reads from env
(ESO-injected); the provisioner (`metabase/provision_dashboard.py`) reads Vault at runtime via a token.

## Convention override via macro

**Problem:** dbt's default `generate_schema_name` concatenates the target schema with the custom schema,
producing `business_business` / `business_curated`.

**Pattern:** **override the macro** so custom schema names are used verbatim — marts land in `business`,
staging in `curated`. Safe because this is a single-target, single-owner analytics DB.

**Where:** `dbt/macros/generate_schema_name.sql`. Do not remove it, or the marts move to
`business_business`.

## Proxy metric with an explicit caveat

**Problem:** presenting a derived metric as authoritative when its underlying semantics are unconfirmed
misleads consumers.

**Pattern:** **document the proxy, and narrow it as facts are confirmed.** GWP (`annualised_premium_eur`)
is labelled a **proxy**. Its money units are now **confirmed** eurocents (DP-007, verified against the
`ktayl-policy-service` domain model), so ÷100 → EUR is authoritative. What remains open is the
**annualisation cadence**: the mart treats each premium row as a recurring schedule (`amount × cadence`);
if rows are individual installments it over-counts. The figure stays a proxy pending that one
row-cardinality decision by the Policy domain (tracked as DP-007) — a proxy shrinks toward authoritative
as each assumption is discharged, rather than staying a blanket disclaimer.

**Where:** the caveat is written into the model column description (`dbt/models/marts/_policy_portfolio.yml`),
the SQL comments (`dbt/models/marts/policy_portfolio.sql`, `dbt/models/staging/stg_premiums.sql`), and
`AGENTS.md` (*Observed pitfalls*).
