---
title: "Addendum: Redpanda Connect Skills Plugin"
created: 2026-10-22
updated: 2026-10-22
---

# Addendum: Redpanda Connect Skills Plugin

Detail meant for downstream documents (PRD, architecture), kept out of the brief.

- Prior art and the summary table → PRD scope and differentiation.
- Landscape → PRD positioning and risks.
- Companion product → architecture integration points.

The prior-art sections use the source repos' job names. Debug roughly equals the brief's Test + Tune, and Extend is out of scope in the brief.

## Summary: prior art vs the brief's design principles

| Brief principle | A: in-repo plugin | B: skills repo |
|---|---|---|
| 1. Checked against the binary | Partly: schema reads come from the binary, but the lint loop is prose only | No: reads source only |
| 2. Short skills, detail on demand | No: long inline primers | Partly: reference index, but long bodies |
| 3. Failure modes from real cases | No | No: source-derived edge cases only |
| 4. Synced with each release | No sync, stale dist | Routine-based sync, hand-written references, no regeneration |
| 5. Tested like code | Fixtures exist, no runner | None |
| Job split (not a principle) | Author only | Split by product/connector; Author + Debug |


## Prior art A: in-repo plugin (`redpanda-data/connect/.claude-plugin`, checked at v4.112.0)

- **Shape:** one plugin `redpanda-connect` v0.2.0 (marketplace.json 0.1.0). Installed via `/plugin marketplace add https://github.com/redpanda-data/connect.git`. Claude Desktop ZIPs are in `dist/`. There are 4 commits in total.
- **Prerequisites:** rpk, `rpk connect`, python3, jq. Setup covers macOS (brew) and Ubuntu (apt) only.
- **Skills (Author job only):**
  - `bloblang-authoring` (442-line SKILL.md with the full Bloblang primer inline). It builds a version-keyed XML cache of functions/methods from `rpk connect list --format jsonschema`, and `test-blobl.sh` runs `rpk connect blobl`.
  - `component-search` (136 lines). It filters `rpk connect list --format jsonschema <category>` into required/optional/advanced/secret fields and fetches docs `.md` from docs.redpanda.com.
  - `pipeline-assistant` (330 lines). It orchestrates the other two using `rpk connect create/lint/run`, plus 12 recipe pairs (DLQ, router, multicast, CDC replication, S3, windowing, rate limiting, metrics).
- **Commands:** `/rpcn:blobl`, `/rpcn:pipeline`, `/rpcn:search` are thin wrappers.
- **Validation:** schema reads come from the installed binary, which makes the plugin version-aware (strong). The lint/blobl test loop is a prose instruction only and is not enforced.
- **Tests:** `tests/fixtures/` holds 29 blobl, 33 pipeline and 34 search cases. There is no runner and no CI, and some expectations are wrong (the `kafka-consumer` case omits `kafka_franz`).
- **Release sync:** none. The only build is `task build:skills` (zip), and no workflow calls it. The committed `dist/` is stale (2025-12 ZIPs vs 2026-10-08 source edits), and the version has not been bumped.
- **Brittleness:**
  - The bash-only scripts use relative paths that assume the working directory is the skill directory.
  - The cache is written into the plugin install directory.
  - `recipes/validate.sh` always fails because `.env.validation` is missing.
  - A grep example has no `-r` flag.
  - Version examples are stale (4.70/4.72).
  - Docs URLs have needed 2 fixes already, a sign of drift.
- **MCP:** no references to `rpk connect mcp-server`, which is still present and experimental (see Landscape). It mentions only the external Redpanda Docs MCP.
- **Coverage by job:** Author only. Missing:
  - Debug: logs, metrics, traces, failure catalog.
  - Migrate: Benthos, Kafka Connect, upgrades.
  - Deploy: Docker, Helm, Cloud, streams mode, `rpk connect test`.
  - Extend (out of scope in the brief): Go `public/service`, plugins.

## Prior art B: `redpanda-data/skills` repo (one `redpanda` plugin, 32 skills, 11 of them Connect)

- **Shape:** marketplace plugin `redpanda@redpanda-skills` v0.1.0, invoked as `/redpanda:<skill>`. It follows the agentskills.io spec and is modeled on google/skills.
- **Connect skills:** `connect`, `connect-debugging`, and 9 `connect-cdc-*` (postgres, mysql, mongodb, sqlserver, oracle, dynamodb, spanner, salesforce, tigerbeetle).
- **Conventions worth keeping:**
  - The description follows the pattern "does X. Use when … For Y see `/redpanda:Z`".
  - SKILL.md must stay under 500 lines; Connect skills run 164–337 lines.
  - A "Reference Directory" index acts as the progressive-disclosure entry point.
  - Each CDC skill has a fixed reference set (config-reference, pipeline-and-output, setup-<db>, enterprise-*).
  - A required `SOURCES.md` maps each file to upstream source and keeps TODO and sync-log sections.
- **Coverage by job:**
  - Author: strong.
  - Debug: decent. It covers lint/dry-run, logs, metrics, tracing, health and pprof, but `failure-modes.md` is a generic triage playbook, not sourced from support cases.
  - Migrate: only `redpanda_migrator` (Kafka cluster to Redpanda). Kafka Connect/Debezium config translation is missing.
  - Deploy: thin. There is `streams-mode.md` and a Docker snippet; Kubernetes gets one line; there is no Helm and no Cloud/BYOC Connect.
  - Extend (out of scope in the brief): none. No Go `public/service`, Python or dynamic plugins.
- **Validation:** none against the binary. Accuracy comes from reading source (Go `Spec()`, info.csv) through MCP. YAML and Bloblang examples are never linted or run.
- **Maintenance model:**
  - Generator → critic → human-merge. Seven scheduled Claude routines, including a weekly release-pinned Connect generator, a 6-hourly read-only critic and a monthly drift audit.
  - Routine prompts and reports live in the private `docs-team-standards` repo.
  - CI only checks that SOURCES.md exists and runs skill-validator (frontmatter and size).
  - No evals. Component references are hand-written, not regenerated.
- **Weak spots:**
  - Enterprise/licensing content is duplicated across about 11 files.
  - The repo's own "durability" rule (no hardcoded versions or defaults) is broken in practice.
  - Open TODOs in nearly every SOURCES.md.
  - MAINTAINING.md and CLAUDE.md contradict each other on CI.
  - mysql_cdc + parquet_encode is described only as "compatible", with no failure mode.

## Landscape (web research, 2026-10-22)

- **Redpanda's own AI tooling:**
  - The skills repo has almost no adoption: about 8 stars, and skills.sh shows 2 installs for `connect`. https://www.skills.sh/redpanda-data/skills/connect
  - Workshop post on the in-repo plugin (Feb 2026): https://www.redpanda.com/blog/redpanda-connect-bloblang-claude-workshop
  - **The MCP server has not been removed.** `rpk connect mcp-server` is still in `main` and in the docs as experimental: https://docs.redpanda.com/streaming/current/reference/rpk/rpk-connect/rpk-connect-mcp-server/ The 4.88.0 changelog does not mention removing it. The idea note's (`docs/first_idea.txt`) claim [6] is contradicted; see the brief's Open Questions.
  - `rpk connect agent init/run` is experimental. https://docs.redpanda.com/streaming/current/reference/rpk/rpk-connect/rpk-connect-agent.md
  - Other tools: the Docs MCP (`https://docs.redpanda.com/mcp`), the Cloud MCP (beta, `rpk cloud mcp install`), and ADP with a Claude Code integration. https://docs.redpanda.com/agentic-data-plane/connect/claude-code.md
  - There is no official Kafka Connect → RPCN config converter. Redpanda Migrator moves data, schemas and ACLs, not connector configs.
- **Competitors:**
  - **Confluent agent-skills** (GA 2026-05-19) ships a Claude plugin, a Cursor plugin and `npx skills`. It has an `msk-migration` skill, per-skill `evals/`, a 90% eval gate run by a reviewer skill, and a dashboard. It also has local and managed MCP servers. This is the strongest example of eval-gated vendor skills. https://confluent.io/blog/ai-developer-tools-mcp-server-agent-skills-ga/
  - Conduit: `conduit mcp` and a Kafka Connect connector wrapper.
  - Airbyte: MCP with Connector Builder tools, plus Claude skills.
  - Conduktor: MCP and skills.
  - WarpStream and Estuary: MCP only.
  - Bento: none.
  - Nobody ships a skill that translates Kafka Connect configs to another tool.
- **Distribution norms:**
  - The agentskills.io open spec (Dec 2025) is adopted by more than 30 clients.
  - Vendors ship one repo with both an `npx skills` install and a Claude marketplace install (Supabase, Confluent, Anthropic, Stripe).
- **Eval evidence:**
  - Vercel found skills scored 53% by default, no better than no docs. Telling the agent to use them raised the score to at most 79%. An 8KB AGENTS.md docs index scored 100%. **Trigger reliability is a core risk.** https://vercel.com/blog/agents-md-outperforms-skills-in-our-agent-evals
  - Anthropic's skill-creator has eval, benchmark and description-optimization modes, and a `claude plugin eval` exists (secondary sources).
- **Pain signals in redpanda-data/connect issues:**
  - Keyword counts: bloblang 309, kafka connect 89, streams mode 78, error handling 52, kubernetes 29, cdc 29, helm 6.
  - Recurring themes: CDC correctness (the most changelog fixes), Kafka ordering and stalls, backpressure and memory, custom processor thread safety, Rust plugin templates, the K8s SYS_CHROOT capability, and Bloblang edge cases (ClickHouse maps, Avro).
  - Deprecation drift: `kafka`/`kafka_franz` are deprecated in favour of `redpanda`.
  - There is no public evidence of Kafka Connect migration pain. Demand seen in Slack is internal only.

## Companion product: Pipeline Designer for Redpanda Connect (VS Code), `../rpcn-vscode-byoc-plugin`

- **Status:** 0.0.1 proof of concept, distributed as a CI-built `.vsix`.
  - **Shipped:** schema-based completion and hover, lint on save with Quick Fixes, Bloblang highlighting and completion, snippets, Run and Stop, a read-only pipeline graph, and a Bloblang test panel.
  - All 4 planned epics are done; the initiative stays open for the later roadmap phases.
- **Its roadmap:** Author → Test → **Assist** (AI help to generate, explain and fix, possibly through `rpk connect mcp-server`) → **Deploy** (push to Redpanda Cloud BYOC) → Observe. Assist and Deploy have no epics yet, and the code has no AI hooks.
- **How it uses the binary:**
  - Lookup: `rpk connect` on PATH, then `redpanda-connect`, then the `binaryPath` setting. Versions below v4.100.0 are rejected.
  - Schema: `list --format jsonschema` merged with `json-full`.
  - Lint: `lint --deprecated --skip-env-var-check` with `--resources` and `--env-file`. Output is text, not JSON.
  - Mapping tests run a temporary one-message pipeline through `run`, because `blobl server` drops metadata.
  - All flags are defined in one place, `src/core/args.ts`.
- **Places the skills could connect:**
  - **Shared CLI flags:** use the same lint and run flags, so results from a skill match the editor's.
  - **Sample files:** a skill can write or read `<config>.samples.json` (v1 format, stored beside the config). The test panel then picks them up.
  - **Snippets:** they already lint clean on the pinned binaries (v4.100.0 and v4.112.0) and could be shared as recipes.
  - **Test corpus:** `test/corpus` holds 15 configs with recorded lint, graph and samples output for v4.100.0 and v4.112.0, usable as a parity check for skill evals.
  - **VS Code commands:** `refreshSchema`, `testMapping`, `run`, `showGraph`.
  - **Config detection rule:** a top-level `input`, `pipeline`, `output`, `buffer` or `*_resources` key.
  - **Schema cache:** it lives in VS Code's private storage, so skills should call `list` themselves.
  - **BYOC deploy:** nothing exists yet in either product.
- **Overlap with the skills plugin:**
  - **Primary user:** this brief and the extension's brief share it: "RPCN developers who build and test locally, later deploy to BYOC".
  - **Main selling point:** "Matches your runtime" (the user's own binary, version and plugins), which is the same idea as principle 1.
  - **Success measures it defines:** editor errors match `rpk connect lint`, and a newcomer runs a first pipeline in under 10 minutes.

## BMAD-METHOD patterns (local v6.13.0-next, checked against GitHub `main`, 2026-10-22)

Patterns taken from the BMad skills and how they map to RPCN. Local paths are under `.claude/skills/`.

- **Small SKILL.md:** about 800 tokens per run. References are one level deep and named only when their branch is reached (`bmod-toolsmith/help/craft-progressive-disclosure.md`). RPCN example: Author loads `references/bloblang-pitfalls.md` only when Bloblang is involved, and Deploy loads `references/byoc.md` only on the BYOC branch.
- **Description is the only trigger:** a 5–8 word summary, then "Use when the user says …" with quoted phrases, then "Not for X" when a sibling collides. Revise from eval failures; never paste failed queries in (`craft-description.md`).
- **Scripts:** run as `uv run {skill-root}/scripts/x.py`, with a PEP 723 header, `--help`, JSON on stdout, non-zero exit with a reason, stdlib first, and `scripts/tests/test_<name>.py`. Prose doing deterministic work is a defect, and so is "warn and exit 0" (`craft-scripts.md`, `bmad-toolsmith/lenses/lens-determinism.md`).
- **Shared scripts:** BMad copies them to `_bmad/scripts/` at setup. For RPCN, either each skill vendors its own wrappers, or one `rpcn-tools` skill holds them. Not verified: how `npx skills` lays out sibling skills.
- **Artifact contracts:** "the ticket is the spec". `bmad-build` routes on the frontmatter `status` and halts on ambiguity, and it has a "Ready for Development" standard (`bmad-build/step-01-clarify-and-route.md`, `bmad-build/workflow.md`).
- **Headless mode:** never ask. End with `{"status":"complete","intent":…, <paths>, "open_questions":[]}` or `{"status":"blocked","reason":…}` (`bmad-product-brief/SKILL.md`).
- **"What next":** each module's help has an "After X finishes, offer next" table (`bmod-toolsmith/help/help.md`). For RPCN this goes in each skill's closing step, not in a router skill.
- **Evals** (`bmad-eval/SKILL.md`, `references/eval-format.md`):
  - Four modes: baseline (skill vs bare model; retire a skill the model matches), variant, quality (rubric) and trigger.
  - Storage: `evals/cases.json` (`input`, `rubric`, `state_prefix`, `files`) and `evals/triggers.json` (`{query, should_trigger}` with near-miss negatives).
  - Each case runs at least 3 times in a clean temp dir with a fresh HOME.
  - On GitHub only 3 skills carry `triggers.json`, and CI does not run evals.
- **Versioning:**
  - The version lives once per module in `bmod.toml`, stamped by `stamp_release.py`.
  - `retired.toml` lists renamed and removed skills, and a retired name is never reused.
  - Deterministic CI validation via `tools/validate_skills.py` (rules SKILL-01..07), `validate_file_refs.py` and `validate_manifests.py`.
- **Review lenses:** findings share one shape (`lens`, `location`, `trigger_condition`, `guard_snippet`, `potential_consequence`). For RPCN, a verification-gap lens fits Deploy (secrets, resources, DLQ).
- **Naming:** own prefix, never `bmad-` (`bmod-toolsmith/help/naming.md`).
- **Avoided for RPCN:**
  - the `_bmad/` setup runtime, the layered TOML resolver and rendered skills, because `npx skills` users expect skills to work at once
  - personas, menus and coaching conversations
  - a memlog in every skill (Migrate only)
