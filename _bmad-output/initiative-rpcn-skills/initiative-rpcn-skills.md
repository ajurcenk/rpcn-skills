---
type: initiative
title: "RPCN developers design, build, test, tune, scale, deploy and migrate pipelines with binary-checked agent skills"
parent: none
sources:
  - _bmad-output/initiative-rpcn-skills/brief-rpcn-skills/brief-rpcn-skills.md
companions:
  - _bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md
  - _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md
after: []
risk: medium
---

# RPCN Skills

## Description

When this initiative is done, a Redpanda Connect (RPCN) developer has one set of agent skills that covers the whole life of a pipeline: design, author, test, tune, scale, deploy and migrate from Kafka Connect. Every result is checked against the developer's own `rpk connect` binary before it is shown. The set is built in this project. It replaces the two partial skill sets as the place to work, which stay references only. See the brief for the problem and the addendum for prior art and integration seams.

## Outcome

RPCN developers and the DevOps engineers who run their pipelines get configs that are correct for their installed binary on the first attempt, at every lifecycle stage. The signals are the brief's Success Criteria: correctness, triggering, freshness and time to a working pipeline.

## Requirements

- R1 (brief Solution: Design; Artifacts and hand-offs): The Design skill writes a design note that applies RPCN best practices: error handling, DLQ, retries, batching, idempotency and ordering. It is met when the note names each relevant pattern, and the pipeline Author builds from it contains those patterns and passes lint.
- R2 (brief Solution: Author): The Author skill writes pipeline YAML and Bloblang using only component fields the installed binary reports. It is met when no generated field is absent from `rpk connect list` for that version.
- R3 (brief Solution: Test): The Test skill lints, runs Bloblang against sample data, does dry runs, writes `rpk connect test` cases and diagnoses failures. It is met when a failing pipeline gets a stated cause and a fix that passes.
- R4 (brief Solution: Tune): The Tune skill reads RPCN logs and metrics and recommends throughput, batching and backpressure changes, each naming the metric that prompted it. It is met when, on a reference pipeline with a known bottleneck, the changes measurably raise throughput or cut latency.
- R5 (brief Solution: Scale): The Scale skill produces a capacity plan covering memory, CPU and network for a stated workload. It is met when, for a reference workload, the plan is within ±20% of what a load test on the deployed pipeline uses, and the pipeline holds its target throughput with no out-of-memory restarts.
- R6 (brief Solution: Deploy): The Deploy skill produces deployments for Kubernetes and Helm, streams mode, secrets handling and Redpanda Cloud BYOC. It is met when the deployed reference workload gets the resources from the R5 plan and meets the same ±20% and no-restart check.
- R7 (brief Solution: Migrate; Success Criteria: Migration): The Migrate skill converts Kafka Connect connector configs to RPCN pipelines that pass lint, and reports every field it cannot map.
- R8 (brief Design principle 1; Success Criteria: Correctness): Before a config or Bloblang result is shown, helper scripts check it against the installed binary (`rpk connect lint`, `blobl`, `list`) until it passes. The scripts return JSON and exit non-zero on failure, and each has unit tests (brief How the skills are built). It is met when 100% of generated configs lint clean on the tested binaries, and Bloblang produces the expected output on the eval samples.
- R9 (brief Design principle 2; How the skills are built): Each SKILL.md states when it applies and stays around 800 tokens. Detail lives in `references/` files, one level deep, that load only at the step that needs them.
- R10 (brief Design principle 3): Resolved support cases, starting with `redpanda-data/connect` GitHub issues, become known-failure-mode reference entries, each naming its case.
- R11 (brief Design principle 4; Success Criteria: Freshness): Component references are regenerated within one week of each RPCN release. CI blocks merges that mention removed or deprecated components.
- R12 (brief Design principle 5; Success Criteria: Triggering; How the skills are built): Each description quotes real trigger phrases and names the sibling it is not for. Every change runs the evals: trigger cases with near-miss negatives, and task cases with fixture files, each run at least 3 times in a clean environment and compared against the bare model. It is met when output passes lint, at least 90% of in-scope prompts trigger the right skill, and out-of-scope prompts trigger none, including when the two existing skill sets are installed alongside.
- R13 (brief Scope: Version 1): The set installs from this project as a Claude Code plugin and through `npx skills`, per the Agent Skills spec.
- R15 (brief Success Criteria: Time to a working pipeline): A developer new to RPCN gets a linted, tested pipeline running in under 10 minutes.
- R16 (brief Solution: Artifacts and hand-offs): Each skill writes defined files that the next skill reads, so any stage can start from files alone, with no chat history. Each hand-off file carries a `status` in its header, and the receiving skill checks a readiness list before using it (brief How the skills are built). When Author deviates from the design note, it updates the note. It is met when each skill, started in a fresh session with only the previous skill's files, completes its job.
- R17 (brief How the skills are built: Headless mode): With no one present, a skill never asks. It ends with a JSON status (`complete` or `blocked`, a reason and file paths). It is met when Test and Migrate run in CI and evals grade that status block.
- R18 (brief How the skills are built: Versioning): Each release is stamped with the RPCN release its references were generated from, and a skill warns when the installed binary is newer. Retired and renamed skill names are listed and never reused. A CI validator checks names, descriptions and file references, and blocks a merge that fails.
- R19 (brief How the skills are built: What next): Each skill closes by naming the next skill for the developer's situation.

## Constraints

- The installed `rpk connect` binary is the source of truth for components and fields. General model knowledge never substitutes for it (brief What Makes This Different).
- The tested binaries are v4.100.0 (the minimum supported) and the newest RPCN release, rolling forward (brief Success Criteria: Correctness).
- Build order: version 1 is Design, Author and Test, plus the validation helpers, eval harness and release-sync CI. Deploy, Tune and Scale come next, and Migrate comes last because demand for it is internal only (brief Scope).
- The skill set is new and built in this project. The `redpanda-data/connect` plugin and `redpanda-data/skills` are references only, and this initiative does not maintain or extend them (brief Executive Summary; Scope: Out of scope).
- The skills follow the open Agent Skills spec, so clients other than Claude can load them (brief Executive Summary).
- Skill and command names must not clash with `/rpcn:*` (the `redpanda-data/connect` plugin) or `/redpanda:*` (`redpanda-data/skills`), because the sets coexist (Decision 2026-10-22). Skills use the `rpcn-` prefix (brief How the skills are built: Naming).

## Done when

- The version 1 skills (Design, Author, Test) install as a Claude Code plugin and through `npx skills`, and every generated config lints clean on the tested binaries.
- The eval harness runs on every change, at least 90% of in-scope prompts trigger the right skill, and out-of-scope prompts trigger none.
- After an RPCN release, references are regenerated within a week, and CI rejects a change that mentions a removed component.
- All seven jobs ship, ending with Migrate converting the sample Kafka Connect configs with every unmapped field reported.

## Boundaries

- Out: extending RPCN (Go components, Python and RPC plugins, core contributions).
- Out: maintaining or changing the `redpanda-data/connect` plugin or `redpanda-data/skills`.
- Out: running an MCP server.
- Out: any integration with the Pipeline Designer VS Code extension.
- Touch point: the `rpk connect` binary, tested at v4.100.0 and the newest release. Check scripts call `lint`, `blobl`, `list` and `test`. Owner: epic-validation-foundation.
- Touch point: the `rpcn-test-skills` test project (`../rpcn-test-skills`). It installs the skills the way a user would and runs end-to-end scenarios. Owner: epic-validation-foundation.
- Touch point: `redpanda-data/connect` GitHub issues, mined for failure-mode entries. Owner: epic-release-sync.
- Touch point: Kubernetes/Helm and Redpanda Cloud BYOC, the deployment targets. Owner: epic-deploy-and-scale.
- Tracer path: a developer describes a pipeline, Design shapes it, Author writes it, Test proves it lints and runs, Scale sizes it, Deploy ships it to Kubernetes or BYOC, Tune adjusts it from metrics, and Migrate brings in Kafka Connect configs.

## References

- brief — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/brief-rpcn-skills.md`, sections The Solution (including Artifacts and hand-offs), Success Criteria, Scope
- research — `_bmad-output/initiative-rpcn-skills/brief-rpcn-skills/addendum.md`: prior art summary table, landscape, companion product seams, BMAD-METHOD patterns
- architecture — `_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md`: AD-1 to AD-14, conventions, structural seed, deferred list

## Notes

- Open question: What capacity model backs Scale, and is there internal benchmark data? R5 waits on this. Deferred until after version 1 and settled when the Scale epic is refined (Decision 2026-10-22).
- Open question: Should teams get one org-facts file (registry, secret store, naming rules) that every skill reads?
- Unknown: How `npx skills` lays out sibling skills on disk. This decides whether one shared `rpcn-tools` skill holds the binary wrappers, or each skill carries its own. Epic 1 waits on this.
- Decision (2026-10-22): Failure-mode cases come from `redpanda-data/connect` GitHub issues first. Aleksej curates them and adds more sources and cases later (R10).
- Decision (2026-10-22): In version 1 this set coexists with the two existing skill sets. Replacing them or offering this set upstream is decided after version 1, based on eval results.
- Decision (2026-10-22): The question of whether `rpk connect mcp-server` stays long term is dropped. Running an MCP server is out of scope.
- Decision (2026-10-22): The success checks for Tune, Scale and Deploy are in R4–R6. The reference workloads and exact numbers are set when those epics are refined.
- Decision (2026-10-22): The under-10-minute target in R15 is confirmed.
- Decision (2026-10-22): BMAD-METHOD patterns adopted: check scripts with JSON output, small skills, description discipline, status on hand-off files, headless mode, the eval layout, versioning with retired names, "what next" and the `rpcn-` prefix. BMad's setup runtime, personas and per-skill decision logs are not adopted (addendum, BMAD-METHOD patterns).
- Decision (2026-10-22): Sliced into 7 epics, one per capability, with the shared foundation first. Version 1 is epics 1–4.
- Decision (2026-10-22): Author and Test (epic 2) are built before Design (epic 3), because R1's check needs Author to build from the design note. The brief lists Design first; that is the user's flow, not the build order.
- Decision (2026-10-22): R9, R12, R16, R17 and R19 are owned by epic 1, which delivers the convention, harness and CI. Each skill epic meets them for its own skills in its Done when.
- Decision (2026-10-23): The initiative covers skills development only. All VS Code extension integration is out: R14 (editor parity) is retired, the earlier code-sharing decision no longer applies, and 4.112.0 is no longer tested. The tested binaries are 4.100.0 and the newest release.
