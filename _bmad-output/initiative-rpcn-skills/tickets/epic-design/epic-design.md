---
tracker_id: ""
type: epic
title: "Design skill"
parent: initiative-rpcn-skills
covers: [R1, R15]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md]
after: []
refined: true
risk: medium
---

# Design skill

## Description

Delivers `rpcn-design`, which writes a design note applying RPCN best practices (error handling, DLQ, retries, batching, idempotency, ordering). Author builds from it, and Test checks the result against it.

## Outcome

A developer new to RPCN goes from a described pipeline to a linted, tested one in under 10 minutes, with best practices designed in (initiative R1, R15).

## Requirements

- R1 (parent R1; AD-7): `rpcn-design` writes `<name>.design.md` in the `design@1` format from a plain request, and names each relevant pattern: error handling and DLQ, retries, batching, idempotency, ordering. It is met when every eval case's note names each pattern relevant to it.
- R2 (parent R1; AD-4, AD-7): every component in the note is one that `rpcn_check list` and `fields` report. It is met when every eval note's components pass that check on 4.100.0 and the newest pin.
- R3 (parent R1; AD-15): each pattern recommendation names the behaviour fact it rests on, and that fact has a SOURCES.md row proved on both binaries. Patterns are distilled from the docs and from the reference skill sets, each adapted piece with its own row. It is met when every pattern in Design's patterns reference cites a row.
- R4 (parent R16; AD-7): an interactive run asks at most two short rounds of questions, each with the answer it would pick. It always asks the failure target, the delivery guarantee, ordering and the idempotency key, and gives every other choice a sensible default. An unanswered choice is `[blocking]` only when it changes components (the failure target or the delivery guarantee); otherwise it is `[non-blocking]`, with the pick written in. It is met by a scenario for each of these cases.
- R5 (parent R17; AD-8): a headless run never asks. It writes a `draft` note that lists its open decisions, and ends with the status block. It is met by a headless scenario.
- R6 (parent R16; AD-7): a Design re-run over an existing note keeps every Deviations row, and marks the rows it absorbed `resolved`. It is met by a scenario on a note with rows.
- R7 (parent R1, R16): Author builds Design's ready note into a pipeline that has the note's patterns and lints clean, and Test's Design check reports no `mismatch`. It is met by a chained scenario.
- R8 (parent R15): from a plain request, Design, then Author, then Test, run headless, reach a passing test report within 10 minutes of wall time on both binaries. It is met by one end-to-end eval scenario.
- R9 (parent R9, R12, R17, R19): `rpcn-design` meets epic 1's conventions, and the rpcn-author and rpcn-test descriptions name it where their triggers collide. It is met when the validator shows no warnings for all three skills and the trigger gate passes with negatives silent.
- R10 (parent R20): one comparison scenario for Design runs in the four arms at the epic's end. It is met when the eval record names its winner. A loss is recorded and accepted unless the user asks for a story.

## Constraints

- The installed binary is the source of truth. The tested binaries are 4.100.0 and the newest release. The pin roll from 4.115.0 to 4.117.0 lands before this epic's first build (initiative Constraints).
- The `design@1` format belongs to epic 1. Any change goes through `tools/shared/formats/design-format.md` and `sync_shared`, and rpcn-author and rpcn-test keep reading the note (AD-2, AD-7).
- Every change under `skills/` needs a passing eval record (AD-14). Scenarios include a pipeline outside the project root with a non-default name (decision 2026-11-05).

## Done when

- For each eval case, the note names every relevant best-practice pattern, and the pipeline Author builds from it contains those patterns and lints clean.
- A newcomer with the binary installed reaches a linted, tested pipeline in under 10 minutes, measured on the eval path.
- Every pattern Design recommends cites a sourced fact (R3), and the Design comparison names a winner (R10).
- Its skills meet R9 (size and references), R12 (triggering evals), R16 (hand-off files), R17 (headless status) and R19 (what next), using epic 1's conventions.

## Boundaries

- In: `rpcn-design` and the design note content.
- Out: YAML generation (Author, epic 2) and the note's file format (epic 1).

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md`: AD-6, AD-7, AD-9

## Notes

- Decision (2026-11-20, user): refined with the picks agreed:
  - **Asking:** R4 and R5. This settles the earlier open question on how `rpcn-design` asks.
  - **Patterns:** a patterns reference distilled from the docs and the reference skill sets (R3).
  - **The 10-minute goal:** one end-to-end eval scenario (R8).
  - **Benchmark:** one comparison at the epic's end (R10).
  - **Order:** the pin roll to 4.117.0 comes before the first build. Backlog story 6 (learning from the reference sets) comes after this epic.
