# ADR-012 — Lakehouse table format: plain Parquet now, Apache Iceberg on trigger

- **Status:** Accepted (2026-11-21). Records the deliberate choice to run the raw lake on **plain
  versioned Parquet** today and to adopt an **open table format (Apache Iceberg)** only when a concrete
  trigger fires — so the gap between our "lakehouse *pattern*" and a *transactional* lakehouse reads as
  **intent, not omission**. Extends the ADR-011 deferred-capability register with one more entry.
- **Date:** 2026-11-21
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS · **Board:** Data Platform (#5)
- **Decider:** owner (architecture call).

## Context

ADR-008 chose the **hybrid S3 lake → DuckDB transform → CNPG serving** shape and calls it a *lakehouse*.
That is accurate as a **capability composition** (lake storage economics + warehouse-grade governed marts),
but it is honest to name what it is **not**: the raw lake is **plain Parquet** (Hive-style
`layer/domain/table/dt=YYYY-MM-DD/*.parquet`, S3 object-versioning + SSE), with **no open table format**
layered over it.

The industry definition of a *data lakehouse* (and the IBM reference) hinges on an **open table format** —
**Apache Iceberg**, Delta Lake, or Hudi — that adds, *on top of* the Parquet files:

- **ACID transactions** (atomic multi-file commits; no partial-write readers),
- **time travel / snapshots** (query/rollback to a prior version),
- **safe schema evolution** (add/rename/drop columns without rewriting or breaking readers),
- **hidden partitioning + partition evolution** (change partition scheme without rewriting data),
- **concurrent writers** (optimistic-concurrency commit protocol).

**What plain Parquet gives up today (the accepted risk):** none of the above. Our writes are
**full-refresh, single-writer, nightly** (`dp-lake-land-policy` → one Parquet object per `dt=` partition),
read by a **single** DuckDB job (`dp-lake-transform-policy`). At this scale (~tens of rows, one writer, one
reader, batch cadence) the Parquet-only lake is **correct and sufficient** — the table-format machinery
(a catalog, a commit protocol, snapshot expiry/compaction maintenance) would be **pure operational tax**
with no workload that exercises it. This is the same need-first gate as ADR-011.

## Decision

**Keep the raw lake on plain versioned Parquet now.** Adopt **Apache Iceberg** as the lake table format
when a trigger below fires — and prefer **Iceberg over Delta/Hudi** for this stack, because:

- **DuckDB** (our OLAP engine) has a first-class Iceberg reader (`iceberg` extension) — the engine we
  already run gains transactional reads with no engine swap.
- **AWS S3** (our lake) has native Iceberg support (S3 Tables / Glue Data Catalog) — a managed catalog
  path with no new standing service to operate.
- Iceberg is the **de-facto open standard** now cross-supported by DuckDB, Snowflake, Databricks, Trino,
  Spark — it does not lock the lake to one engine (Delta is strongest inside the Databricks/Spark world,
  which we do not run).

## Triggers (adopt Iceberg when ANY fires)

1. **Concurrent / incremental writers** — the moment ingestion moves off single-writer full-refresh:
   **CDC** (the ADR-011 #3 Debezium→NATS trigger) or a second pipeline writing the same table. CDC's
   merge/append needs atomic commits + delete handling — exactly Iceberg's job; doing CDC on plain Parquet
   invites partial-read and lost-update bugs. **This is the most likely first trigger** and couples to the
   ADR-011 CDC decision.
2. **Time-travel / audit need** — a regulatory or reconciliation requirement to query or prove the lake's
   state *as-of* a past date (insurer audit, GDPR lineage, "what did the portfolio look like on
   31-Dec"). S3 object-versioning is file-level, not a queryable table snapshot — Iceberg snapshots are.
3. **Schema evolution pain** — when source schemas start changing under us (e.g. `ktayl-core` Phase-1b
   adding premium/coverage columns, issue #28) and full-rewrite-on-change becomes too costly or risks
   breaking readers mid-flight. Iceberg's safe column add/rename/drop removes the rewrite.
4. **Scale-out query engine** — if DuckDB-single-node is outgrown and **Trino/Spark** is introduced for
   distributed SQL over the lake, Iceberg becomes the shared table contract those engines read/write
   consistently (plain Parquet directories do not give multi-engine write safety).

None of these are firing today → **no action now**, by design.

## Build-time discipline (mandatory when adopted)

- **Catalog choice first** — AWS Glue / S3 Tables (managed, no ops) vs a self-hosted REST catalog
  (Nessie/Polaris). Prefer the managed AWS catalog to avoid a new standing service (consistent with
  keyless Vault-STS access — ADR-008).
- **Maintenance is not optional** — schedule **snapshot expiry + compaction** (small-file problem) from
  day one; an unmaintained Iceberg table degrades. Wire it into the Dagster graph (ADR-010/011 #2).
- **Migrate raw first, not the marts** — the marts stay dbt-materialised in CNPG; Iceberg replaces the
  **raw/landing** Parquet substrate (and any silver lake tables), where the writer/reader/snapshot
  semantics actually matter.
- **DuckDB reader parity** — validate the `iceberg` extension reads our partitions at parity before
  cutting the transform job over; keep the Parquet path until parity is proven (same safe-direction
  discipline as the ADR-008 cutover).

## Consequences

- **Positive:** the plain-Parquet choice is now an **accepted, triggered decision** (auditable intent),
  the lake stays cheap and simple to run, and the upgrade path to a *true* transactional lakehouse is
  unambiguous and ranked (CDC co-triggers it). Closes the single biggest honest gap between our stated
  "lakehouse" and the reference definition — as a documented decision, not a silent omission.
- **Negative / watch:** until a trigger fires we genuinely lack ACID / time-travel / safe schema-evolution
  on the lake — so **do not add a second lake writer or CDC without adopting Iceberg in the same change**
  (trigger #1). Reviewers: if a PR introduces concurrent/incremental lake writes, this ADR is the gate.

## Related

ADR-006 (governed-lakehouse roadmap — P6 "object-table lakehouse") · ADR-008 (the hybrid lake/DuckDB/CNPG
shape this refines) · ADR-011 #3 (CDC — the co-trigger) · ADR-011 #2 (Dagster daemon — where compaction
scheduling lands) · issue #28 (Phase-1b schema evolution) · `cloud-adoption.md` (need-first gate).
