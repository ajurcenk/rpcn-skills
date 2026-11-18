---
title: 'Benchmark Author and Test against the other skill sets'
type: 'feature'
ticket: '12'
created: '2026-11-13'
status: 'built'
baseline_revision: 'e3aa77f3d10cabf3e5bb5ae6a11cd899fbce9280'
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

**Problem:** epic R12 needs a winner for one Author and one Test comparison across the four arms (`ours`, `connect-plugin`, `skills-repo`, `bare`). The only comparison so far is epic 1's `rpcn-test__compare_lint`. Every arm scored 4/4 there, and the judge decided it. Its score is "errors named in the reply", which can't score a written pipeline.

**Approach:**
- **Author comparison:** a new scenario, `rpcn-author__compare_write`. Every arm gets the same plain request to write a pipeline. The pipeline it writes is scored arm-neutrally on file points:
  - it lints clean on both binaries;
  - a bounded run on fixed input messages gives the expected outputs;
  - it has the DLQ topic the request names.
- **Test comparison:** a failing pipeline every arm must diagnose, scored by the causes its reply names (the existing `[[compare.errors]]`).
- **The runner:** it scores both kinds and picks winners as today: score first, then judge rank, then cost.
- **Recording:** the winners go in the eval record's `compare`. Each scenario another arm wins becomes a new improvement story.

**Decisions (2026-11-13, user):**
- **Test comparison:** a new `rpcn-test__compare_diagnose`. Its pipeline lints clean but fails at runtime (a total that can arrive as a string) and has a mapping bug (cents × 10). Its `[[compare.errors]]` are those two causes. `compare_lint` stays as it is.
- **Run:** the full `run_evals.py --with-compare` on the committed tree, about $55. The eval record's `compare` names each winner.
- **Losses:** this build records each loss and its evidence in Implementation Notes and in the final summary. The user then runs `bmad-agent-po` (Sofia) to add the improvement stories; this build writes no ticket file.

## Boundaries & Constraints

**Always:**
- Every arm gets the same prompt, fixtures and `allowed_tools`, as `compare_lint` does (decision 2026-10-29).
- Plugin arms are used in place, unchanged, at the commit `arms.toml` records.
- Scoring is arm-neutral: the same checks for every arm, run by the runner on both binaries.
- `claude plugin eval` always runs with `--no-publish`.

**Never:**
- Tune our skills to the benchmark in this story (losses become stories).
- Score by our own file formats (a test report, a status block).
- Touch the other arms' repos.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Author arm writes a correct pipeline | the request | every file point scored, e.g. 3/3 | — |
| Arm writes no file, or the wrong path | — | 0 file points | the run still counts as finished |
| Written pipeline fails lint | — | no lint point; run and contains still scored | — |
| Bounded run fails or times out | — | no run point | timeout as in `dry-run.md` |
| Test arm names each cause | failing fixture | each named cause scores 1 | an edited fixture scores 0, as today |
| Arms tie on score | — | judge rank, then cost decides | as `pick_winner` today |
| Another arm wins | results | a new improvement story for that scenario | — |

</frozen-after-approval>

## Code Map

`R` = `rpcn-skills`, `T` = `rpcn-test-skills` (local, baseline `0dcdce7917ced141fbb00b347d1ea539309ff4c8`; leave the untracked `T/orders_benthos_test.yaml` alone).

- **`T/run_scenarios.py`:**
  - `validate_compare` (around line 277) knows only `enabled` and `[[compare.errors]]`. Add `[[compare.files]]`: `{id, file, lint?, run?, contains?}`, where `run` is `{input = [...], expect = [...]}`. Each entry with a `run` table compares per message with JSON-subset matching.
  - `compare_scores` (around line 1271) scores `errors_found` from the reply. Add file points. Keep the field names readable in old `results.json` files, or add `score`/`score_total` and have `pick_winner` (around line 1323) and `summarize_arm` use them, falling back to `errors_found`.
  - `run_once`'s compare block (around line 2048) uses `check_unchanged` on the fixtures. An Author scenario starts with no fixtures, so that passes trivially.
  - Lint and the bounded run reuse what `[[lint]]` and `[[fix]]`'s `dry_run` call (`rpcn_check lint`, `run --bounded --input`), using the R copy of `rpcn_check.py` on every binary in `RPCN_TEST_BINARIES`.
  - `--rejudge` (around line 2345) must still work on old runs.
- **`T/scenarios/rpcn-test__compare_lint/expect.toml`** is the template: a shared `allowed_tools` list, the pass checks that run only in `ours`, and `[compare] enabled = true`. Scenarios run with `rpcn-author__*`'s install, `install = ["rpcn-author"]`.
- **`T/arms.toml`:** the arms are unchanged. Both plugin clones are at their recorded commits (`f15e3064`, `a4562333`).
- **`R/tools/run_evals.py`:** `--with-compare` (line 389) records `{scenario: winner}`. No change is expected.
- **`R/evals/README.md`, `T/README.md`:** document `[[compare.files]]`, the new scenarios, and the cost.

## Tasks & Acceptance

**Execution:**
- [x] `T/run_scenarios.py` `[[compare.files]]` scoring and `pick_winner`, plus tests (each matrix row).
- [x] `T/scenarios/rpcn-author__compare_write/` (prompt, `expect.toml` with `ours`-only pass checks and file points) and `T/scenarios/rpcn-test__compare_diagnose/` (a failing fixture, the two causes as `[[compare.errors]]`, `ours`-only pass checks).
- [x] READMEs.
- [x] After review and commit: `run_evals.py --with-compare` (about $55), commit the `dirty: false` record, and record each winner, the per-arm scores and any loss in Implementation Notes.

**Acceptance Criteria:**
- Given the repo, when `validate_skills`, `sync_shared --check`, all `tools/` suites and T's tests run, then all pass.
- Given `run_evals.py --with-compare`, when it finishes, then it passes, and the record's `compare` names a winner for both scenarios, with each arm's score, judge rank and cost.
- Given a scenario another arm wins, then the loss and its evidence are recorded, for the user to hand to Sofia; no ticket file is written.

## Implementation Notes

- **`[[compare.files]]`** (`T/run_scenarios.py`): `{id, file, lint?, run?, contains?}`, 1 point each. `lint` and
  `run` use R's `skills/rpcn-test/scripts/rpcn_check.py` from `--source` (git source: `../rpcn-skills`) on every
  binary in `RPCN_TEST_BINARIES`; a missing copy exits 2 at startup. Unset env vars get one retry with
  `<VAR>=dry-run` (dry-run.md section 3). Run outputs match order-independently (a real run reordered o2/o3), each
  expected message a JSON subset of one output, exact count, numbers by exact value (so an unrounded
  `1998.9999999999998` does not pass for 1999). A missing/wrong-path file scores 0 and the run still finishes.
- **Score:** `compare_scores` adds `score`/`score_total` (errors + file points) and `files_found`/`files_total`/
  `file_points`; an edited fixture zeroes all of it. `pick_winner`, `summarize_arm` and the table use `score`,
  falling back to `errors_found` for old `results.json` (`--rejudge` still works). `decided_by` now says `score`
  (`tie on score, judge rank`, ...).
- **Judge:** for a `[[compare.files]]` scenario each reply is followed by the files the run wrote (listed files plus
  other non-fixture `.yaml`/`.yml`/`.blobl` outside hidden folders); a files-only scenario uses a write rubric
  (correctness, robustness, clarity). Empty fixtures (`pipes/.keep`) are no longer shown to the judge.
- **Scenarios:** `rpcn-author__compare_write` (install `rpcn-author`; `ours` checks skill, status, lint; 3 file
  points on `pipes/orders.yaml`: lint, a 3-message bounded run, `orders.dlq`) and `rpcn-test__compare_diagnose`
  (fixture `pipes/orders.yaml` with `(this.total * 10).round()`; errors `total_string`, `cents_x10`; `ours` checks
  skill, unchanged, report ready/fail, lint). Both use `compare_lint`'s 13-entry `allowed_tools`. A reference
  pipeline scored 3/3 on 4.100.0 and 4.115.0; the `* 10` + no-DLQ variant scored lint only. The diagnose fixture
  lints clean on both and fails the bounded run with `cannot multiply types string`.
- **Smoke run** (`run_scenarios.py --scenario '*compare*' --runs 1`, `runs/20261113-115848`, exit 0, ours PASS on
  all three, about $3.30): **every arm got full score in all three** (write 3/3, diagnose 2/2, lint 4/4), so ties
  decided every winner: compare_write `connect-plugin` (tie on score, cost; the judge returned invalid JSON twice,
  a stray `}` closing `notes` early, so no rank); compare_diagnose `skills-repo` (judge: skills-repo >
  connect-plugin > bare > ours); compare_lint `skills-repo` (judge: same order). `ours` was the most expensive arm
  in each ($0.32 / $0.58 / $0.46 vs $0.10-0.44). In judge notes ours lost points for `[tool]` redaction placeholders
  and the trailing status block in its reply, and for unrequested files (`.env.example`, a test report): partly an
  artifact of redaction and headless output, not only reply quality.
- **Not done here:** the full `run_evals.py --with-compare` (about $55) and its record, which the plan puts after
  review and commit; winners, per-arm scores and losses for Sofia go here after that run.
- **Eval record:** `evals/results/2026-11-18-6db288bec933.json` passed with `dirty: false`, at $54.24, on the first full run. Trigger accuracy was 1.0, and all 33 pass scenarios passed 3/3, linted on 4.100.0 and 4.115.0. Wall time was about 48 minutes. `compare`: `compare_write` → `bare`, `compare_diagnose` → `skills-repo`, `compare_lint` → `bare`. Full results are in `T/runs/20261118-105216/results.json`.
- **Benchmark results (3 runs per arm).** Every arm got full marks on all three comparisons, so judge rank decided every winner. The judge ranked `ours` last (4th) in all three.

  | scenario | ours | connect-plugin | skills-repo | bare | winner |
  |---|---|---|---|---|---|
  | `compare_write` (score 3) | rank 4, $0.24, 14.3 turns | rank 2, $0.23 | rank 3, $0.36 | rank 1, $0.31 | `bare` |
  | `compare_diagnose` (score 2) | rank 4, $0.57, 28.0 turns | rank 2, $0.15 | rank 1, $0.25 | rank 3, $0.14 | `skills-repo` |
  | `compare_lint` (score 4) | rank 4, $0.47, 22.0 turns | rank 2, $0.11 | rank 3, $0.20 | rank 1, $0.10 | `bare` |

- **Losses for Sofia (all three comparisons):**
  1. **`rpcn-author__compare_write`, won by `bare`.** In the judge's words: runs 2 and 3 use `.string()` on email, so a missing email passes through silently, against their own failure claims; run 3 uses `mutation`; runs 2 and 3 have header problems. The replies end with `[tool]` placeholders and raw status JSON.
  2. **`rpcn-test__compare_diagnose`, won by `skills-repo`.** The judge left no note on `ours`. `ours` took 28 turns and $0.57, against 7–10 turns and $0.14–0.25 for the others.
  3. **`rpcn-test__compare_lint`, won by `bare`.** In the judge's words: it finds all four errors and checks the fixes on a copy, but run 2's mapping diff is broken (its old and new lines are the same), the replies leave `[tool]` placeholders, and they pad the answer with notes about skipped checks.

  Themes the judge named:
  - **Reply quality, a real weakness:** a status block in an interactive reply, notes about checks that didn't run, files nobody asked for, and a broken diff.
  - **Mapping correctness in Author:** `.string()` lets a missing field pass through.
  - **Cost and turns:** `ours` spends 2–4× more per Test run.
  - **The runner's redaction:** the `[tool]` placeholders are not the skill's own output (`deferred-work.md`, 2.12). They may account for part of the gap.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 1 medium, 4 low, 1 false, 0 maybe-false, plus three findings of our own. Two route to patch, two of our own to defer, and the rest are rejected.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | AC 2 asks for each arm's score, rank and cost in the record's `compare`, but `run_evals` writes only `{scenario: winner}` | low | reject | Fixing this means editing the plan (its AC against "no change expected"). The Intent asks only for the winners in `compare`; task 4 puts the per-arm numbers in Implementation Notes, taken from `results.json`. |
| 2 | Task 4 (the paid run) is open | false | reject | The plan runs it after review and commit, in step 5. |
| 3 | `compare_diagnose` matchers `x 100`, `by 100`, `10x`, `coerce` and `number()` match replies that don't name the cause | medium | patch | Case-insensitive substring match (`match_errors`); "max 100", "by 1000" and an unrelated `.number()` all score. Fix: drop the loose strings and keep the specific ones, plus a negative test that the loose phrases don't match. |
| 4 | `--rejudge` on a moved runs folder gives the judge no written files | low | patch | `written_files` reads the stored absolute `run["dir"]`. Fix: fall back to `<src>/<scenario>/<arm>/run-<i>` when the stored path is gone. |
| 5 | A `git:` source scores with the local `../rpcn-skills` checker | low | reject | It is documented, still arm-neutral, and `run_evals` always uses a `local:` source. A fix would mean extracting the checker from the git source. |
| 6 | `contains = ["orders.dlq"]` is met by any mention | low | reject | The plan says "has the DLQ topic". Checking routing would need a YAML walk; the judge sees the files. |
| 7 | (own) the judge now sees written files, with a written-work rubric, which the plan didn't spell out | low | reject | It fits the Intent (score what each arm wrote), and the judge is unchanged for reply-only scenarios. |
| 8 | (own) redaction leaves `[tool]` placeholders that only our replies show, and the judge marks them down | medium (unverified) | defer | Pre-existing (epic 1 redaction). It can decide a tie-break, so it is raised with the user before the paid run. |
| 9 | (own) on `compare_write` the judge gave the same broken JSON twice, so cost alone decided it | medium (unverified) | defer | Pre-existing (the retry tests pin this reply as invalid). Raised with the user before the paid run. |

## Verification

**Commands:**
- `cd T && uv run --with pytest pytest -q tests` — pass
- `uv run --with pytest pytest -q tools/tests skills` — pass
- `cd T && uv run run_scenarios.py --scenario '*compare*' --runs 1` — a smoke run: each arm scored, a `winner:` line per scenario
