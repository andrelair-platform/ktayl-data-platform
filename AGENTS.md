# AGENTS.md — ktayl-data-platform

Tiny repo-context block (policy / command-catches / non-default conventions / observed pitfalls).
The code is the context; this holds only what the code can't cheaply say. See org rules in
`minicloud-gitops/.claude/rules/*` (deployment-vs-code, bmad, gitops, testing).

## Policy
- **This is a CODE repo.** Deployment config lives in `minicloud-gitops` (`manifests/data-platform/`,
  `apps/platform/data-platform.yaml`). Never put k8s manifests / Helm / ArgoCD here. (conventions.md
  *Deployment repo vs code repo*.)
- Two-layer model: this serves the **ktayl-solution IS**, not Retrieva, not a cert deliverable.
- Secrets: never commit any. Runtime creds come from Vault `secret/platform/data-platform` via ESO
  (deployment side) or `VAULT_TOKEN` (the provisioner). Scripts must be secret-free.

## Command-catches
- The ingest/dbt CronJobs (in gitops) **git-clone this repo** and run `ingest/ingest_policy.sh` /
  `dbt build` from repo root — so paths are repo-relative, not under a subdir.
- Metabase provisioner targets the **in-cluster service** when the ingress is SSO-gated:
  `MB_BASE=http://metabase.data-platform.svc.cluster.local:3000` (the ingress has Authentik forward-auth).
- dbt: `generate_schema_name` is overridden (macros/) so custom schemas are verbatim → marts land in
  `business`, staging in `curated` (NOT `business_business`).

## Observed pitfalls
- dbt schema concatenation (fixed via the macro above) — don't remove it or marts move to `business_business`.
- CNPG bootstrap volume can transiently fault on a node → cordon + recreate on a clean node (deployment side).
- Money columns are BIGINT **eurocents** (÷100 → EUR) — **CONFIRMED** (DP-007) against the source domain
  model (`ktayl-policy-service` `internal/domain/{premium,coverage}.go`: `int64 // eurocents`).
- GWP annualisation (DP-007, **resolved with a guarded contract**): the mart annualises `amount × cadence`
  under an **interim contract** — *one premium row per policy = the recurring schedule at its frequency* —
  which is **enforced by a `unique` test on `premiums.policy_id`**. Premium management is a *future* domain
  (`policy-service` `ports.go`: "future premium management stories"); if it later ships **per-installment**
  rows, that test **fails the dbt build** → switch the annualisation to `sum(amount)` before serving. So
  GWP is authoritative *under a tested assumption with a loud tripwire*, not an open-ended proxy. Issue #7.

## Doctrine
Thin vertical slice: one live source → just-enough medallion → one data product. Do NOT build a generic
connector framework or heavy OLAP (ClickHouse/Kafka) for sources that don't exist yet (need-first gate).
