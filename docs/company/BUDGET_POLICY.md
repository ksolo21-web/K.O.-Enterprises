# Budget Policy

## Purpose

Budgets convert strategy into hard operating limits. A budget is permission to reserve a defined resource for an approved purpose; it is not permission to perform an otherwise gated action.

## Hierarchy

```text
CEO-approved corporate envelope
  -> President portfolio allocation
    -> department allocation
      -> product or experiment allocation
        -> task reservation
```

Every child allocation must fit inside the parent's scope, period, resource type, currency/unit, and unallocated balance. Agents cannot create or raise the parent cash envelope.

## Resource classes

Track at least:

- external cash by currency;
- model/API tokens or estimated usage cost;
- GitHub/compute minutes;
- storage and network usage;
- human/CEO review minutes;
- outreach, publication, refund, or connector action counts when authorized.

A free tier, subscription allowance, credit, or public-repository allowance still consumes an operational resource and may have terms or limits. Do not describe it as unlimited without current authoritative evidence.

## Budget states

`proposed -> active -> exhausted | expired | suspended | closed`

Task usage follows `reserved -> committed -> settled` or `released`. Availability is the ceiling less child allocations, active reservations, committed usage, and settled usage as appropriate. Reservations and idempotency must be atomic.

## Authority

- Kaleb creates or raises a corporate external-cash envelope.
- The President allocates approved internal capacity across the portfolio within the mandate.
- Department leads allocate their remaining department capacity to accepted objectives.
- Task leads reserve, release, and reconcile only the resource named by their delegation.
- Finance Control independently blocks missing, stale, mismatched, duplicated, or insufficient budget.

No actor may relabel a resource, currency, period, or account to evade a ceiling. Forecast revenue is never available cash.

## Fail-closed conditions

Deny reservation or execution when the parent budget is missing, inactive, expired, suspended, mismatched, insufficient, unverifiable, or concurrently exhausted. A budget overrun stops the affected work and creates a variance/escalation record; it does not silently borrow from another budget.

## Reconciliation

Reconcile reservations after every attempted external action, including uncertain outcomes. Store source references and distinguish estimates, commitments, incurred costs, paid costs, realized revenue, and cleared cash. Unknown external state remains unknown until verified.

## CEO attention

The President should request a changed corporate cash ceiling only when current evidence and unit economics justify it. The packet states amount, currency, period, use, stop condition, downside, and the no-spend alternative. Ordinary resource reallocation inside an existing mandate does not return to the CEO.
