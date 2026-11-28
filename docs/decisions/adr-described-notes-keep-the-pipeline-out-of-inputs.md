# Described notes keep the pipeline out of `inputs`

When rpcn-design describes an existing, hand-written pipeline (describe mode, story 8.1, commit `cc6c727`; plan `_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/tickets/story-tracer-rpcn-design-describes-a-hand-written-pipeline-plan.md`), the `design@1` note names the pipeline in Purpose and writes `inputs: []`, so neither the pipeline nor its resources, `.blobl` or `.env.example` files are hashed. A later re-run never adds them (`rerun.md`, story 8.6, commit `df8ef84`).

The reason is staleness. A note that hashed the pipeline would go stale as soon as rpcn-author's change mode edited the pipeline, and `design@1` lets rpcn-author write only Deviations rows and `updated`, not `inputs`. The user chose this option (a) on 2026-11-25 (epic file `epic-existing-pipelines.md`, Notes). They declined option (b), letting Author refresh `inputs` (a change to `design@1`'s "Who writes what"), and option (c), accepting staleness and re-describing after every change.

The cost is that a described note never detects a pipeline edited by hand behind its back.
