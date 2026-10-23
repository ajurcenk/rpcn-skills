---
title: "Product Brief: Redpanda Connect Skills"
status: final
created: 2026-10-22
updated: 2026-10-22
---

# Product Brief: Redpanda Connect Skills

## Executive Summary

Redpanda Connect Skills is a set of agent skills for Claude Code, and for any other client that supports the open Agent Skills spec. It helps a Redpanda Connect (RPCN) developer through the whole life of a pipeline:

1. **Design:** shape it using RPCN best practices.
2. **Author:** write its YAML and Bloblang.
3. **Test:** check it before it runs for real.
4. **Tune:** improve its performance.
5. **Scale:** plan its capacity.
6. **Deploy:** run it in production.
7. **Migrate:** convert existing Kafka Connect configurations to it.

Each skill checks its own output against the developer's installed `rpk connect` binary before showing it. As a result, answers match the developer's RPCN version and never contain config fields that don't exist.

Version 1 ships Design, Author and Test, plus binary-validation helpers, an eval harness and release-sync CI. Deploy, Tune and Scale follow, and Migrate comes last.

Two partial Redpanda skill sets exist today. Neither checks against the binary, runs evals, or covers deployment, capacity or migration. This project builds one new skill set and uses the two existing sets only as references.


## The Problem

An RPCN developer loses time at every stage of a pipeline's life:

- **Design:** Error handling, dead-letter queues, retries and batching are patterns the developer has to know already. Nothing suggests them while the pipeline is being designed.
- **Author:** RPCN has hundreds of components. Developers guess field names, and Bloblang takes time to learn. A general-purpose model often suggests fields that don't exist or that belong to another version.
- **Test:** It is unclear how to test a pipeline before running it for real. The lint-fix-lint loop is manual. `rpk connect test` and dry runs are little known.
- **Tune:** Developers adjust throughput, batching and backpressure without a guide to reading RPCN's logs and metrics.
- **Scale:** Developers size memory, CPU and network for a deployment by trial and error.
- **Deploy:** Docs and existing skills cover Kubernetes, streams mode, secrets and Redpanda Cloud BYOC poorly. The existing skills give Kubernetes one line and don't cover BYOC at all.
- **Migrate:** Teams moving from Kafka Connect rewrite connector configs by hand. Redpanda Migrator moves data, schemas and ACLs, not connector configs.

Today a developer has three options, and none covers the whole job:
- the docs
- a general-purpose model with no knowledge of their binary
- two partial skill sets that are not kept in sync with RPCN releases

The `redpanda-data/connect` plugin's distributed bundles are about 10 months older than its source. The component references in `redpanda-data/skills` are written by hand and drift.

## The Solution

**One plugin with small skills, one for each lifecycle job:**

| Job | What the skill does |
|---|---|
| **Design** | Proposes a pipeline shape using RPCN best practices: error handling, DLQ, retries, batching, idempotency, ordering. |
| **Author** | Writes pipeline YAML and Bloblang, using component fields read from the installed binary. |
| **Test** | Lints, runs Bloblang against sample data, does dry runs, writes `rpk connect test` cases, and diagnoses failures. |
| **Tune** | Reads logs and metrics, and recommends changes to throughput, batching and backpressure. |
| **Scale** | Plans capacity: memory, CPU and network for a given workload. |
| **Deploy** | Covers Kubernetes and Helm, streams mode, secrets, and Redpanda Cloud BYOC. |
| **Migrate** | Converts Kafka Connect connector configs to RPCN pipelines and lists anything that cannot be translated. |

**Design principles:**
1. **Every result is checked against the binary.** Skills run `rpk connect lint`, `rpk connect blobl` and `rpk connect list` and fix their output until it passes. The check is enforced by the skill's helper scripts, not left as an instruction to the model.
2. **Short skills, detail on demand.** Each SKILL.md says when the skill applies. Details such as per-connector notes and known edge cases sit in `references/` files that the agent loads only when needed.
3. **Known failure modes come from real cases.** Each resolved support issue becomes a reference entry. This is knowledge a general-purpose model doesn't have. Cases come from `redpanda-data/connect` GitHub issues first. Aleksej curates them and adds more sources later.
4. **Kept in sync with each release.** CI regenerates component references for every RPCN release. It fails when a skill mentions a removed or deprecated component (for example `kafka` or `kafka_franz`, replaced by `redpanda`).
5. **Skills are tested like code.** Each change runs a set of eval prompts. The output must pass lint, and each skill must trigger on the requests it is meant for.

**Artifacts and hand-offs.** Each skill writes plain files into the developer's project, and the next skill reads them. Any stage can therefore start from files alone, with no chat history, and every hand-off can be reviewed in git.

| Skill | Writes | Read by |
|---|---|---|
| **Design** | A design note only (no YAML): what goes in and out, the chosen components, error handling (DLQ, retries, fallback), delivery and ordering guarantees, batching, and the decisions still open. | Author, Scale, Test |
| **Author** | Pipeline YAML and resource files, Bloblang inline or as `.blobl` files, and `.env.example` with secrets as `${ENV}`. | Test, Deploy |
| **Test** | Bloblang sample files, `rpk connect test` unit tests, and a test report. | Tune |
| **Scale** | A capacity plan: workload assumptions, plus CPU, memory, network and replicas, with the reasoning. | Deploy |
| **Deploy** | Kubernetes manifests or Helm values, the streams-mode layout, references to secrets (never their values), and the BYOC pipeline definition. | Tune |
| **Tune** | A tuning report: each metric, what was observed, the recommended change and a diff to the YAML. | Author |
| **Migrate** | Converted pipeline YAML and a migration report listing every Kafka Connect field that could not be mapped. | Test |

The design note is the contract between Design and Author. Author builds from the note. When Author has to deviate, it updates the note instead of silently diverging. Test checks the pipeline against both the binary and the note. Exact file names and formats are set when the shared foundation is designed.

**How the skills are built.** These practices are adapted from the BMAD-METHOD skills (see addendum):
- **Check scripts:** helper scripts wrap `rpk connect` and return JSON with a non-zero exit on failure, so "fix until it passes" is mechanical. Each script has unit tests.
- **Small skills:** each SKILL.md is about 800 tokens. A reference loads only at the step that needs it, one level deep.
- **Descriptions:** each one quotes real trigger phrases and names the sibling it is not for (for example "Not for capacity sizing: use `rpcn-scale`").
- **Status on hand-offs:** each hand-off file carries a `status` in its header, and the receiving skill checks a readiness list before using it.
- **Headless mode:** with no one present, a skill never asks. It ends with a JSON status (`complete` or `blocked`, a reason and file paths), so Test and Migrate can run in CI and evals can grade a fixed output.
- **Evals:** trigger cases with near-miss negatives, task cases with fixture files, at least 3 runs in a clean environment, and a comparison against the bare model.
- **Versioning:** one version per release, stamped with the RPCN release the references were generated from, so a skill warns when the installed binary is newer. A list of retired and renamed skills means no name is reused. A CI validator checks names, descriptions and file references.
- **"What next":** each skill closes by naming the next skill.
- **Naming:** skills use the `rpcn-` prefix, checked against `/rpcn:*` and `/redpanda:*`.

## What Makes This Different

- **It matches the user's runtime.** Answers come from the binary the developer actually runs: its version, its components, its plugins. The existing skills repo never runs the binary.
- **It covers the whole lifecycle.** No current Redpanda skill set covers capacity planning, deployment or Kafka Connect migration.
- **It has a Kafka Connect migration skill.** This is the clearest differentiator: no vendor ships a skill that translates Kafka Connect configs.

It does not have a technical moat. The advantage is direct access to the binary and to Redpanda field engineers, and faster iteration than the existing sets.

## Who This Serves

**Primary user: the RPCN developer.** This is someone who builds pipelines: writes YAML and Bloblang, tests locally, deploys to Kubernetes or BYOC, and runs the pipelines in production. They may be a customer's data engineer, a Redpanda field engineer, or an internal user. Success means:
- fewer trips to the docs
- config that is correct on the first attempt
- confidence that a pipeline that works locally will also work in production

**Secondary user: DevOps engineers who deploy and operate RPCN.** They size, deploy, tune and scale pipelines on Kubernetes or BYOC. The Deploy, Tune and Scale skills serve them.

**Out of scope:** developers who extend RPCN (see Scope).

## Success Criteria

- **Correctness (v1):** 100% of generated configs pass `rpk connect lint` on the tested binaries (v4.100.0 and the newest release). Bloblang mappings the skills write produce the expected output when run with `rpk connect blobl` on the eval samples.
- **Triggering (v1):** at least 90% of in-scope eval prompts trigger the right skill, and out-of-scope prompts trigger no skill.
- **Freshness (v1):** reference material is regenerated within one week of each RPCN release, and CI blocks merges that mention removed or deprecated components.
- **Time to a working pipeline (v1):** a developer new to RPCN gets a linted, tested pipeline running in under 10 minutes.
- **Tune (after v1):** on a reference pipeline with a known bottleneck, the recommended changes measurably raise throughput or cut latency, and each recommendation names the metric that prompted it.
- **Scale and Deploy (after v1):** for a reference workload, planned memory, CPU and network are within ±20% of what a load test on the deployed pipeline uses, and the pipeline holds its target throughput with no out-of-memory restarts. Reference workloads and exact numbers are set when these skills are planned.
- **Migration (after v1):** a set of sample Kafka Connect configs converts to RPCN pipelines that pass lint, and each field that cannot be mapped is reported.

## Scope

**Version 1:**
- Design, Author and Test skills.
- The validation helpers that call the binary.
- An eval harness that checks that output passes lint and that skills trigger correctly.
- Release-sync CI.
- Distribution from this project as a Claude Code plugin, and through `npx skills` following the Agent Skills spec.
- Coexistence with the two existing skill sets, with skill and command names that do not clash with `/rpcn:*` or `/redpanda:*`. Replacing them or offering this set upstream is decided after version 1, based on eval results.

**Next, in order:**
1. Deploy, Tune and Scale.
2. Migrate (Kafka Connect), last: demand is internal to Redpanda, with no public evidence in GitHub issues.

**Out of scope:**
- Extending RPCN: Go components, Python and RPC plugins, core contributions.
- Maintaining the two existing skill sets.
- Running an MCP server.
- Any integration with the Pipeline Designer VS Code extension. This initiative is about the skills only.

## Vision

In two or three years, an RPCN developer will describe a pipeline in Claude Code or any client that supports Agent Skills and get one that is designed, tested, sized and deployed, and correct for the binary they run. Release-synced references and a growing list of real failure modes will make the skills the most reliable source on running RPCN in production.

## Open Questions

- What capacity model backs Scale, and is there internal benchmark data? Deferred until after version 1.
- Should teams get one org-facts file (registry, secret store, naming rules) that every skill reads?
