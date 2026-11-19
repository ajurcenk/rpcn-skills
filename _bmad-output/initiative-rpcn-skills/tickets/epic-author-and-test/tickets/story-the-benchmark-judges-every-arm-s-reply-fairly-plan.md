---
title: "The benchmark judges every arm's reply fairly"
type: 'feature'
ticket: '14'
created: '2026-11-18'
status: 'built'
baseline_revision: 'd6144b2419108266529d873e3c128fc5db69eb40'
route: 'full'
route_source: 'auto'
risk: 'low'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** in the 2.12 benchmark the blind judge marked `ours` down for the runner's own artifacts, not for the skill's work.
- **Placeholders:** redaction turns every arm-identifying name into `[tool]`. Only our replies name their tools, so only ours read "apply the changes with [tool], then run [tool] again".
- **Status block:** the AD-8 status block a headless run must end with was judged as "a stray JSON status blob".
- **Broken JSON:** on `compare_write` the judge returned the same malformed JSON on both attempts (`notes` closed one brace early), so cost alone decided that winner.

**Approach:**
- **Neutral redaction:** each redaction pattern gets a plain neutral phrase in place of `[tool]`: "the skill", "the check script", "the report file", "the skill folder". This keeps the judge blind but leaves the reply readable. The same rules apply to every arm.
- **Strip the status block:** a reply's trailing status block (the AD-8 shape `parse_status_block` already finds) is removed before judging, for every arm. The prompt says headless runs end with a machine status block that was removed.
- **Repair the JSON:** when the retry also fails, `parse_judge` tries one narrow repair. It drops one surplus closing brace and moves top-level label keys into `notes`. It accepts the result only when the ranking is valid. Any other malformed reply still fails as today.
- **Prove it:** rejudge the 2.12 run.

## Boundaries & Constraints

**Always:**
- Runner-only (`rpcn-test-skills`): no change under `rpcn-skills/skills/`, so no eval record is needed.
- Every arm is treated the same.
- `results.json` records the redaction map.
- `--rejudge` writes a new file and never changes `results.json`.
- Old runs stay readable.

**Never:**
- Hide anything the arm itself chose to write, such as extra files or `Not run` notes. Those stay for the judge.
- Change scoring or `pick_winner`.
- Rerun any arm.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Reply names a skill or script | "run rpcn-test again; `rpcn_check.py lint`" | "run the skill again; `the check script lint`" | — |
| Path to an installed skill or plugin | `.claude/skills/rpcn-test/…`, a plugin dir literal | "the skill folder" | — |
| Reply ends with a status block | a fenced json block with the AD-8 keys | block removed; the rest kept | a json block without the status keys is kept |
| Judge reply valid | — | parsed as today | — |
| Judge closes `notes` early | `{"ranking":[…],"notes":{"A":…,"B":…}, "C":"…"}}` | repaired: every label's note kept, ranking used | — |
| Other malformed JSON | — | fails, retried once, then an error as today | the existing retry tests keep a still-invalid case |
| Rejudge of `T/runs/20261118-105216` | 3 comparisons | a ranking for all four arms in each; no `[tool]` or status JSON in any judge prompt | — |

</frozen-after-approval>

## Code Map

`T` = `/home/aleksejjurcenko/projects/clients/personal/rpcn-test-skills` (local, baseline `f9c826b3fdb3b7fcaf0a53cee316b8dcdac16985`; leave the untracked `orders_benthos_test.yaml` alone).

- **`T/run_scenarios.py`:**
  - `JUDGE_REDACTIONS` (around line 1926) is a list of patterns, and `REDACTED_TOKEN = "[tool]"`. Make it `(pattern, replacement)` pairs:
    - skill names (`rpcn-*`, plugin skill names, `redpanda-connect:*`, `redpanda:*`): "the skill";
    - `rpcn_check(.py)`: "the check script";
    - `*.test-report.md`: "the report file";
    - `.claude/skills/…`, `.claude-plugin/…` and literal paths: "the skill folder".
  - `redact()` (around line 1940) applies the literals first, then the patterns, longest first.
  - `run_judge` records `redactions` in `results.json` (around line 2106). Record the pairs.
  - `judge_prompt` (around line 1983) redacts each reply. Strip the status block first, with a small helper that uses the same rule as `parse_status_block` (around line 414): only the last fenced json block, and only when it has the status keys. Add one rubric line, in both `JUDGE_RUBRIC` and `JUDGE_RUBRIC_WRITE`: "A machine-readable status block that headless runs end with has been removed from every reply."
  - `parse_judge` (around line 2012) uses `_json_candidates`. Add the narrow repair as a last candidate: when the text fails to parse with exactly one surplus `}` at the end, drop it, then move any top-level key that is a label into `notes`. Keep it in a small, documented function.
  - `rejudge` (around line 2567) and `saved_replies` reuse `run_judge`, so they pick up all of the above.
- **`T/tests/test_run_scenarios.py`:**
  - The judge, redaction and retry tests pin `[tool]` and the 2.12 broken reply as invalid. Update them to the new phrases, and to the reply now being repaired.
  - Keep a still-invalid case for the retry path.
- **`T/README.md`:** the redaction and judge section.

## Tasks & Acceptance

**Execution:**
- [x] `T/run_scenarios.py`: neutral redaction pairs, status-block strip plus the rubric line, and the narrow `parse_judge` repair.
- [x] `T/tests/test_run_scenarios.py`: a test per matrix row, with the existing tests updated.
- [x] `T/README.md`.
- [x] Rejudge `T/runs/20261118-105216` (about $1–2) and record each comparison's new ranking, with the 2.12 one beside it, in Implementation Notes.

**Acceptance Criteria:**
- Given T's tests and R's `tools/` suites, when they run, then all pass.
- Given the rejudge, when it finishes, then each of the three comparisons has a ranking of all four arms, and no judge prompt contains `[tool]` or a status-block JSON.

## Implementation Notes

- `T/run_scenarios.py`:
  - **Redaction:** the redactions are `(pattern, phrase)` pairs, applied in this order:
    1. `JUDGE_FOLDER_REDACTIONS`: `.claude/skills/…` and `.claude-plugin/…` become "the skill folder". They come first, so a skill folder inside a run folder still reads that way.
    2. The literal paths, longest first: plugin folders become "the skill folder", runs folders "the working folder".
    3. `JUDGE_NAME_REDACTIONS`: the report file, the check script (a leading path is absorbed), any other path token with a skill name in it becomes "a folder", and skill names become "the skill". Names also absorb an optional "the" and "skill(s)"/"plugin(s)"/"script".

    `JUDGE_REDACTIONS` is the two pattern lists joined, in the order applied. A phrase is capitalised only at the start of a sentence: the text start, or after `. `, `! `, `? ` or a newline.
  - **Status block:** `strip_status_block` uses parse_status_block's rule. It runs once per reply, on the reply alone, in `run_judge`'s `shown()`, before any written files are appended.
  - **JSON repair:** `parse_judge(..., repair=False)`. `run_judge` parses each attempt without the repair. Only after the last attempt still fails does it try `repair_judge_json` on the not-JSON attempts, latest first, and mark the one it uses `repaired: true`.
  - **What `results.json` records:** `judge.redactions` is `{"patterns": [[pat, phrase]…], "literals": [[path, phrase]…], "status_block": "removed"}`. The old `token` key is dropped; nothing reads it.
- **Tests:** 280 pass in T.
- **Rejudge:** `T/runs/20261118-105216` gave `rejudge-20261118-210218.json`, exit 0, judge cost about $0.54.
  - compare_write: the first attempt was not JSON and the retry also failed, so the repair was used on the retry's reply. The other two parsed first time.
  - The prompts in `rejudge-20261118-210218/<scenario>/judge*.prompt.md` (including compare_write's retry prompt) contain 0 `[tool]`, 0 "the skill-", 0 `"status"` and 0 ```` ```json ```` fences.

| comparison | 2.12 ranking | rejudge ranking |
|---|---|---|
| compare_write | bare > connect-plugin > skills-repo > ours | bare > connect-plugin > skills-repo > ours (retried, then repaired) |
| compare_diagnose | skills-repo > connect-plugin > bare > ours | skills-repo > connect-plugin > bare > ours |
| compare_lint | bare > connect-plugin > skills-repo > ours | bare > connect-plugin > skills-repo > ours |

- **Finding:** the judge no longer cites `[tool]` or the status JSON. Its compare_write and compare_lint notes on ours are about substance only. In compare_diagnose it still calls "the report file" and "the skill" placeholders that make ours' replies harder to act on.
- **After the review fixes:** T's tests (280), R's `tools/` and skill suites (146) and the validator pass. Nothing under `skills/` changed, so the 2.11 eval record still covers the skills.

## Plan Change Log

## Review Triage Log

Quick pass: 0 high, 3 medium, 2 low, 0 false, 0 maybe-false. All five route to patch.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The JSON repair runs on the first attempt, so the retry never runs; the frozen intent says it comes after the retry fails | medium | patch | `parse_judge` calls `repair_judge_json` on every attempt, and `test_notes_closed_early_repaired_without_retry` pins `calls == 1`. Fix: parse without the repair first, and repair only once the retry has also failed. Update the test and the README. |
| 2 | A run-folder literal swallows `ours`' installed-skill script path, so its commands read `uv run the working folder lint …` | medium | patch | `redact()` replaces literals (plus the rest of the path) before the `.claude/skills/` pattern. Only `ours` runs scripts from under its run folder. Fix: apply the skill-folder and plugin-folder patterns before the literals, so that path reads "the skill folder". |
| 3 | Skill names are replaced inside paths, giving text such as `/tmp/the skill-qkzmwrtb/` | medium | patch | `\brpcn-test\b` matches inside path segments; seen in the rejudge's `compare_lint` prompt. Fix: replace a whole path that contains an arm-identifying name with a neutral "a folder", before the name rule runs. |
| 4 | Capitals follow the matched text, not the sentence | low | patch | `_neutral()` capitalises only when the match did. Fix: capitalise only at the start of a sentence, and lowercase everywhere else. |
| 5 | Write comparisons strip the status block twice | low | patch | `reply_text` strips it, then `judge_prompt` strips it again over the reply plus the written files. A written file with a status-shaped json fence could be hidden. Fix: strip it in one place only. |

## Verification

**Commands:**
- `cd T && uv run --with pytest pytest -q tests` — pass
- `uv run --with pytest pytest -q tools/tests skills` (in R) — pass
- `cd T && uv run run_scenarios.py --rejudge runs/20261118-105216` — exit 0; every comparison ranked
- the rejudge's judge prompts, in the work folder `rejudge` writes them to (not the original `judge.prompt.md`), contain no `[tool]` and no status-block JSON
