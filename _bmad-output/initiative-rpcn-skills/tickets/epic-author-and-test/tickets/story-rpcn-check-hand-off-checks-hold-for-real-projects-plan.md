---
title: 'rpcn_check hand-off checks hold for real projects'
type: 'feature'
ticket: '2'
created: '2026-11-05'
status: 'built'
baseline_revision: 'f8c3a10c7f398caba1a18a4a5268b39db69262d3'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Four gaps from the epic 1 retrospective (D1, F6–F8, and the deferred subfolder-scenario check) make `rpcn_check`'s hand-off checks wrong on real projects. Epic 2's readers will soon depend on `pipeline_ready`, so these need fixing first.
- **Lint:** lint counts any extra output line as an error, even on a clean exit 0. An `rpk` update notice is enough to make a clean pipeline fail.
- **`.yml`:** a `.yml` pipeline is never `pipeline_ready`.
- **Shared resources:** the skill only knows `<name>.resources.yaml`, so a shared resources file is neither linted nor hashed.
- **Empty inputs:** a test report with no pipeline input comes back `ready`.
- **Scenarios:** they can't catch the subfolder bug's real causes, an agent that `cd`s or a report that records `pipes/` paths.

**Approach:**
- **`rpcn_check.py`:**
  - Ignore unparsed lint lines on exit 0.
  - Accept `<pipeline>.yaml` or `.yml`.
  - For `test-report`, require the first input to be the pipeline file.
- **`rpcn-test` and the formats:** name shared resources files.
- **`rpcn-test-skills`:** add `no_cd` and `bare_inputs` scenario checks, used by both subfolder scenarios.
- **Evals:** sync the copies and run the evals.

## Boundaries & Constraints

**Always:**
- Keep the schema-1 envelope and exit codes 0, 1 and 2.
- Keep today's lint behaviour whenever the binary exits non-zero, including fileless errors.
- Keep the `0 errors.` behaviour for matched lint lines with exit 0: they still give exit 1, as `test_output_with_exit_zero_is_failure` asserts.
- Update `SCHEMA.md`, `handoff-header.md` and `test-report-format.md` together with the code.
- Change shared files only under `tools/shared/`, then run `sync_shared.py`.

**Never:**
- Change `parse_run_lint_errors`, which serves `run`.
- Change the `.yaml` default anywhere it is right today.
- Touch any other subcommand's behaviour.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Notice, exit 0 | lint exits 0, and stderr has an `rpk` notice | ok, exit 0, `error_count` 0 | — |
| Notice plus error, exit 0 | exit 0, a notice and one `file(l,c) msg` line | exit 1, with only the matched error | — |
| Unparsed, exit 1 | exit 1 and an unmatched line | as today: a fileless error, exit 1 | — |
| `.yml` pipeline | a report for `orders` whose first input is `orders.yml`, with verdict pass | `ready`, and `pipeline_ready: true` | — |
| No pipeline input | a `test-report` with `inputs: []`, or a first input that isn't `<pipeline>.yaml`/`.yml` | `ready: false`, exit 1, with an error on the `inputs` line | — |
| Shared resources | the pipeline plus `resources.yaml` in inputs, and the resources file then changes | not ready (input changed) | — |
| `no_cd` | a scenario run where a Bash segment starts with `cd` | the `no_cd` check fails, naming the command | denied calls are ignored |
| `bare_inputs` | a `[[report]]` with `bare_inputs = true`, and the pipeline input recorded as `pipes/orders.yaml` | the check fails, naming the input; a `../resources.yaml` second input passes | — |

**Decision (2026-11-05, user):** report inputs are paths relative to the report's folder. The pipeline is always first and always a bare file name. Other inputs, such as a shared `../resources.yaml`, may be relative paths. `bare_inputs` checks the pipeline input only.

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`. `T` = `rpcn-test-skills`, which starts at `0ae3995923899cc65123b56b5ad122d6c246c938` (local only).

- **`R/tools/shared/rpcn_check/rpcn_check.py`:**
  - `_LINT_LINE_RE` is at 47.
  - `parse_lint_output` (245-278) turns unmatched lines into fileless errors. Add a matched-only mode, and use it from `cmd_lint` (313-370, call at 356) when `returncode == 0`.
  - `_check_handoff` (531-597): `pipeline_file` is built at 583, and the ready decision is at 580. Accept `.yaml`/`.yml`. For `artifact == "test-report"`, require `inputs[0]` (normpath) to be the pipeline file, else report an error on `key_lines["inputs"]`.
- **`R/tools/shared/rpcn_check/tests/test_rpcn_check.py`:**
  - `LintTest` is at 346; use `fake_lint_rpk`/`write_exe` (41).
  - The `HashTest` `handoff()` helper (620) defaults to `inputs: []` for a test-report. Give the default a pipeline input, or audit every HashTest that expects exit 0.
  - `test_verdict_without_pipeline_input` (941-949) flips to exit 1. Add a `.yml` case beside 902.
- **`R/tools/shared/rpcn_check/SCHEMA.md`:** lint parsing and exit codes at 109-127; the `ready`/`pipeline_ready` rows at 195-196.
- **`R/tools/shared/formats/handoff-header.md`** (4, 23, 85-93, 110) and **`test-report-format.md`** (4, 20-21, 78, 82):
  - `.yaml` or `.yml`.
  - The test-report "pipeline first" rule is now checked by the script.
  - Any resources file counts as an input.
- **`R/skills/rpcn-test/SKILL.md`** (Steps 2, 3, 5: lines 44-82): name a shared resources file (pass it with `--resources` and hash it after the pipeline), and say the pipeline may be `.yml`.
- **`R/skills/rpcn-test/`:** `scripts/rpcn_check.py` and `references/*.md` are synced copies (`shared.txt`). Run `uv run tools/sync_shared.py` after the edits.
- **`T/run_scenarios.py`:**
  - `validate_expect` (74-182): the top-level keys are at 84-86, so add `no_cd` (bool). The `[[report]]` fields are at 163-170, so add `bare_inputs` (bool) to the required-one-of set.
  - `StreamState.bash_commands` (680-685) drops denied calls. Reuse the segment helpers `_QUOTED_RE`/`_SEGMENT_SPLIT_RE` (484-485) to find a `cd` segment.
  - `run_checks` (1277-1305) runs `hash --check` at 1291-1296. Read `data.inputs[].file` there for `bare_inputs` (no `/` or `\`).
- **`T/tests/test_run_scenarios.py`:** ExpectTests 108, CheckTests 220 (reports 246-276), GroundedTests 743.
- **`T/scenarios/rpcn-test__lint_subfolder*/expect.toml`:** add `no_cd = true` and `bare_inputs = true` to the `[[report]]`.

## Tasks & Acceptance

**Execution:**
- [x] `R/tools/shared/rpcn_check/rpcn_check.py` and its tests: lint on exit 0, `.yml`, pipeline-first for test-report.
- [x] `R/tools/shared/rpcn_check/SCHEMA.md`, `R/tools/shared/formats/handoff-header.md`, `test-report-format.md`: document the new behaviour.
- [x] `R/skills/rpcn-test/SKILL.md`: shared resources files and `.yml`. Then `uv run tools/sync_shared.py`.
- [x] `T/run_scenarios.py` and its tests: `no_cd` and `bare_inputs`.
- [x] `T/scenarios/rpcn-test__lint_subfolder*/expect.toml`: use both checks.
- [x] `T/README.md`: document both checks.

**Acceptance Criteria:**
- **Given** the subfolder scenario with both new checks, **when** it runs against the old skill (`git:0fd10ca`), **then** at least one run fails on `no_cd` or `bare_inputs`, and against the current skill all 3 runs pass.
- **Given** the repo, **when** `uv run tools/run_evals.py` runs, **then** it passes and writes a record for the new skills hash, and the `rpcn_check` tests pass on 4.100.0 and 4.115.0 in CI.

## Implementation Notes

- **Built as planned.** Test counts: `rpcn_check` 142 on 4.100.0 and 4.115.0, and `run_scenarios` 144. The other suites are green.
- **The new checks catch the old skill.** `git:0fd10ca` failed `no_cd` in 5 of 6 subfolder runs (`T/runs/20261105-120620`). The current skill passes 6 of 6 (`T/runs/20261105-120625`). `bare_inputs` never failed on a real agent run: the old skill still recorded bare names, so `no_cd` is the check that bites.
- **First record superseded.** The record `2026-11-05-ab5d28984931.json` passed ($6.49) but was dirty, because it was run before the commit (retrospective lesson L2). The review patches then changed `skills/`, so it was deleted unused. The evals re-run from the committed tree.
- **Size:** `rpcn-test` SKILL.md is now about 1,574 tokens. That's a warning only, and story 2.3 trims it under 1,200.
- **Change:** `pipeline_matches` now looks only at `inputs[0]`, consistent with the pipeline-first rule.

- **Final record:** `evals/results/2026-11-05-1d26594d55bb.json` passed with `dirty: false`, at $6.75. The runner tests ran first, the gate passed with accuracy 1.0, and all 5 scenarios passed 3/3.

## Review Triage Log

Quick pass: 0 high, 2 medium, 4 low, 0 false, 0 maybe-false.

| Finding | Verdict | Route | Evidence / action |
|---|---|---|---|
| SKILL.md command templates still hardcode `.yaml` | medium | patch | A `<pipeline>` placeholder (the real extension) is now used in every template, and the resources fallback is paired with it. |
| SKILL.md never says to convert hashed paths to paths relative to the report | medium | patch | Step 5 now states the rule, with two examples (`../resources.yaml`). |
| `bare_inputs = false` validates but checks nothing | low | patch | It is now rejected, with tests. |
| `no_cd` misses `&`, `{ cd`, `pushd` | low | patch | New split and match regexes, with tests for each and an updated README. `$(cd …)` stays out of scope (rare, and covered by the bare-name rule). |
| The `pipeline_ready` row says "an input", while the code now requires the first one | low | patch | SCHEMA row updated, and `pipeline_matches` aligned to `inputs[0]`. |
| handoff-header says "all four hold" for every artifact | low | patch | Rule 4 is now for test reports only, and re-synced. |

## Verification

**Commands:**
- `uv run tools/shared/rpcn_check/tests/test_rpcn_check.py`, with `RPCN_TEST_BINARIES` set to both cached binaries: all pass.
- `uv run tools/sync_shared.py --check`, `uv run tools/validate_skills.py`: exit 0.
- In `T`: `uv run tests/test_run_scenarios.py`: all pass. Then `uv run run_scenarios.py --source git:<0fd10ca full sha> --scenario rpcn-test__lint_subfolder --runs 3 --no-judge`, which should fail at least once, as evidence that the checks catch the old skill.
- `uv run tools/run_evals.py`: passes, and writes the record.
