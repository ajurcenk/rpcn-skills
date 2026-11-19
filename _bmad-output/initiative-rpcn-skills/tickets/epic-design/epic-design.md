---
tracker_id: ""
type: epic
title: "Design skill"
parent: initiative-rpcn-skills
covers: [R1, R15]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md]
after: []
refined: false
risk: medium
---

# Design skill

## Description

Delivers `rpcn-design`, which writes a design note applying RPCN best practices (error handling, DLQ, retries, batching, idempotency, ordering). Author builds from it, and Test checks the result against it.

## Outcome

A developer new to RPCN goes from a described pipeline to a linted, tested one in under 10 minutes, with best practices designed in (initiative R1, R15).

## Done when

- For each eval case, the note names every relevant best-practice pattern, and the pipeline Author builds from it contains those patterns and lints clean.
- A newcomer with the binary installed reaches a linted, tested pipeline in under 10 minutes, measured on the eval path.
- Its skills meet R9 (size and references), R12 (triggering evals), R16 (hand-off files), R17 (headless status) and R19 (what next), using epic 1's conventions.

## Boundaries

- In: `rpcn-design` and the design note content.
- Out: YAML generation (Author, epic 2) and the note's file format (epic 1).

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md`: AD-6, AD-7, AD-9

## Notes

- Open question: How does `rpcn-design` ask the user for what only they can decide? These are choices the binary can't settle: delivery (at least once, or exactly once with a dedupe key), ordering, where a failed message goes (retry, DLQ or drop), volume and latency, and sink idempotency. To settle when this epic is refined; its stories wait on the answer. Proposed starting point (2026-11-18, user asked for it to be recorded here):
  - Design runs a short guided interview, in a few rounds, and each question comes with the answer it would pick.
  - A choice left unanswered is written to the note's Open decisions as `[blocking]`. The note is then not `ready`, and Author and Test won't build from it (`tools/shared/formats/design-format.md`, Open decisions and readiness).
  - Headless, it never asks. It writes a draft note that lists the open decisions.
  - Every choice the note settles is one Author never asks about (story 2.17's rule).
  - It must still meet R15 (a newcomer reaches a linted, tested pipeline in under 10 minutes), so a simple flow gets sensible defaults, not a long interview.

  Still to decide: how many rounds, which decisions Design must always ask, and when one may stay `[blocking]`.
