# Contributing

This is the **code** repo for the ktayl Data Platform. Deployment config (k8s manifests, ArgoCD,
CronJobs) lives in `minicloud-gitops` (`manifests/data-platform/`) — never add k8s/Helm here.
See the org rule *Deployment repo vs code repo* (`minicloud-gitops/.claude/rules/conventions.md`).

## Branch conventions (trunk-based)

| Branch | Rules |
|---|---|
| `main` | The only deploy branch. PR required; GPG-signed commits (key `FD6D39D681DEFA34`). The ingest/dbt CronJobs git-clone `main`. |
| feature branches (`feat/`, `fix/`, `docs/`, `chore/`) | Short-lived → PR → `main`; auto-deleted on merge. |

> Environments ≠ branches: the platform runs `dev` + `prod` medallion schemas, both fed from `main`.

## Commit style

Conventional commits: `type(scope): message` — `feat`, `fix`, `docs`, `chore`, `ci`, `refactor`, `test`.
`feat:` → minor bump, `fix:` → patch, `feat!:` → major (release-please cuts releases from these).

Examples:
```
feat(dbt): add loss-ratio column to policy_portfolio
fix(ingest): make COPY atomic per table
docs: document GWP proxy assumptions
```

## PR requirements

- All CI checks must pass before merge (yamllint, ruff, shellcheck, dbt parse).
- `main` PRs require GPG-signed commits.
- No `Co-Authored-By` lines — commits represent the portfolio owner's work.

## Running checks locally

```bash
# dbt (needs the analytics Postgres for build; parse is offline)
cd dbt && dbt deps && dbt parse            # validate project structure (no DB)
dbt build                                   # full run + tests (needs ANALYTICS_PG_* env)

# lint
ruff check metabase/                        # Python provisioner
shellcheck ingest/ingest_policy.sh          # ingest script
yamllint dbt/                               # dbt yml
```
