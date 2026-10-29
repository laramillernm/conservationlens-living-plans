# ConservationLens Living Plans

**Insights built for small conservation teams.**

ConservationLens Living Plans is an open-source prototype for keeping
place-based conservation plans current, transparent, and useful for
real management decisions.

The prototype is designed to test a planning framework rather than to
serve as a finished conservation-planning platform.

Its core logic is:

> **Threat → Connection → Consequence → Intervention**

The purpose of the prototype is to determine whether this decision chain
can provide a practical, repeatable structure for organizing existing
national, state, and local data into useful planning information.

The goal is not simply to map hazards.

ConservationLens asks:

1. **Where is the threat?**
2. **How is that threat connected to places or values we care about?**
3. **What could be affected, and how much would it matter?**
4. **Where would intervention be most beneficial, and why?**

---

# Prototype Status

This repository is an active **v0.1 prototype**.

It is being developed using the El Rito watershed in northern New Mexico
as the first test geography.

The prototype is intended to demonstrate:

- a reusable analytical structure
- source-independent workflows
- transparent rules
- configurable planning geography
- updateable datasets
- traceable findings
- integration of national and local information
- a logical path from environmental condition to management action

It is **not** intended at this stage to provide:

- a complete watershed plan
- a regulatory determination
- a final treatment prescription
- a complete debris-flow model
- a complete wildfire-risk model
- a universal prioritization score
- a replacement for local expert judgment

The prototype is testing the analytical framework first.

---

# Why ConservationLens?

Conservation organizations already have access to a large amount of
environmental data.

The problem is often not lack of data.

The problem is turning that data into information that is:

- relevant to local decisions
- easy to update
- transparent
- adaptable to different planning questions
- capable of incorporating local knowledge
- capable of accepting newer or corrected datasets
- connected to management action

Many conservation plans become static shortly after completion.

Many existing planning platforms contain valuable information but are
difficult for small organizations to customize when:

- conditions change
- new datasets become available
- local data conflict with national data
- projects are completed
- priorities change
- planning questions differ between communities

ConservationLens is designed around a different idea:

> **National data provide the baseline, not the ceiling.**

Authoritative national and statewide datasets establish a repeatable
starting point.

Newer local data, corrections, monitoring results, treatment data, and
project-specific information can supplement or supersede those sources
without requiring the entire analytical workflow to be rebuilt.

---

# The ConservationLens Decision Chain

The prototype is organized around four connected stages:

```text
THREAT
What could happen here?

        ↓

CONNECTION
How could that threat reach or affect something important?

        ↓

CONSEQUENCE
What would be affected, and how much would it matter?

        ↓

INTERVENTION
Where could action reduce the threat or consequence?