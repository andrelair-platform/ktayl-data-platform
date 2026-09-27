---
slug: /
title: Overview
sidebar_position: 1
---

# ktayl Data Platform

The **analytical data platform** for the ktayl-solution insurance IS (portfolio board **#5**). It turns
operational domain data into portfolio / pricing / exposure analytics through a **dbt medallion**
(`raw → curated → business`), a **full-refresh ingest** of the live policy source, and **Metabase** as
the BI serve layer.

> **Two-layer model.** This is part of the **ktayl-solution IS** (the simulated insurer) — it is *not*
> Retrieva and *not* a certification deliverable.

## What it is

- **Ingest** — a CronJob copies the live `ktayl-policy-service` prod Postgres into the analytics `raw`
  schema (full-refresh `COPY`; CDC is a later slice).
- **Transform** — dbt builds `curated` staging views then the `business` marts, running schema tests on
  every build so bad data never reaches the serve layer.
- **Serve** — Metabase reads the `business` schema and renders the dashboards; the ingress is gated by
  Authentik forward-auth.

## Light-first stack

| Layer | Tool | Note |
|---|---|---|
| Storage (medallion) | **Postgres** (CNPG `dp-postgres`, db `analytics`) — schemas `raw` / `curated` / `business` | own DB, no shared operational DB (ADR-005) |
| Ingestion | **CronJob** (`ingest/ingest_policy.sh`, `pg` COPY) | full-refresh; CDC (Debezium to NATS) is Slice 2 |
| Transform | **dbt-postgres** (`dbt/`) — staging to marts + schema tests | run via CronJob after ingest |
| BI / serve | **Metabase** | Authentik forward-auth; reads `business` schema |

ClickHouse / Trino / Kafka are deliberately **deferred** behind a need-first gate — building a heavy OLAP
for domains that do not exist yet is waste.

## Thin-vertical-slice doctrine

The platform grows **one live source at a time**: one real source produces a just-enough medallion which
produces one data product. It is deliberately *not* a generic connector framework or an OLAP cluster built
ahead of demand. Each new slice adds one real data product from one real live source, with tests green.

## Slice 1 — `policy_portfolio`

The first slice takes the live policy source to a single data product at policy grain, seeding the two
hardest industry problems:

- **GWP proxy** (`annualised_premium_eur`) — seeds P2 (margin / portfolio steering).
- **TIV** (`total_insured_amount_eur`) — seeds P1/P3 (exposure / accumulation).
- plus scheduled / paid premium, coverage counts, and dimensions (product code, status, inception year).

See [Data Model](./data-model.md) for the full grain and columns, and [Architecture](./architecture.md)
for the end-to-end flow.

## Deployment vs code

This is a **code repo** — dbt project, ingest script, and the Metabase provisioner. The Kubernetes
deployment (namespace + quota, CNPG cluster, ESO secrets, netpols, the ingest / dbt CronJobs, Metabase,
and the ArgoCD app) lives in **`minicloud-gitops`** under `manifests/data-platform/`. The CronJobs
**git-clone this repo** and run its code at runtime — app source here, deployment config there.

## Links

- Repository: [github.com/andrelair-platform/ktayl-data-platform](https://github.com/andrelair-platform/ktayl-data-platform)
- Deploy location: `minicloud-gitops` → `manifests/data-platform/`
- Org platform docs: [andrelair-platform.github.io/minicloud-platform-docs](https://andrelair-platform.github.io/minicloud-platform-docs/)
