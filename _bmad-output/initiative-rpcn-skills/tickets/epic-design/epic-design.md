---
tracker_id: ""
type: epic
title: "Design skill"
parent: initiative-rpcn-skills
covers: [R1, R15]
sources: []
companions: []
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
