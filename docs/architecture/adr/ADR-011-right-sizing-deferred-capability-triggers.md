# ADR-011 — Right-sizing: the deferred-capability trigger register

- **Status:** Accepted (2026-11-19). The standing register of what the data platform **deliberately
  defers**, why, and the **exact trigger** to build each. Complements ADR-006..010 (which chose the tools);
  this one records what we chose **not** to turn on yet, so a deferral reads as *intent*, not a gap.
- **Date:** 2026-11-19
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS · **Board:** Data Platform (#5)
- **Decider:** owner (architecture call) · **Reviewer refinements** incorporated (see each trigger).

## Context

The data platform is **production-adopted but deliberately right-sized** (ADR-009/010): single-pod Cube,
webserver-only Dagster with in-process runs, full-refresh ingestion. At the current scale (~tens of rows,
~11 policies, **one** BI consumer) the HA/scale machinery — Cube Store, the Dagster daemon + K8sRunLauncher
+ replicas, WAL-based CDC — would be **pure operational tax**. The one upgrade that *did* earn its place now
is **persistent run history on CNPG** (so history survives restarts) — that's built. Everything else is a
documented deferral with a concrete trigger below.

**Two categories — do not conflate them:**
- **Tooling-deferred** (1–3) — *we* control these; build the day the trigger fires. Right-sizing.
- **Data-blocked** (4) — blocked on **another domain producing data**; no tooling we add unblocks it.
  Building it now would mean fabricating numbers — the exact anti-pattern ADR-007 forbids.

## The register

### 1. Cube Store (Cube HA + pre-aggregations) — *tooling-deferred*
- **What:** Cube's columnar engine for **pre-aggregations** (materialised rollups) + what enables **multi-
  replica** Cube. Today: single-pod, `CUBEJS_CACHE_AND_QUEUE_DRIVER=memory`, queries pass through to CNPG.
- **Give up:** no pre-aggs (every query re-hits Postgres), no horizontal scale, single point of failure.
- **Trigger (refined):** **NOT row-count alone.** The real near-term triggers are **(a) multi-consumer
  load** (≳10 concurrent BI/app consumers) or **(b) heavy SQL expressions** (complex cohort/window/nested
  measures) — a *small* table can still be slow under those. **Watch query latency + concurrency**, not just
  "millions of rows." → then: deploy Cube Store (router+worker), flip the driver, scale Cube ≥2 replicas.

### 2. Dagster daemon · K8sRunLauncher · multi-replica — *tooling-deferred, THREE separate triggers*
**Do not bundle these** — each has its own trigger (this is the key refinement):
- **daemon** — runs **schedules, sensors, auto-materialization**. Cheap: a **lightweight daemon running a
  nightly schedule/sensor in-process** adds ~one small process, no per-run pods. **Trigger:** you want the
  graph to run **itself** (a nightly refresh/retrain, or a sensor on new source data). *This is the
  designated next move* — the cheapest, highest-leverage upgrade.
- **K8sRunLauncher** — one **ephemeral pod per run** (isolation, per-run limits, real parallelism).
  **Trigger (refined):** **only** once runs are **heavy, parallel, or risk UI contention** — not bundled
  with the daemon. In-process runs are fine until then.
- **multi-replica (HA webserver)** — **Trigger:** the orchestrator becomes operationally critical. Note:
  run history already survives restarts (CNPG storage, built) — so this is about UI uptime only.

### 3. CDC ingestion (Debezium → NATS) — *tooling-deferred*
- **What:** replace **full-refresh** dlt with **change-data-capture** — Debezium tails the source Postgres
  **WAL** → NATS JetStream → incremental land. Pattern **already proven on-platform** (`ktayl-claims`).
- **Give up (today, full-refresh):** freshness (batch, not near-real-time) + cost/slowness as tables grow.
- **Trigger:** source tables large enough that full-refresh is too slow/costly, **or** a near-real-time need.
- **Build-time discipline (refined — mandatory when adopted):** handle **deletes**, **late-arriving
  updates**, and **schema drift** (e.g. Phase-1b adding premium/coverage columns) **cleanly in dbt** so the
  incremental merge never silently diverges from source. (Full-refresh hides all three; CDC exposes them.)

### 4. Cross-domain KPIs — GWP · loss ratio · combined ratio — *DATA-BLOCKED (not tooling)*
- **Why blocked:** `ktayl-core` policy module shipped **Phase 1 only** (the policy *registry* —
  `policy.policy`; no premiums/coverages) and **claims** aren't in the warehouse. GWP needs premium;
  combined ratio = (incurred claims + expenses) ÷ earned premium, net of ceded reinsurance — **four domains
  joined**. No tooling unblocks this; only the data does. Tracked: **issue #28**.
- **Action now (refined — do EARLY, before Phase-1b ships):** agree the **data contract** with the
  ktayl-core Phase-1b team **up front** — exact **grain**, **currency** (minor units), **effective vs
  written dates**, and **reinsurance/expense definitions**. Settling these before the data lands avoids a
  large rework when it does. This is cheap to do now and is the one productive move while blocked.

## Consequences

- **Positive:** every deferral is an **accepted, triggered decision** (auditable intent, not an oversight);
  the platform stays cheap to run; the next steps are unambiguous and ranked (daemon first).
- **Review discipline:** when a trigger’s signal appears (latency/concurrency climbing, a schedule needed,
  tables growing, Phase-1b scoping starting), re-open the relevant ADR and build **just** that item.
- **Designated next move:** **Dagster daemon + a nightly schedule/sensor** (in-process) — turns manual
  "click-materialize" into hands-off automation with minimal infra, ahead of Phase-1b.

## Related
ADR-007 (don't build KPIs on stub data — the #4 principle) · ADR-008 (lake/CDC) · ADR-009 (Cube) ·
ADR-010 (dlt + Dagster) · issue #28 (Phase-1b data dependency) · `cloud-adoption.md` (need-first gate).
