---
title: 'Tracer: rpcn-author writes a pipeline that lints clean'
type: 'feature'
ticket: '4'
created: '2026-11-06'
status: 'built'
baseline_revision: '94a4be463e2895695c4b765648a04271522ba5b4'
route: 'full'
route_source: 'auto'
risk: 'high'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The repo has only `rpcn-test`, which can lint a pipeline but not write one. Epic 2's tracer bullet is `rpcn-author`'s first slice: from a plain request, it writes pipeline files that lint clean on the installed binary using only the fields the binary reports (epic R1). It also brings the sibling conventions (AD-9) and the trigger gate (AD-13) to two skills.

**Approach:**
- **The skill:** new `skills/rpcn-author/` with these steps:
  - check the binary
  - pick components with `rpcn_check list`
  - check every field it sets against `rpcn_check fields`
  - write `<name>.yaml` (plus `<name>.resources.yaml` and `.env.example` when needed)
  - lint until clean
  - end with Next naming `rpcn-test`, and the AD-8 status block when headless
- **Sibling edits:** `rpcn-test`'s description "Not for" and its Next name `rpcn-author`, and it stays at 1,200 tokens or less.
- **Evals:** trigger cases for `rpcn-author`, and sibling near-miss negatives in both directions.
- **`rpcn-test-skills`:** the `npx`-alone pair, and two write scenarios: a subfolder pipeline, and a `.yml` pipeline with a cache resource and an env var. The runner learns what those scenarios need to assert.

## Boundaries & Constraints

**Always:**
- AD-1: only files inside the skill folder.
- AD-3: `uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py`, one call per Bash call, with no `cd`.
- AD-4: `binary` first, and the fixed lint arguments.
- AD-6:
  - The pipeline YAML has no header.
  - Files sit beside `<name>.yaml`.
  - Secrets are always `${ENV_VAR}` and listed in `.env.example`, never inline.
- AD-8: the headless rules.
- AD-9: description shape, "Not for … use rpcn-<sibling>", references named at the step that loads them, and Next per situation.
- The shared `rpcn_check.py` comes in through `shared.txt` and `sync_shared.py`. Never hand-edit a copy.
- The validator reports **no warnings** for `rpcn-author`, and no size warning for `rpcn-test`.
- Every `rpcn-author` scenario runs on an `npx` install of `rpcn-author` alone, uses a pipeline in a subfolder, and has `no_cd = true`. One uses a `.yml`, non-default name.
- Commit before the paid eval run. Run all `tools/` test suites before any push.

**Never:**
- Overwrite an existing `<name>.yaml`. In this slice: ask, or when headless, `blocked` with an open question. Updating is story 2.5.
- Add `rpcn-author` behaviour for test reports, design notes or Bloblang files (stories 2.5–2.7).
- Remove trigger phrases from `rpcn-test`'s description to save size.
- Change `rpcn_check.py`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Simple write | headless: "a pipeline in `pipes/heartbeat.yaml` that generates a message every second and prints it to stdout" | `pipes/heartbeat.yaml` lints clean on 4.100.0 and 4.115.0; status `complete`, `checks.lint` `pass` | — |
| Resources and env | headless: a `.yml` pipeline in `pipes/` that enriches messages from a cache resource whose address comes from an env var | `pipes/<name>.yml`, `pipes/<name>.resources.yml` and `pipes/.env.example` are written; the pipeline lints clean with `--resources`; `.env.example` names the variable, and the YAML uses `${VAR}` | — |
| Lint won't clean | lint still fails after 3 revisions | the remaining errors are reported; headless ends `blocked` with the first error | — |
| Existing file | `<name>.yaml` already exists | the file is not written over; interactive: ask; headless: `blocked`, with the question in `open_questions` | — |
| Unknown component | `fields` exits 1 with close matches | a reported match is chosen, or the gap is asked about or recorded in `open_questions` | never write a component the binary doesn't list |
| Lint request | "lint my pipeline" | `rpcn-test` fires and `rpcn-author` stays silent | — |
| Write request | "write me a new pipeline …" | `rpcn-author` fires and `rpcn-test` stays silent | — |

**Decision (2026-11-06, user):** there are two kinds of trigger negative.
- *Out-of-repo* near-misses keep the any-`rpcn-` grader.
- *Sibling* near-misses (a write request for `rpcn-test`, a lint request for `rpcn-author`) assert only that their own skill stayed silent. The sibling's own positives cover it firing.

**Decision (2026-11-06, user):** the plan stays whole, at about 3,000 tokens, over the 1,600 guideline, and is not split. The runner checks are what prove this story's acceptance criteria.

</frozen-after-approval>


## Code Map

`R` = `rpcn-skills`; `T` = `rpcn-test-skills` (local, starting at `4cfec4709cb977f65d73b60cfe2b0d3194704ea3`).

- **`R/skills/rpcn-test/SKILL.md`** (4,799 characters; the validator counts the whole file, frontmatter included, against `len//4 <= 1200`):
  - The description's last sentence is "Not for writing, designing or deploying pipelines." It becomes "Not for writing pipelines: use rpcn-author. Not for designing or deploying them." (`SIBLING_RE`, `validate_skills.py:65`, needs `skills/rpcn-author/` to exist).
  - `## Next` gets a "no pipeline yet / write one: use rpcn-author" bullet.
  - To pay for those characters, move body detail into a new skill-local reference. The status-block bullets are the best candidate. Keep every trigger phrase.
- **New `R/skills/rpcn-author/`:**
  - `SKILL.md`: frontmatter like `rpcn-test`'s, the same `compatibility` (AD-3), `license`, and `metadata.plugin-version`.
  - `shared.txt`: only `rpcn_check/rpcn_check.py scripts/rpcn_check.py`. Syncing a format file SKILL.md never names would be a `file-refs` warning, so formats come in with 2.5 and 2.6.
  - `references/pipeline-files.md` (skill-local): the layout of the resources file (`cache_resources: - label: …`), the `.env.example` format (one `NAME=` line per variable with a comment, no values), and the `${VAR}` rule.
  - Template: `R/skills/rpcn-test/SKILL.md`, for the preamble, the Headless paragraph, the `${CLAUDE_SKILL_DIR}` fallback line, `<dir>/`/`<pipeline>`/`<res>`, and the status block.
- **`rpcn_check` facts:**
  - `list <category>` gives `data.components`.
  - `fields <category> <component>` gives `data.fields[]` with `{path, type, kind, required, default?, advanced, deprecated, secret, description}`. Nested paths come parents first (`tls.enabled`, `a[].b`).
  - An unknown component gives exit 1 with `data.components` (close matches). A cache's fields come without the `cache_resources[]` wrapper.
  - `lint <file> [--resources f]... [--env-file f]` always skips the env-var check.
- **`R/evals/`:**
  - The 8 `rpcn-test__trigger_*` cases stay as they are.
  - The 6 `rpcn-test__miss_*` cases: `miss_write_new_pipeline`'s grader becomes `rpcn-test`-only (a sibling near-miss).
  - Add about 6 `rpcn-author__trigger_*` positives (prompt frontmatter `max_turns: 2`, `allowed_tools: [Skill]`, `tags: [trigger, positive]`; grader `fired.md` with `input_match` for `rpcn-author`), and about 4 `rpcn-author__miss_*` negatives: at least one sibling case (lint) and out-of-repo ones (deploy to k8s, Kafka Connect config).
  - Update `README.md`: the title, the table, the two negative kinds, and the case count and cost.
  - `eval_gate.py` and `run_evals.py` already pick up any `<skill>__trigger_`/`__miss_` folder and any T scenario. No change.
- **`T/run_scenarios.py`:**
  - The `[[lint]]` check (about l.1351) runs only `lint <file>`. Add optional `resources = [..]` and `env_file` keys, validated in `validate_expect`.
  - Lint once per binary listed in `RPCN_TEST_BINARIES` (`:`-separated) when it is set, through `RPCN_BINARY`; otherwise the default binary. The check fails if any binary fails.
  - Add a `[[file]]` check, `{file, contains = [..]}`: the file exists and holds each string.
  - Add tests in `T/tests/test_run_scenarios.py` and a section in `T/README.md`.
- **New T scenarios:**
  - `rpcn-author__npx_trigger`: "Write a Redpanda Connect pipeline in pipes/heartbeat.yaml …, unattended". This is also the simple-write case.
  - `rpcn-author__npx_miss` (`silent = true`).
  - `rpcn-author__write_resources_yml`: the cache and env-var `.yml` case.
  - Each has `install = ["rpcn-author"]` and `allowed_tools = ["Bash(uv run *)", "Read", "Write", "Edit", "Skill"]`, about 40 turns, an empty `pipes/.keep` fixture, `[status]` and `[[lint]]` (`ok = true`).
- **Other:**
  - `R/README.md` l.9–11: add an `rpcn-author` row and fix the stale `rpcn-test` text.
  - CI and `sync_shared.py` already iterate every `skills/*/`. No change.
  - `.cache/rpcn/<v>/` holds the 4.100.0 and 4.115.0 binaries for `RPCN_TEST_BINARIES`.

## Tasks & Acceptance

**Execution:**
- [x] `R/skills/rpcn-author/` (`SKILL.md`, `shared.txt`, `references/pipeline-files.md`), then `uv run tools/sync_shared.py`.
- [x] `R/skills/rpcn-test/SKILL.md` and a new reference: the sibling "Not for" and Next lines, kept at 1,200 tokens or less.
- [x] `R/evals/rpcn-author__*`, `R/evals/rpcn-test__miss_write_new_pipeline/graders/`, `R/evals/README.md`: cases, and the two negative kinds.
- [x] `T/run_scenarios.py`, `T/tests/test_run_scenarios.py`, `T/README.md`: `[[lint]]` `resources`/`env_file`, linting on each binary, and `[[file]] contains`.
- [x] `T/scenarios/rpcn-author__{npx_trigger,npx_miss,write_resources_yml}/`.
- [x] `R/README.md`: the skills table.

**Acceptance Criteria:**
- **Given** the repo, **when** `uv run tools/validate_skills.py` runs, **then** `rpcn-author` has no warnings and `rpcn-test` has no `size` warning.
- **Given** `RPCN_TEST_BINARIES` set to both cached binaries, **when** `run_scenarios.py --source local:../rpcn-skills --scenario 'rpcn-author__*' --runs 1` runs, **then** every scenario passes, and its pipeline files lint clean on both binaries.
- **Given** the committed tree, **when** `uv run tools/run_evals.py` runs (about $11), **then** the gate passes for both skills with negatives silent, every scenario passes 3/3, and a `dirty: false` record is written and committed.
- **Given** all of R's `tools/` suites, `rpcn_check` tests and T's tests, **when** they run before the push, **then** all pass, and CI is green after it.

## Implementation Notes

- **Built in both repos.** Commits: R `77fde7a` and `42dec87` (record); T `d7f802e` and `06bb199`. `rpcn-author` is about 1,175 tokens with no validator warnings. `rpcn-test` is about 1,163 tokens: its status-block bullets moved to `references/status-block.md`.
- **Unplanned:** `--scenario` accepts globs, because the acceptance command `'rpcn-author__*'` needs them.
- **`npx_miss`:** with no pipeline to find, the agent searched and hit 5 turns. It got a `pipes/orders.yaml` fixture and 15 turns. The implementer's first full eval failed only on this ($10.67, uncommitted); the second passed ($10.25, record `2026-11-06-5dea371e33a1`). Both ran before review, so the review patches make that record stale.
- **Matrix audit:** added `rpcn-author__existing_file` (blocked, file unchanged; 1/1 smoke). "Unknown component" and "lint won't clean" are deferred by the user's choice (deferred-work).
- **After review:** `run_evals` passes `RPCN_TEST_BINARIES` (the pinned cached binaries) to the scenarios, and checks for them before any paid step. The final eval record is the first to prove lint on both binaries.

- **The review patch for `no_cd` on `npx_miss` was wrong.** The first post-review run (`f3de850d3066.failed`, $11.03) failed `rpcn-author__npx_miss` 0/3. No skill runs in a near-miss, and Claude Code auto-allowed plain Claude's read-only `cd pipes && cat …` even though Bash is outside `allowed_tools`. T `d2d32d8` now rejects `no_cd` together with `silent` and drops it from that scenario.
- **Final record:** `evals/results/2026-11-06-f3de850d3066.json` passed with `dirty: false`, at $10.97. Trigger accuracy was 1.0 for both skills, and all 9 scenarios passed 3/3, linted on 4.100.0 and 4.115.0. Story 2.4's eval spend in total was about $43 over 4 full runs.

## Spec Change Log

## Review Triage Log

Quick pass: 0 high, 3 medium, 4 low, 0 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| `rpcn-author__existing_file` isn't in the committed eval record, and the README count is stale | medium | patch | Confirmed: the scenario was added after the eval run, during the matrix audit. The README count was updated, and the final eval run covers the scenario. |
| Nothing committed proves "lints clean on both binaries": `run_evals` never sets `RPCN_TEST_BINARIES` | medium | patch | Confirmed. `run_evals` now passes the pinned cached binaries, and raises SetupError when one is missing. |
| A headless run with an unlisted component is forced to `complete` | medium | patch | Confirmed in the Status block rule. A missing component is now `blocked` (AD-8 "required input is missing"). |
| `## Next` has no situation for an existing file or a binary error | low | patch | Confirmed against AD-9. Bullets added. |
| `rpcn-author__npx_miss` lacks `no_cd = true` | low | patch | Confirmed. Added. |
| `ShippedAuthorScenarioTests.NAMES` omits `existing_file` | low | patch | Confirmed. Added. |
| `existing_file` doesn't assert a non-empty `open_questions` | low | reject | Real. But `check_status` only compares exact values, so the fix is a new runner feature, while `blocked` and `unchanged` already pin the behaviour that matters. |
| The AD-11 deferred note doesn't name the new Kafka Connect negative | low | defer | A deferred-work entry was added. It only matters when AD-11's scan lands. |

## Design Notes

- **Why the runner lints on every binary:** the epic asks for "lints clean on 4.100.0 and the newest release". The agent runs on one binary, so the scenario check is the only place to prove the second.
- **Why `.env.example` sits beside the pipeline:** AD-6 says Author's files sit "beside `<name>.yaml`". One `.env.example` per folder is shared by the pipelines in it. Author adds missing names and never removes any.

## Verification

**Commands:**
- `uv run tools/validate_skills.py && uv run tools/sync_shared.py --check`: exit 0, with the warnings as in the acceptance criteria.
- `for t in tools/tests/test_*.py; do uv run $t; done`, and `RPCN_TEST_BINARIES=… uv run tools/shared/rpcn_check/tests/test_rpcn_check.py`: all pass.
- In T: `uv run tests/test_run_scenarios.py`, then a smoke run of the author scenarios at `--runs 1 --no-judge`.
- After committing: `uv run tools/run_evals.py`, and `uv run tools/eval_record_check.py` exits 0.
