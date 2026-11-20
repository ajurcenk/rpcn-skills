---
title: 'Re-benchmark Author and Test after the improvements'
type: 'chore'
ticket: '18'
created: '2026-11-20'
status: 'built'
baseline_revision: 'f31f161ed5505c8758f35ba33cb200deea754fb7'
route: 'oneshot'
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

**Problem:** stories 14–17 changed the benchmark judge, the comparison points, rpcn-test (16) and rpcn-author (17). Two things are still open:
- whether `ours` now wins any comparison;
- the eval record for 16 and 17 (AD-14). Under the epic's 2026-11-18 decision, this run is that record, and 16–18 are pushed together after it.

**Approach:**
- Run `uv run tools/run_evals.py --with-compare` once on the committed tree, with absolute `RPCN_TEST_BINARIES` for 4.100.0 and 4.115.0. It costs about $55.
- Commit the record.
- In Implementation Notes, from `results.json`, record each comparison's winner, every arm's score, judge rank and cost, plus the turns and cost of the scenarios 16 aimed at, against 2.12.
- A comparison `ours` loses is recorded with the judge's evidence and accepted. No new story comes from it unless the user asks (epic decision 2026-11-18).
- No skill or runner change in this story. If the run fails, stop, record why, and ask the user.

</frozen-after-approval>

## Implementation Notes

- **Eval record:** `evals/results/2026-11-20-83e2eea0bd76.json` passed with `dirty: false`, at $54.21, on the first full run (about 58 minutes). Trigger accuracy was 1.0. All 38 scenarios (35 pass scenarios, the four new 2.17 ones among them, plus the 3 comparisons) passed 3/3 on 4.100.0 and 4.115.0. Scenarios with a `[[lint]]` check linted on both. It is the AD-14 record for 16 and 17. Full results: `T/runs/20261120-171018/results.json`. `compare`: `compare_write` → `skills-repo`, `compare_diagnose` → `skills-repo`, `compare_lint` → **`ours`**.
- **Comparisons** (3 runs per arm):

  | Comparison | ours | connect-plugin | skills-repo | bare | Winner |
  |---|---|---|---|---|---|
  | `compare_write` | 4.00/4, rank 4, $0.30, 19.0 turns | 3.67/4, rank 3, $0.23 | 4.00/4, rank 1, $0.48 | 3.33/4, rank 2, $0.22 | skills-repo (tie on score, judge rank) |
  | `compare_diagnose` | 3.00/3, rank 4, $0.47, 26.3 turns | 2.67/3, rank 3, $0.21 | 3.00/3, rank 1, $0.28 | 3.00/3, rank 2, $0.21 | skills-repo (tie on score, judge rank) |
  | `compare_lint` | 4.00/4, rank 1, $0.38, 18.7 turns | 4.00/4, rank 4, $0.12 | 4.00/4, rank 3, $0.23 | 4.00/4, rank 2, $0.12 | **ours** (tie on score, judge rank) |

  Against 2.12, the scores now separate some arms. `ours` gets full marks on every comparison, which only `skills-repo` also does. Every point lost on `compare_write` is the lint point, lost for a deprecated `kafka_franz` (`lint --deprecated`, AD-4): one `connect-plugin` run and two `bare` runs. `connect-plugin` also loses one point on `compare_diagnose`.
- **Losses, recorded and accepted** (epic decision 2026-11-18; no new story unless the user asks):
  1. **`compare_write`, won by `skills-repo`.** The judge's note on `ours`: it relies on `lowercase()` erroring when `email` is missing, so an empty-string email passes through to `orders.clean`. String totals fail, later runs drop the error header, it never ran the pipeline on sample messages, and it adds an unrequested env-var indirection and `.env.example`. The winner rejects missing, null or empty emails and tested thoroughly. In the judge's words, "runs 2 and 3 use an atomic mapping so the DLQ gets the event unchanged, and the run 1 mutation weakness was caught and disclosed".
  2. **`compare_diagnose`, won by `skills-repo`.** The judge ranked `ours` 4th but wrote no note on it: its reply's `notes` cover the other three labels only. That leaves no judge evidence, and it happened in 2.12 as well (deferred as a judge defect). Not the judge's reason, but on record: `ours` cost 26.3 turns and $0.47, against 12.3 and $0.28.
- **What 16 aimed at** (turns against 2.12, like for like):
  - `lint_broken`: 18.7, against 23.7. Met.
  - `dry_run_error`: 26.7, all three runs writing unit tests, against 28. Met.
  - `unit_bug`: 26.7, against 26.7. **Not met:** story 16's criterion asks for fewer turns, and this run is 16's record. 16's smoke had 25.7. The user decides whether to accept it.
  - Cost, like for like: $0.32 against $0.49, $0.51 against $0.55 (the tests-written runs) and $0.40 against $0.50.

## Review Triage Log

Quick pass (first started on an empty diff from a mistyped baseline hash; re-run on the corrected 335-line diff): 0 high, 1 medium, 6 low, 2 false, 1 deferred.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The record is not committed | false | reject | Committing is the next step of this route. |
| 2 | "37 pass scenarios" is wrong | low | patch | It is 38 (35 plus 3 comparisons). Fixed. |
| 3 | "linted on 4.100.0 and 4.115.0" overstates it | low | patch | 9 scenarios have no `[[lint]]`. Fixed. |
| 4 | "about 56 minutes" | low | patch | 17:10:18 to 18:07:59 is about 58. Fixed. |
| 5 | `connect-plugin`'s `compare_write` loss is misattributed | low | patch | It is also `kafka_franz` on the lint point. Fixed. |
| 6 | The winner's evidence is overstated | low | patch | Now quotes the judge, with the run 1 qualifier. |
| 7 | `compare_diagnose` loss has no judge evidence | medium (unverified) | defer | The judge omitted a note on `ours` two runs in a row (2.12 and 2.18). Recorded in the notes and in `deferred-work.md`. |
| 8 | `unit_bug` misses 16's turn criterion in 16's own record | medium | patch | Stated as not met, for the user to decide. |
| 9 | The cost baseline isn't like for like | low | patch | `dry_run_error` now compares against $0.55. |
| 10 | `lenses_ran` was set before the review | false | reject | The route writes it once the lens is launched; it was. |

## Verification

- `uv run tools/eval_record_check.py` — the new record matches the current skills, `passed: true`, `dirty: false`
- `uv run --with pytest pytest -q tools/tests skills` and T's tests — pass before the push
