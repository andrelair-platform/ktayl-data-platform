# ADR-007 — The Data Platform depth + MDM is the gating foundation (sequencing decision)

- **Status:** Accepted (sequencing decision). Builds on ADR-006 (target governed lakehouse); does not supersede it.
- **Date:** 2026-11-08
- **Owner:** SA/TL (André) · **Layer:** ktayl-solution IS (organisational context — not Retrieva / not a cert deliverable)
- **Board:** Data Platform (#5)
- **Decider:** owner (architecture call)

## Context

Building the rest of the IS bottom-up made a sequencing truth undeniable: **almost every high-value
business capability is data-dependent, and none of it is real until the Data Platform has depth (a
conformed warehouse) and MDM (the join keys).** The top-down gap analysis predicted the same order
(`gap-analysis.md` §9 E + the P1/P2/P3 dependency fan-out); the bottom-up build confirmed it. This ADR
promotes that from an observation to an **explicit gating rule** so it is unmissable.

Where we are: **Slice 1 is LIVE but PARTIAL** — a medallion (`raw → curated → business`) in CNPG,
ingesting the **policy** and **underwriting** sources (`stg_policies/premiums/coverages/uw_quotes/
uw_bindings → marts/policy_portfolio`), with dbt quality tests (GWP reconciles, non-negative money, no
PII in serving) served through Metabase. What is missing is the **depth**: a conformed warehouse spanning
all the business domains, keyed by **MDM** master entities, with the governance spine of ADR-006.

The failure this prevents: **building data-dependent capabilities against stubs for zero real value** —
the same "don't build the automation before its foundation" lesson already learned with the parked
Copilot and MDM. A Combined Ratio with no earned-premium + incurred-claims + ceded-RI in one place is a
hard-coded number; a RoRAC with no capital data is theatre; an accumulation/PML with no geocoded,
MDM-keyed exposure is a guess.

## Decision

**The Data Platform depth (a conformed warehouse) + MDM (Customer/Entity, Broker, Policy, Location,
reference data) is the gating foundation of the IS. No data-dependent capability build starts before the
data + keys it needs exist in the warehouse.**

Concretely, the following are **gated** — not to be built (beyond a declared stub/spike) until their
warehouse inputs + MDM keys are live:

| Gated capability | Blocked until the warehouse holds… |
|---|---|
| Loss / Expense / **Combined Ratio** (`CAP-181/182/183`) | earned premium + incurred claims (incl. IBNR) + expenses + ceded reinsurance, joined |
| **RoRAC** (`CAP-684`) | portfolio profitability + allocated capital together |
| **Pricing Engine** (base/exposure/experience rating, `CAP-023/024` + #04) | historical loss experience + exposure, MDM-keyed |
| Claims-Experience (`CAP-463–468`) | a claims fact keyed on policy/customer |
| **Accumulation / PML / EP-curve** (`CAP-462/632/689`) | geocoded, MDM-keyed exposure aggregated across policies |
| Portfolio analytics (`CAP-208/209/502–508`) | conformed facts + dims |
| P1 Climate / P3 Systemic-accumulation differentiators | the hazard/climate data layer + the Retrieva graph over a mastered portfolio |

**MDM is the keystone inside the gate.** Without a Customer/Entity/Broker/Policy/Location master key you
cannot *join* across domains, so no cross-domain KPI is possible. (See also the cross-domain env-boundary
constraint: a cross-domain join only flows when both sources live in the **same environment** — Slice 2
needs its source domains co-located.)

**Litmus test for any new backlog item:** *does it read or aggregate data across more than one business
domain, or compute a ratio/metric/score?* If yes → it is gated behind the warehouse + MDM; schedule the
data slice first.

## Consequences

- **Positive:** no more building against stubs; one honest source of truth for every KPI; the governance/
  quality spine (ADR-006, EU AI Act Art. 10) is in place *before* AI/analytics consume the data; the
  build order is now unambiguous and auditable.
- **Accepted cost:** several visibly-valuable capabilities (Pricing, Combined Ratio, RoRAC, Accumulation)
  are deliberately **deferred** behind an unglamorous foundation. This is the right trade — they are
  worthless on stub data. State it so it reads as intent, not as a gap.
- **This is a sequencing ADR, not a licence to gold-plate** — the warehouse is built **thin and
  demand-pulled** (only the facts/dims a committed downstream capability needs), per ADR-002's
  thin-vertical-slice principle, not a big-bang enterprise DWH.

## Next step — Slice 2 scope (dependency-ordered)

Slice 2 = **warehouse depth + MDM keys**, built in this order (each step unblocks the next; do **not**
reorder):

1. **MDM keys + reference data (the keystone — do first).** Master entities: **Customer/Legal-Entity,
   Broker, Policy, Location/Site**; reference/code sets: **LOB, country, currency, industry**. Deliver a
   stable surrogate key per entity + a crosswalk from each source's natural key. (`CAP-200/201/202/218`.)
   *Nothing downstream can join without this.*
2. **Ingest the missing domain sources into the medallion.** Today only policy + underwriting land. Add
   **Claims** (the `ktayl-claims` read-model), **Billing/premium** (`ktayl-core`), **Finance/GL**
   (ERPNext). Co-locate them in the **same environment** so cross-domain joins flow. (`CAP-078–082`.)
3. **Conformed warehouse marts (fact/dim star, MDM-keyed).** `fact_premium` (written + earned),
   `fact_claim` (incurred + reserves), `fact_commission`, `fact_reinsurance_ceded`; `dim_customer/
   policy/broker/lob/period/location`. **This is the layer the gated KPIs read from.** (`CAP-204–209`.)
4. **Apply the governance/quality spine (ADR-006).** dbt tests + data contracts + lineage + PII masking
   on every new model — extend the Slice-1 pattern (GWP-reconciles / non-negative-money / no-PII-in-serving).
5. **Serving + semantic layer.** Metabase models/dashboards for Loss/Expense/**Combined Ratio** and
   portfolio analytics — the first *real* KPI, proving the chain end-to-end.

**Only after step 5** do the gated builds (Pricing, Combined Ratio, RoRAC, Accumulation) start — now
against real, conformed, mastered data.

## Related

- ADR-006 (target governed lakehouse — the *what*); this ADR is the *when/in-what-order*.
- `minicloud-platform-docs/data/gap-analysis.md` §9 E (foundations) + the sequencing rule.
- Capability register: the gated caps above; MDM `CAP-200`.
