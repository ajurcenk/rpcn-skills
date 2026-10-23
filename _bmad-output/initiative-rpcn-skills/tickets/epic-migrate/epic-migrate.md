---
tracker_id: ""
type: epic
title: "Migrate skill (Kafka Connect)"
parent: initiative-rpcn-skills
covers: [R7]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md]
after: []
refined: false
risk: medium
---

# Migrate skill (Kafka Connect)

## Description

Delivers `rpcn-migrate`, which converts Kafka Connect connector configs to RPCN pipelines and reports every field it cannot map.

## Outcome

Teams leaving Kafka Connect get working RPCN pipelines without rewriting configs by hand (initiative R7).

## Done when

- A set of sample Kafka Connect configs converts to pipelines that lint clean, and every unmapped field is reported.
- Migrate runs headless in CI and ends with a JSON status.
- Its skills meet R9 (size and references), R12 (triggering evals), R16 (hand-off files), R17 (headless status) and R19 (what next), using epic 1's conventions.

## Boundaries

- In: `rpcn-migrate`, the migration report, and headless runs in CI.
- Out: Benthos migration and moving data (Redpanda Migrator).

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md`: AD-4, AD-6, AD-8; Deferred: Migrate mapping tables
