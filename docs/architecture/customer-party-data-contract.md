# Customer / Party data contract (the target for real MDM)

> **What this is.** The *pre-agreed* definition of what a future Customer/Party source domain must deliver
> so that **real customer-matching (MDM)** can be built — **without** fabricating anything today. This is
> the cheap pre-work named in
> [ADR-014](adr/ADR-014-customer-party-mdm-golden-record-trigger.md) ("agree the party contract early").
> Status: **blocked** on a source domain existing; tracked as issue #45. Nothing here is built yet — it's
> the spec that makes building it fast and safe when the data arrives.

## Why write this now

Today the platform has only a **name field** and ~tens of policies, so it cannot tell that the *same*
customer appearing in **policy**, **underwriting** and **claims** is one person (names are spelled
differently in each). Real matching needs real information to compare. By agreeing **up front** exactly
what a Customer/Party system must provide, we avoid a large rework when it ships — the data lands already
shaped for matching.

## The Party (what one row represents)

A **Party** is one real-world **person or organisation**. Grain = **one real party** (not one contract,
not one claim). A party is referenced by every domain, under a single permanent id: **`party_id`**.

## What lets us match (the identifiers the source MUST provide)

Matching is only as good as the identifiers available. The contract requires, at minimum:

| Party type | Strong identifiers (exact match) | Supporting attributes (fuzzy match + survivorship) |
|---|---|---|
| **Person** | national-id *(where lawful)*, email, date of birth | full name, postal address, phone |
| **Organisation** | **SIREN / SIRET**, VAT number | legal name, trading name, registered address |

Plus the **links that already exist** and must be preserved end-to-end:
- `underwriting.binding.policy_number` ↔ `policy.policies.policy_number` (a real, exact link today).
- the future `claims.claim.policy_number` ↔ the same policy (so a claimant resolves to the policy's party).

> Without at least one **strong identifier** per party, matching cannot be tuned to a safe accuracy
> (a wrong merge can expose one customer's data to another). A name alone is **not** sufficient — that is
> precisely why today's `md5(holder_name)` is only a placeholder.

## The party-role model (the insurance twist)

One party plays **many roles**, often across different domains. The contract models **roles separately**
from the party, so the same `party_id` can be all of these at once:

| Role | Appears in | Example |
|---|---|---|
| Policyholder | policy | holds contract P-001 |
| Insured | policy / underwriting | the risk being covered |
| Claimant | claims | files a loss under P-001 |
| Beneficiary | policy | receives a payout |
| Broker / intermediary | distribution | sold the policy |
| Payer | billing | pays the premium |

## What each existing domain must expose to link

| Domain | Must expose | So we can link… |
|---|---|---|
| **policy** | the policy's party identifiers (not just `holder_name`) + `policy_number` | holder → party |
| **underwriting** | `binding.policy_number` (already does) + the quoted party's identifiers | quote/premium → the policy's party |
| **claims** (future) | `claim.policy_number` + the claimant's identifiers | claimant → party (same or different from holder) |

## The target output (what MDM will produce)

1. **Party master** — one golden row per `party_id` (best value per attribute, chosen by rule).
2. **Party-role table** — `party_id` × role × domain reference.
3. **Crosswalk (`party_xref`)** — every source record's key → its `party_id`, with how-matched + confidence
   + valid-from. This is the bridge that lets the existing marts swap `md5(holder_name)` for `party_id`
   as a **dimension change, not a mart rewrite**.

## How it will be matched (summary — detail at build time)

- **Exact rules first** on the strong identifiers + the `policy_number` crosswalk (high confidence).
- **Fuzzy matching** (name/address/DOB similarity) only as a fallback where strong ids are missing —
  runs inside DuckDB (open-source tooling), so no new runtime.
- **A human reviews the uncertain cases** — the system auto-decides the clear ones and queues the rest,
  biased toward *keeping two records apart* when unsure (a wrong split is recoverable; a wrong merge is a
  data breach).

## Status & trigger

**Not built — data-blocked.** Build when a Customer/Party source domain ships (`ktayl-distribution`/CRM,
board #13) or a regulatory single-customer-view need appears. Trigger-watch: **issue #45**. Until then,
`dim_customer` stays the labelled interim key ([ADR-014](adr/ADR-014-customer-party-mdm-golden-record-trigger.md)).
