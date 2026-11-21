# ADR-014 — Customer/Party MDM: interim pseudonymous key now, golden record when a Party domain ships

- **Status:** Accepted (2026-11-21). Records that `dim_customer` is a deliberate **interim pseudonymous
  join key** (`md5(normalised holder_name)`), **not** a master-data golden record — and that real
  Customer/Party MDM is **data-blocked** (needs a source Party domain), not tooling-deferred. A *data-
  blocked* entry in the sense of ADR-011 #4.
- **Date:** 2026-11-21
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS · **Board:** Data Platform (#5)
- **Decider:** owner (architecture call).

## Context

**Master data management (MDM)** produces a **golden record** — the single authoritative version of a core
entity (Customer/**Party**, Policy, Product) reconciled across *all* source systems by **match → merge →
survivorship**, maintained by **stewardship**. Insurance is the canonical MDM domain: one **party** is at
once policyholder, claimant, broker, beneficiary — across policy, underwriting, claims, distribution.

**What we have:** `dim_customer.customer_sk = md5(lower(trim(holder_name)))`. This is an honest **interim
pseudonymous join surrogate on an exact-normalised name string** (the raw name is never served — PII-safe).
It is explicitly **not** a golden record, and it fails as one the moment data is messy:

- **Typos / variants** — "Jean Dupont" vs "J. Dupont" vs "Dupont Jean" → *different* customers.
- **Legal-form noise** — "ACME SARL" vs "ACME S.A.R.L." vs "SARL ACME" → distinct keys for one company.
- **No cross-system resolution** — the same party in `policy` and `underwriting` only collides if the name
  strings are byte-identical; across claims/distribution it cannot.
- **No survivorship, no steward, no xref** — no "which source wins," no human merge/split, no
  cross-reference table mapping source keys → one golden ID, no history.

**Why we cannot build real MDM now (the key point): it is DATA-blocked, not tooling-deferred.** Real entity
resolution needs **an authoritative Customer/Party source domain producing structured party records** —
and today **none exists** (the CAP-001 gap). Building probabilistic matching on ~11 policies with a single
free-text name field would be **fabricating a capability** — the exact anti-pattern ADR-007 forbids. No
tool we install unblocks this; only the *data* does.

## Decision

**Keep `dim_customer` as the interim pseudonymous key**, clearly labelled (it already is, in `_mdm.yml`),
and **do not** stand up entity-resolution tooling until a real Party domain ships. When unblocked, build
MDM as: a **golden `party_id` + an xref/crosswalk** (source-key → golden-ID, with match confidence +
history) + **deterministic *and* probabilistic matching** (open-source **Splink** or **Zingg**) +
**survivorship rules** + a **stewardship** merge/split workflow. (A metadata catalog — ADR-013 — is **not**
MDM: catalogs *describe* data; MDM *masters* it.)

## Triggers (build real MDM when ANY fires) — *data-blocked*

1. **A Customer/Party source domain ships (the unblock)** — `ktayl-distribution` (#13, CRM scope) or a
   dedicated Party master starts producing structured party records (name, type, SIREN/VAT, addresses).
2. **Cross-domain accuracy becomes load-bearing** — a KPI needs *customer-level* rollup across
   policy+claims (customer lifetime value, accumulation/concentration by insured, client-attributed
   combined ratio) where name-collision errors would corrupt the number.
3. **A regulatory single-customer-view need** — KYC/AML, sanctions screening, or a GDPR DSAR ("give this
   person all their data") — all require one authoritative customer identity.

None are firing today → **no MDM tooling now**, by design.

## Action while blocked (cheap pre-work — the ADR-011 #4 "agree the contract early" move)

- **Scaffold the xref pattern now** — model `customer_sk` as a replaceable *interim* key and keep marts
  referencing it indirectly, so swapping in a real `party_id` later is a **dimension change, not a mart
  rewrite**.
- **Agree the party data contract up front** with whoever builds the Customer/CRM domain — the **grain**
  of "party," the **identifier set** (SIREN/VAT/national-id), and the **party-role model** (policyholder
  vs claimant vs broker vs beneficiary). Settling these before the data lands avoids a large rework.
  **Done:** the target spec is written — [`../customer-party-data-contract.md`](../customer-party-data-contract.md)
  (the party grain, required identifiers, role model, per-domain link requirements, and the target
  golden-record/crosswalk output a source domain must satisfy).

## Consequences

- **Positive:** the interim key is an **accepted, documented** decision (not a hidden weakness); the star
  schema joins today; the upgrade path is unambiguous and the cheap pre-work de-risks it.
- **Negative / watch:** until unblocked, any **customer-level** aggregate across domains is **unreliable by
  construction** (name-collision) — so **do not publish a customer-level KPI** on `customer_sk` without
  adopting real MDM first. Reviewers: a PR introducing a per-customer cross-domain metric is the gate.

## Related

ADR-007 (don't build on stub data — #4 data-blocked principle) · ADR-011 #4 (cross-domain KPIs are
data-blocked) · ADR-013 (catalog — describes entities; distinct from mastering them) · `dbt/models/marts/
mdm/README.md` (the interim-dim rationale) · CAP-001 (no Customer master) · board #13 (Distribution/CRM).
