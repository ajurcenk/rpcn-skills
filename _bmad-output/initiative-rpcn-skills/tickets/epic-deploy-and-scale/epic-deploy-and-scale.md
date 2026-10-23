---
tracker_id: ""
type: epic
title: "Deploy and Scale skills"
parent: initiative-rpcn-skills
covers: [R5, R6]
sources: []
companions: [_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md]
after: []
refined: false
risk: high
---

# Deploy and Scale skills

## Description

Delivers `rpcn-scale` and `rpcn-deploy`. Scale writes a capacity plan covering memory, CPU and network. Deploy produces Kubernetes/Helm, streams-mode, secrets and BYOC deployments sized from that plan.

## Outcome

Developers and DevOps engineers deploy pipelines sized right the first time (initiative R5, R6).

## Done when

- For a reference workload, the plan is within ±20% of load-test usage on the deployed pipeline, and the pipeline holds target throughput with no out-of-memory restarts.
- Deploy produces working deployments for Kubernetes/Helm, streams mode and BYOC, with secrets referenced, never inlined.
- Its skills meet R9 (size and references), R12 (triggering evals), R16 (hand-off files), R17 (headless status) and R19 (what next), using epic 1's conventions.

## Boundaries

- In: `rpcn-scale`, `rpcn-deploy`, the capacity plan, and deployment files for Kubernetes/Helm, streams mode and BYOC.
- Out: post-deploy tuning (epic 6) and Migrate (epic 7).

## References

- parent — `_bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md`, section Requirements
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md`: AD-6, AD-7, AD-8; Deferred: load-test environment, capacity model, deployment specifics

## Notes

- Open question: What capacity model backs Scale, and is there internal benchmark data? (initiative Notes; settled when this epic is refined)
