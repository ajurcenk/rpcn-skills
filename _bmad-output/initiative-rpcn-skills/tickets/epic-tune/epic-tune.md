---
tracker_id: ""
type: epic
title: "Tune skill"
parent: initiative-rpcn-skills
covers: [R4]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md]
after: []
refined: false
risk: medium
---

# Tune skill

## Description

Delivers `rpcn-tune`, which reads RPCN logs and metrics and recommends throughput, batching and backpressure changes, each naming the metric behind it.

## Outcome

Developers improve running pipelines from evidence, not guesswork (initiative R4).

## Done when

- On a reference pipeline with a known bottleneck, the recommended changes measurably raise throughput or cut latency, and each names its metric.
- Its skills meet R9 (size and references), R12 (triggering evals), R16 (hand-off files), R17 (headless status) and R19 (what next), using epic 1's conventions.

## Boundaries

- In: `rpcn-tune`, the tuning report and a YAML diff.
- Out: capacity sizing (epic 5).

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md`: AD-6; Deferred: load-test environment
