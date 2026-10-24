---
title: 'Lint-only rpcn-test explains errors and writes a test report'
type: 'feature'
ticket: '5'
created: '2026-10-23'
status: done
baseline_revision: '650bf257a5a0d2cc730c7969eba2562cbe9df192'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md', '{project-root}/tools/shared/formats/handoff-header.md', '{project-root}/tools/shared/formats/test-report-format.md', '{project-root}/tools/shared/rpcn_check/SCHEMA.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `rpcn-test` can only report the binary. A developer can't yet ask it to check a pipeline and get the cause and fix for each error, or a test report that other skills can trust.

**Approach:** Extend `skills/rpcn-test/SKILL.md` into the lint-only test skill. It:
1. checks the binary
2. runs `rpcn_check.py lint`
3. explains every error with its cause and a proposed fix, using a new hand-written reference loaded only when there are errors
4. writes `<name>.test-report.md` in `test-report@1`, with inputs hashed through `rpcn_check.py hash`
5. ends with a Next step, and when headless, with the AD-8 status block

The lint guidance is copied and adapted from `redpanda-data/skills`, and recorded in `SOURCES.md`.

## Boundaries & Constraints

**Always:**
- **No direct binary calls:** every binary call goes through `uv run ${CLAUDE_SKILL_DIR}/scripts/rpcn_check.py …`, keeping the existing fallback line. The skill never runs `rpk connect` directly.
- **No edits to the pipeline:** the skill never edits the pipeline YAML (AD-6). Fixes go into the report's Proposed changes as diffs, and the reply shows them. The developer, or rpcn-author later, applies them.
- **Lint inputs:** lint the pipeline the user names. Pass `--resources` for `<name>.resources.yaml` when it exists, and `--env-file` only when the user names one.
- **Errors:** for each error, give its file, line and column, the cause, and the fix. The script's `errors` are the only source of errors; the skill never invents or drops one.
- **The report** follows `test-report@1`:
  - **Header:** `status: ready` once written. `inputs` holds the pipeline first, then any resources file, hashed with `rpcn_check.py hash` before linting. `rpcn_version` comes from `binary`.
  - **Summary:** the verdict is `pass` only with 0 lint errors.
  - **Lint:** the error table.
  - **Bloblang samples, Unit tests and Design check:** `Not run.`, with the reason "not in this version of rpcn-test".
  - **Proposed changes:** one diff per fix.

  After writing, the skill runs `rpcn_check.py hash --check` on the report and requires `ready: true`.
- **Environment errors:** when `binary` or `lint` exits 2, the skill writes no report and shows the script's errors with the fix from the existing binary guidance.
- **`references/lint-errors.md`** is hand-written and owned by the skill. For each common message pattern it gives the cause and the fix, plus what lint does and doesn't catch. It's adapted from `redpanda-data/skills` `skills/connect-debugging/references/lint-and-validate.md` (commit `a4562333b774d963066e11dfa1282646b8490550`, Apache-2.0), with one row added to `SOURCES.md`. Its message patterns must match the verified `rpcn_check lint` output (`field X not recognised`, `field X is required`, `unable to infer output type, multiple candidates …`, `component X is deprecated`, YAML syntax errors, Bloblang parse errors such as `required: expected query`, `required environment variables were not set`).
- **The description** follows AD-9 and covers both jobs, binary check and pipeline lint, with quoted trigger phrases and "Not for writing, designing or deploying pipelines." It stays within 1024 characters, and SKILL.md stays around 800 tokens (warn above 1,200).
- **The Next step:** after applying the proposed changes, re-run rpcn-test. With 0 errors, there's nothing to fix.

- **Decision (user, 2026-10-23), option (a):** in a headless run, lint errors give `status: "complete"` with `checks.lint: "fail"`. `blocked` is only for a run that couldn't test: no or too-old binary, a missing pipeline, or the script exiting 2.

**Never:**
- running Bloblang samples, unit tests or the design check (epic 2)
- editing `rpcn_check.py` or the format docs
- shipping fixture pipelines inside the skill folder
- a description that names a sibling skill that doesn't exist yet

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Clean pipeline | a pipeline that lints clean | report `ready`, verdict `pass`, Lint `0 errors.`, no Proposed changes | — |
| Broken pipeline | `multi_error.yaml` (4 errors) | 4 explained errors, 4 diffs, report `ready` with verdict `fail`, and the fixed file lints clean | — |
| Deprecated component | a `kafka` input | cause "deprecated", fix "use `redpanda`" | — |
| Resources file | `<name>.resources.yaml` beside the pipeline | passed with `--resources` and listed in `inputs` | — |
| No binary | nothing found | no report, binary fix guidance | script exit 2 |
| Missing pipeline | the named file doesn't exist | no report, the error is shown | script exit 2 |
| Headless broken | an unattended run on the broken pipeline | no questions asked, ends with exactly one status block, `complete` with `checks.lint: "fail"` | — |
| Binary-only request | "check my Redpanda Connect binary" | reports the binary only, no report written | — |

</frozen-after-approval>

## Code Map

- **`skills/rpcn-test/SKILL.md`** (current, 435 words):
  - **Keep:** the headless rules, Step 1 (binary), the exit-2 guidance, the `RPCN_BINARY` note, and the status block shape.
  - **Add:** the lint, explain, report and Next steps.
  - **Rewrite:** the description.
- **`skills/rpcn-test/references/`** already holds the synced `handoff-header.md`, `design-format.md` and `test-report-format.md`. Add the skill-owned `lint-errors.md`; `sync_shared` doesn't manage it, because it isn't in `shared.txt`.
- **`rpcn_check.py` calls:** `lint <file> [--resources f] [--env-file f]` returns errors sorted, with exit codes 0, 1 and 2. `hash <files>` and `hash --check <report>` are the contract for inputs and readiness. See `SCHEMA.md`.
- **Fixtures for manual and eval checks:** `tools/shared/rpcn_check/tests/fixtures/` (`valid.yaml`, `multi_error.yaml`, `deprecated.yaml`, `bad_yaml.yaml`, `env_var.yaml`).
- **Example report:** the filled example in `test-report-format.md`.
- **`SOURCES.md`:** an empty table with the header `File | Source | Licence | Notes`.
- **The source for `lint-errors.md`:** `/home/aleksejjurcenko/projects/skills/skills/connect-debugging/references/lint-and-validate.md` (215 lines; sections "What lint catches" and "What lint does NOT catch"). Adapt only what fits. Skip its CLI-flag advice that `rpcn_check` fixes, and its dry-run and CI sections.

## Tasks & Acceptance

**Execution:**
- [ ] `skills/rpcn-test/SKILL.md` -- the new description, and the steps (binary, lint, explain from `references/lint-errors.md` only when there are errors, write and verify the report, Next, headless block) -- the lint-only skill
- [ ] `skills/rpcn-test/references/lint-errors.md` -- the message pattern → cause → fix table, plus what lint does and doesn't catch -- error knowledge
- [ ] `SOURCES.md` -- a row for `skills/rpcn-test/references/lint-errors.md`, with source path, commit, Apache-2.0 and "adapted" -- licence record

**Acceptance Criteria:**
- Given `multi_error.yaml` copied to a scratch folder, when Claude Code runs headless with this plugin (`claude --plugin-dir <repo> -p "lint <scratch>/multi_error.yaml"`), then the reply explains 4 errors with fixes, `<scratch>/multi_error.test-report.md` exists, `hash --check` reports it `ready` with verdict `fail`, and the reply ends with one valid AD-8 status block.
- Given the proposed diffs applied to that copy, when `rpcn_check.py lint` runs, then it exits 0.
- Given `valid.yaml`, when the same headless run happens, then the report's verdict is `pass`, and `hash --check` reports `pipeline_ready: true`.

## Implementation Notes
- **Verification (orchestrator, 2026-10-23), run after the implementer was stopped:** three headless `claude --plugin-dir` runs, with progress shown as they ran.
  - **Broken pipeline:** `multi_error.yaml` passed in 52 s ($0.40). It gave 4 errors with diffs, the report is `ready` with verdict `fail`, and the reply ended with a `complete` status block where `lint` is `fail`.
  - **Proposed diffs:** applied with `patch`, the file lints clean on 4.100.0 and 4.115.0.
  - **Clean pipeline:** `valid.yaml` passed in 29 s ($0.30). Verdict `pass`, `pipeline_ready: true`, `lint` `pass`.
- **Re-check after the review fixes:** the headless broken-pipeline run passed again (51 s, $0.42). The report is `ready` with verdict `fail`, and the status block is `complete` with `lint` `fail`.

## Plan Change Log

## Review Triage Log

**Pass 1 (quick):** 10 → patch. The orchestrator applied them, because the implementer had been stopped.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | SKILL.md is over its size target (718 words) | medium | patch | AD-9 sets about 800 tokens. Trimmed to about 900 tokens in the body (4.4 KB including the description), under the 1,200 warning. |
| 2 | The `${CLAUDE_SKILL_DIR}` fallback breaks with "run from the pipeline folder" | medium | patch | The fallback is now "replace it with the absolute path of the folder that holds this SKILL.md". |
| 3 | `lint-errors.md` names `kafka` and `kafka_franz`, which AD-11's deprecated scan will flag | low | patch | The row is now generic: use the successor its documentation names. |
| 4 | The rename advice was wrong for `kafka_franz`, and the field shapes differ | medium | patch | Wrong guidance removed. The row now says to check each field against the successor and re-lint. |
| 5 | The `expected <type> value` row was never verified | low | patch | Row deleted, because the plan requires every pattern to be verified. |
| 6 | The unset-variable note contradicts the `env_var.yaml` fixture | medium | patch | Rewritten: lint doesn't check unset variables, and the problem shows up at run time. |
| 7 | "Positions are in the pipeline file" isn't always true | low | patch | Now names the resources file and the null case. |
| 8 | The fix check in Step 4 leaves out `--resources` and `--env-file` | medium | patch | Now lints with the same flags as Step 3. |
| 9 | The status-block template had run-specific values baked in | medium | patch | It now uses `<complete\|blocked>` and `<pass\|fail\|skipped>`, with `artifacts: []`. |
| 10 | `hash --check` failing had no way out, so a headless run could loop | medium | patch | One retry, then `status: draft` and `blocked` when headless. |

## Verification

**Commands:**
- `uv run tools/sync_shared.py --check` -- expected: exit 0 (the synced references are untouched)
- `wc -w skills/rpcn-test/SKILL.md` -- expected: about 600 words or fewer (around 800 tokens)
- the acceptance criteria's headless runs, in a scratch folder, using `claude --plugin-dir`

**Manual checks:**
- every message pattern in `lint-errors.md` appears in real `rpcn_check lint` output on the fixtures, run on 4.100.0 or 4.115.0
