---
title: 'Benchmark arms and the first comparison'
type: 'feature'
ticket: '10'
created: '2026-10-29'
status: done
baseline_revision: '6c027ecbe57ed5c3d73f3e07782cebb877a24a1e'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: ['{project-root}/_bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** We can't tell whether `rpcn-test` is any better than what a developer could use today: the `redpanda-data/connect` Claude plugin, the `redpanda-data/skills` plugin, or Claude with no skill at all (R20).

**Approach:** Extend the `rpcn-test-skills` runner with **benchmark arms**. A scenario marked `compare = true` runs the same prompt and fixtures in four arms, each in its own fresh folder:
- `ours`: `rpcn-skills`, installed as in story 6
- `connect-plugin`: the Connect repo's plugin only
- `skills-repo`: the `redpanda` plugin only
- `bare`: nothing installed

Every arm is scored with the same arm-neutral checks, and one blind quality judgement. The runner writes a comparison table with a winner.

## Boundaries & Constraints

**Always:**
- **Installing the benchmark sets:** whole and unchanged, the way their own READMEs install them, as Claude Code plugins with `--plugin-dir`:
  - `connect-plugin`: `/home/aleksejjurcenko/projects/redpanda-replicator/v4.112.0/connect/.claude-plugin/plugins/redpanda-connect`, recorded at commit `f15e3064a4e4aa4edc47f3b0f87c53d1572189fc`
  - `skills-repo`: `/home/aleksejjurcenko/projects/skills`, recorded at commit `a4562333b774d963066e11dfa1282646b8490550`

  The paths and the expected commits live in `arms.toml` in `rpcn-test-skills`. At startup the runner reads each clone's `HEAD`, records it in `results.json`, and exits 2 if a path is missing. A `HEAD` that differs from the recorded commit is only a warning. Nothing from these repos is copied into either of our repos.
- **Isolation:** every arm keeps story 6's isolating flags. `bare` and the plugin arms install nothing through `npx`.
- **One prompt for all arms:** each arm gets the same prompt and the same copy of the fixtures. It's a neutral request, the way a developer would phrase it, with no skill names.
- **Arm-neutral checks** (`[compare]` in `expect.toml`):
  - **`errors_found`:** how many of the scenario's known errors the final reply names. Each error is a `[[compare.errors]]` entry with `id` and `any` (case-insensitive substrings, any of which counts). Score: 0..N.
  - **`grounded`:** whether the arm ran the Redpanda Connect binary, meaning any Bash call containing `rpk connect` or `redpanda-connect`, or our `rpcn_check.py`.
  - **`unchanged`:** the fixture files are byte-identical after the run.
  - **`turns`, `cost`, `time`**, from the stream.
- **Quality judgement:** one extra headless Claude call per comparison scenario (`--judge`, on by default).
  - It sees the prompt, the original fixture and the four arms' final replies, labelled A–D in a fixed random order recorded in the results, with the arm names hidden.
  - Its rubric covers correctness of each diagnosis, quality of each fix, and clarity.
  - It returns JSON `{"ranking": ["B","A","D","C"], "notes": {...}}`. The runner validates it and maps it back to the arm names.
- **The winner:** the highest mean `errors_found` over the runs. Ties go to the best mean judge rank, then the lowest mean cost. A run with `unchanged` failed scores 0 for `errors_found`, because the arm edited the user's file.
- **Results:** `results.json` gets a `comparison` section per scenario (per-arm means and per-run values, judge ranking and notes, and the winner). stdout gets a table with columns `arm`, `errors_found`, `grounded`, `unchanged`, `judge rank`, `turns`, `cost`, `time`, and a `winner:` line.
  - Exit codes: 0 when every arm ran (a lost comparison isn't a failure), 1 if an arm's runs crash or time out, 2 for setup errors.
- **Pass checks stay separate:** a `compare = true` scenario still runs its normal pass checks, but only in the `ours` arm.
- **The first comparison scenario:** `scenarios/rpcn-test__compare_lint/`.
  - The fixture is `multi_error.yaml`, the same 4-error file story 6 already verified on 4.100.0 and 4.115.0.
  - The prompt: "Check `multi_error.yaml`. Tell me what is wrong and how to fix each problem."
  - Its `[[compare.errors]]` entries are the 4 lint errors: `mapingg`, the missing `mapping`, the Bloblang `this.`, and `codecc`.
  - **Decision (planning):** not seeded from the Connect plugin's `tests/fixtures`. Those hold only descriptions, Bloblang transforms and search queries, with no broken configs to lint.
- **Live progress:** arms print `[<scenario>/<arm> run <i>/<n> +<sec>s] …`, and the judge prints `judge: <ranking>`.
- **Unit tests:** `tests/test_run_scenarios.py` gains tests for `arms.toml` and `[compare]` validation, error matching, `grounded` detection, judge-output parsing and mapping (valid, invalid JSON, a missing label, a duplicate), and winner tie-breaking. No Claude calls.
- **Commit:** in the `rpcn-test-skills` repo, locally only.

- **Decision (user, 2026-10-29), option (a):** comparison runs use the same `allowed_tools` for all four arms: `Bash(rpk *)`, `Bash(redpanda-connect *)`, `Bash(uv run *)`, `Bash(python3 *)`, `Bash(jq *)`, `Bash(bash *)`, `Bash(./*)`, `Bash(ls *)`, `Bash(cat *)`, `Read`, `Write`, `Edit` and `Skill`. They go in the scenario's `expect.toml`. Non-comparison scenarios keep their own lists.

**Never:**
- changing the benchmark sets or copying their files
- giving one arm a different prompt, fixtures or limits
- letting the judge see the arm names
- installing all three sets together
- changing `rpcn-test` to win (findings become improvement stories, R20)

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Full comparison | `compare = true`, 3 runs, judge on | 4 arms × 3 runs, then 1 judge call, a table and a winner line | — |
| Missing clone | an `arms.toml` path doesn't exist | exit 2 before any run, naming the arm | — |
| Clone moved | `HEAD` differs from the recorded commit | a warning line, with the actual `HEAD` recorded | — |
| Arm edits the file | `unchanged` fails in a run | `errors_found` is 0 for that run, with the reason shown | — |
| Tie | equal `errors_found` | decided by judge rank, then by cost | — |
| Judge output invalid | not JSON, or not a permutation of A–D | the comparison has no judge rank, the winner comes from `errors_found` and cost, a warning is shown | — |
| `--no-judge` | flag set | no judge call, and no rank column | — |
| Arm crashes | a timeout or non-success result | that run counts as failed, and the arm's means use the runs that finished | exit 1 |
| Not a comparison | `compare` absent | story 6 behaviour, unchanged | — |

</frozen-after-approval>

## Code Map

- **`rpcn-test-skills/run_scenarios.py`** (commits `f402499` and `a7bdecd`):
  - **Reuse:** `run_once` (folder setup, `git init` per run folder, `npx` install, `run_claude` with stream parsing and live progress), the check functions, `validate_expect`, `make_out_dir` and the results writer.
  - **Add:** an arm abstraction. For `ours` it installs with `npx`. For a plugin arm it adds `--plugin-dir <path>` to the Claude command. For `bare` it installs nothing.
  - **Judge:** a `run_judge`, built the same way as `run_claude`, with no tools allowed.
  - **Untouched:** the story 6 checks.
- **The Claude command** is built around line 541: `--setting-sources project,local`, then `--allowedTools`, and so on. The plugin arms add `--plugin-dir` there.
- **`connect-plugin`:**
  - Its skills run bash and python3 scripts by relative path and need `jq`, which is installed at `/usr/bin/jq`.
  - It is invoked as `redpanda-connect:<skill>`.
  - Under the story-6 narrow rule its scripts can't run, which is why the comparison list is wider.
- **`skills-repo`:** a single `redpanda` plugin with 32 skills, including `connect` and `connect-debugging`. It is invoked as `redpanda:<skill>`.
- **Turns:** per story 6, `ours` takes about 16 turns on `multi_error.yaml`.

## Tasks & Acceptance

**Execution:**
- [x] `rpcn-test-skills/arms.toml` -- arm names, kinds (`skills`, `plugin` or `none`), paths and recorded commits -- the benchmark sources
- [x] `rpcn-test-skills/run_scenarios.py` -- arms, `[compare]` checks, the judge, the winner rule, the comparison table and results, and the progress prefix -- R20
- [x] `rpcn-test-skills/scenarios/rpcn-test__compare_lint/{prompt.md,expect.toml,fixtures/multi_error.yaml}` -- the first comparison -- the R20 evidence
- [x] `rpcn-test-skills/tests/test_run_scenarios.py` -- the new tests listed in Boundaries -- runner correctness
- [x] `rpcn-test-skills/README.md` -- the benchmark section: arms, scoring, winner rule and costs -- usage

**Acceptance Criteria:**
- Given `uv run run_scenarios.py --scenario rpcn-test__compare_lint`, when it finishes, then all four arms have run 3 times each, a judge ranking is recorded, and the table and `winner:` line are printed and saved in `results.json`.
- Given `uv run tests/test_run_scenarios.py`, then every test passes, including story 6's.

## Implementation Notes

- **Arms** live in `run_scenarios.py` as `Arm` (from `arms.toml`, validated by `validate_arms`, clones checked by `resolve_arms`). `run_once` takes an optional arm: `ours` installs with `npx` and runs the pass checks, a plugin arm adds `--plugin-dir`, `bare` installs nothing. Every arm run gets `compare` scores. Folders: `runs/<ts>/<scenario>/<arm>/run-<i>/`.
- **`grounded`** matches `rpk connect`, `redpanda-connect` as a command word (so a path such as `.../plugins/redpanda-connect/skills/...` doesn't count) and `rpcn_check.py`. A binary call made only inside a script the arm ran (the Connect plugin's `format-component-fields.sh`) is not seen.
- **`grounded` ignores denied calls:** Bash calls listed in the result event's `permission_denials` don't count (the smoke run showed `bare` and `skills-repo` issuing compound `cd …; rpk connect lint` calls that `allowed_tools` denied).
- **`time`** in the comparison is Claude's run time (`claude_duration_s`), so `ours` isn't charged for the `npx` install.
- **Judge:** `run_judge` uses `run_claude` with the prompt on stdin (`judge.prompt.md`), `--tools ""`, `--disable-slash-commands`, `--max-turns 2`, in its own empty git folder. Each label carries every finished run's reply for that arm, so the single call yields one rank per arm, used as its "mean judge rank".
- **Crashes:** a run with any error (git init, install, timeout, non-success result) is not finished; the means use finished runs only, and any crashed arm run makes the exit code 1.
- **`--plugin-dir` under `--setting-sources project,local`:** verified to load both benchmark plugins (init lists `redpanda-connect:*` and `redpanda:*` skills).

## Plan Change Log

- **2026-10-29, `[[compare.errors]]` ids:** the plan named `mapingg`, a missing `mapping`, `this.` and `codecc`, but the story-6 `multi_error.yaml` it says to reuse (and verified on both pins) has `not_a_field` (line 5), `root = this.` (line 9), `bogus_option` (line 13) and `wrong_key` (line 18). The fixture is kept as the source of truth, and the four entries are that file's real lint errors.
- **2026-10-29, how a scenario is marked:** TOML can't hold both `compare = true` and the `[[compare.errors]]` table under the same key, so the marker is `[compare] enabled = true`. "`compare` absent" (or `enabled = false`) keeps story-6 behaviour.

- **Full comparison (orchestrator, 2026-10-29),** in `runs/20261029-111007`. 4 arms × 3 runs plus the judge, exit 0.

  | arm | errors_found | grounded | unchanged | judge rank | turns | cost | time |
  |---|---|---|---|---|---|---|---|
  | ours | 4.00/4 | 3/3 | 3/3 | 1 | 16.7 | $0.29 | 43 s |
  | connect-plugin | 4.00/4 | 3/3 | 3/3 | 3 | 3.7 | $0.09 | 16 s |
  | skills-repo | 4.00/4 | 3/3 | 3/3 | 2 | 7.3 | $0.22 | 27 s |
  | bare | 4.00/4 | 3/3 | 3/3 | 4 | 4.7 | $0.09 | 38 s |

  **Winner:** ours, decided by judge rank because every arm tied on errors found. The judge cost $0.11.
  - **Judge's notes:** ours "avoids listing component fields from memory" and confirms that its fixes lint clean. Every other arm invented fields; connect-plugin and bare did so the most.
  - **Observed:** the comparison table and the `winner:` line are printed twice.
- **After the review fixes:** rpcn-test-skills commit `fb88bbf`, 108 unit tests pass. The first comparison's judge rank came before redaction, so it may have been influenced by names in the reply text. Re-judging the saved replies is the follow-up offered to the user.
- **Blind re-judge** of the saved replies, with redaction (user chose option (a)). These are rpcn-test-skills commits `ec9bcbe` (`--rejudge`) and `91f8497` (one retry on invalid judge JSON), with 116 tests.
  - **First attempt** (`rejudge-20261029-141306.json`): the ranking was valid and identical (ours > skills-repo > connect-plugin > bare), but the JSON was malformed, so the runner fell back to cost. That's what prompted the retry fix.
  - **After the fix** (`rejudge-20261029-142111.json`): exit 0, the same ranking, `winner: ours (tie on errors_found, judge rank)`, decided under a fully blind judge.

## Review Triage Log

**Pass 1 (quick):** 5 → patch (grounding counts as one entry), 5 rejected.

| # | Finding | Verdict | Route | Evidence |
|---|---|---|---|---|
| 1 | The comparison table and `winner:` line print twice | low | patch | Two print sites in `main()`. It was seen in `runs/20261029-111007`. |
| 2 | `grounded` counts paths that end in `/redpanda-connect` | medium | patch | The connect-plugin arm's own folder name matches. It shares a root cause with #3. |
| 3 | `grounded` counts `cat`/`echo` of `rpcn_check.py` and `rpk connect` | medium | patch | The regex isn't anchored to the command being run. The fix anchors it after a command separator. |
| 4 | Denied calls count when there is no result event | low | reject | Only unfinished runs are affected, and they're left out of the arm's means. |
| 5 | Arm identity leaks to the judge through the reply text | medium | patch | Replies name `rpcn-test`, `rpcn_check.py` and plugin prefixes, which goes against the "judge never sees arm names" rule. The fix is a fixed redaction list. The rank in the first comparison may be affected, and re-judging is possible from the saved replies. |
| 6 | The judge-invalid case shows a `judge rank` column of `-` | low | reject | `-` already means no rank. Cosmetic. |
| 7 | `decided_by` mentions judge rank when no rank was compared | low | patch | A direct string correction. |
| 8 | The judge folder's `git init` return code is ignored | low | patch | Make it match `run_once`. |
| 9 | The stdin file handle leaks if `Popen` raises | low | reject | `claude` is checked before starting. The fix adds structure for an unreachable case. |
| 10 | Acceptance criterion 1 says "saved in results.json", but the table text isn't saved | low | reject (false) | The comparison data (`arms`, `judge`, `winner`, `decided_by`) is saved. The table is a view of that data. |

## Verification

- **2026-10-29, implementer:** `uv run tests/test_run_scenarios.py`: 103 tests, all pass. One smoke run, `uv run run_scenarios.py --scenario rpcn-test__compare_lint --runs 1` (`runs/20261029-110653`): exit 0, all four arms ran, every arm scored `errors_found` 4/4, `grounded` and `unchanged`. Judge ranked ours > connect-plugin > skills-repo > bare, so the winner is `ours` (tie on errors_found, decided by judge rank). Cost about $0.65 in all. Neither plugin arm invoked one of its skills; both linted with `rpk connect lint` directly. The full 3-run comparison is left to the orchestrator.

**Who runs what:** the implementer runs only the unit tests and at most one `--runs 1` smoke run of the comparison scenario. The orchestrator runs the full 3-run comparison, with live progress shown to the user.

**Commands** (from `rpcn-test-skills`):
- `uv run tests/test_run_scenarios.py` -- expected: all pass
- `uv run run_scenarios.py --scenario rpcn-test__compare_lint` -- expected: 12 arm runs plus 1 judge call, a table, a `winner:` line, and exit 0. Cost about $4–5.
