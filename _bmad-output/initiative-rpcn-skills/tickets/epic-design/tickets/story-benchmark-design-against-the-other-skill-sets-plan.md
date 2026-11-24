---
title: 'Benchmark Design against the other skill sets'
type: 'feature'
ticket: '9'
created: '2026-11-23'
status: 'done'
baseline_revision: '0afd001ffdb5e2623839fa4d589216763a98bb71'
route: 'full'
route_source: 'auto'
risk: 'medium'
review: 'quick'
review_source: 'pinned'
lenses_ran: ['quick']
review_loop_iteration: 1
context: ['_bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md', 'evals/README.md']
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** epic R10 asks for one Design comparison scenario run in all four arms (`ours`, `connect-plugin`, `skills-repo`, `bare`) at the epic's end, with the eval record naming the winner. Every existing comparison scores a pipeline or a diagnosis. None scores a design note, and the other arms don't write `design@1`.

**Approach:**
- **One comparison scenario,** `rpcn-design__compare_design`. It gives the same plain request in every arm: "before any YAML is written, write a design note in `flows/order_feed.design.md`" for a pipeline that calls for several patterns. Those are a named DLQ, retries with a count, per-key ordering, and dedupe by a key. Each arm gets the same fixtures and `allowed_tools` as the other comparisons.
- **Arm-neutral scoring on the file the arm writes,** reusing `[[compare.files]]`:
  - one `contains` entry (one point) per expected pattern, naming what any good note must say (such as the DLQ topic `orders.dlq`, and the dedupe key `order_id`);
  - **one new key, `components`:** a list of component names, each a string or `a|b` alternatives. It scores a point when every name, or one of its alternatives, appears in the file, and `rpcn_check list` reports each name found, on every binary in `RPCN_TEST_BINARIES`. This is the "components against the binary" check. It scores names, not the `design@1` format.
- **Pass checks in the `ours` arm only,** as for the other comparisons: the skill used, the status, and the note `ready` through `hash --check`.
- **The record:** `run_evals.py --with-compare` at 2 runs is the record for 3.6, 3.7, 3.8 and 3.9 (decision 2026-11-23). It must pass with `dirty: false`.
- **Decision (2026-11-23, user, review loop 1: "full rework"):** the scoring changes as follows.
  1. **Pattern points** use a new `[[compare.files]]` key, `any_of`. It is a list of alternatives, matched case-insensitively as substrings. One point when any alternative is in the file. `contains` stays as it is, so the other three comparisons keep their exact scoring.
  2. **The `components` point** also fails when the note claims an invented component. That is a backticked bare identifier on a line that names a component kind (input, output, processor, cache, rate limit, buffer, or "component"), which `rpcn_check list` doesn't report on every pinned binary. Field names that `rpcn_check fields` reports for the listed components the note names are excluded, and so are words from the prompt.
  2a. **Decision (2026-11-23, user, after the rebuild smoke):** the line-based rule gave false positives. It took config sections, test ids, metric names, cache labels and Bloblang functions as invented components, and those alone made `ours` win. A backticked identifier now counts as a claimed component only in a component position:
     - in a Markdown table row whose kind cell is input, output, processor, cache, rate_limit or buffer, as the next cell;
     - or right next to a kind word ("the `x` output", "`x` processor", "output: `x`", "a `x` cache").
     
     Before the record, re-score both saved smokes (`T/runs/20261123-185229` and `T/runs/20261123-192330`) offline. No arm may lose the point to a non-component. Any arm that does is a bug in the rule, which is fixed first.
  3. **No pattern is counted twice.** Each pattern has exactly one point; `components` checks grounding, not the patterns.
- **A loss:** it is recorded with the judge's evidence and accepted, unless the user asks for a story (epic decision 2026-11-20). The plan records each arm's score, judge rank and cost.

## Boundaries & Constraints

**Always:**
- The scoring is arm-neutral: no point needs `design@1`, a header or our section names.
- A `components` name counts only when `rpcn_check list` reports it on every pinned binary. A misspelled or invented name scores nothing.
- Sessions run on 4.117.0, and the checks run on both pins.
- The record runs 2 times per case. After it passes, ask before pushing 3.6–3.9 together.

**Never:**
- Changing a skill to win the comparison inside this story.
- Changing any existing comparison's scoring: the other three keep their points exactly.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| A note naming every pattern and real components | any arm | full points | — |
| A note with an invented component | for example `kafka_dlq` | the `components` point is lost | — |
| An arm writes no file | — | 0 file points; the judge still ranks the reply | as the other comparisons |
| `a\|b` alternatives | `redpanda\|kafka_franz` | either one present and listed scores | — |
| A bad `components` value | not a list, or an empty string | `SetupError` naming the key | as the other keys |
| A name the binary doesn't list | in the expected list itself | it never scores; the shipped test asserts every expected name is listed on both pins | — |

</frozen-after-approval>

## Code Map

`T` = `rpcn-test-skills` (local, baseline `c87e47c0bddcc483e0043bcf1da8920ded1b1f87`; leave the untracked `orders_benthos_test.yaml` alone). `R` = `rpcn-skills`.

- **`T/run_scenarios.py`:**
  - `validate_compare` (line ~397): the `compare.files` keys gain `components`, a non-empty list of non-empty strings. Add `"components"` to `FILE_POINTS`.
  - **Scoring:** where a `[[compare.files]]` entry's `lint`, `run` and `contains` points are scored (find it through `FILE_POINTS` and `compare_scores`, line ~1857), add `components`. For each name, split on `|`, and use the first alternative found in the file as a whole word, case-insensitive. Then check it with `rpcn_check list` on each binary: one `list` call per category per binary per run, cached. It is one point when every name has a listed alternative in the file. Its why names what is missing or unlisted.
- **Review loop 1 amendments (do these):**
  - **`any_of`:** a new `[[compare.files]]` key, a non-empty list of non-empty strings. It scores one point when any alternative is a case-insensitive substring of the file. Add it to `FILE_POINTS` and to validation. Test it: a hit, a miss, case, and a bad value.
  - **The scenario's pattern entries, one point each, all `any_of`:**
    - `dlq` (`orders.dlq`);
    - `retries` (alternatives for three retries: `3 times`, `three times`, `3 retries`, `max_retries: 3`, `retries: 3`, `up to 3`);
    - `ordering` (`max_in_flight`, `in order`, `ordering`);
    - `dedupe` (`dedupe`, `deduplicat`, `de-duplicat`, `duplicate`). The key `order_id` is in the prompt, so any arm echoes it, and it scores nothing on its own.

    Keep exactly one point per pattern. An entry holds only `any_of`, because each scoring key in an entry is its own point.
  - **The `components` point:**
    - Expected names stay as KEEP.
    - It also fails on a claimed but unlisted component: a backticked bare identifier (`^[a-z][a-z0-9_]*$`) on a line naming a component kind (input, output, processor, cache, rate limit, buffer, or "component", case-insensitive). That identifier must not be in any `rpcn_check list` category on every binary, must not be a field name `rpcn_check fields <category> <name>` reports for a listed component the note names (cached per run), and must not be a word in the scenario prompt.
    - The why names each invented identifier.
    - Tests: a note with `` `kafka_dlq` `` on an output line loses the point; a backticked field like `` `max_in_flight` `` on an output line doesn't; a prompt word doesn't; a backticked token on a line with no kind word is ignored.
  - **No double count:** pattern points never use component names as their only evidence.
  - **Binary label:** read the version from the `list` envelope's `binary.version`.
  - **T README:** four comparisons, and their total cost.
  - **Smoke:** the four arms once, with the judge on. Record each arm's score, judge rank and cost.
- **`T/tests/test_run_scenarios.py`:** cover the matrix rows: validation (good, not a list, an empty string), and scoring (all present and listed, one missing, an invented name, alternatives). Stub the `list` call, as the existing `run`/`lint` compare tests stub `rpcn_check`.
- **New `T/scenarios/rpcn-design__compare_design/`:** copy `T/scenarios/rpcn-author__compare_write/` for the `allowed_tools`, `max_turns` and `[compare] enabled = true` shape.
  - **The prompt** is plain and unattended. It names the topic `orders` on Redpanda, an HTTP API at `${FULFILMENT_API_URL}`, retries 3 times, then `orders.dlq`, each customer's orders in order, and repeats dropped by `order_id`.
  - **The `ours` pass checks:** `[status]` (`rpcn-design`, complete), and `[[report]]` on the note (`ready = true`).
  - **The `[[compare.files]]` entries, one point each:**
    - `dlq` (`contains = ["orders.dlq"]`);
    - `retries` (`contains = ["retry", "3"]`);
    - `ordering` (`contains = ["max_in_flight"]`);
    - `dedupe` (`contains = ["order_id", "dedupe"]`);
    - `components` (`["redpanda|kafka_franz|kafka", "http_client", "retry", "fallback", "dedupe"]`).
  - **A shipped test** asserts every expected component alternative is listed by `rpcn_check list` on both pins, using a real-binary skip as elsewhere.
- **`T/README.md`:** document `components`.
- **`R/evals/README.md`:** four comparisons; the `--with-compare` cost.
- **The record:** `uv run tools/run_evals.py --with-compare`, which runs 2 by default. Then commit the `evals/results/*.json`.

## Tasks & Acceptance

**Execution:**
- [x] T runner: `components` and `any_of` validation and scoring (with the invented-component rule), with tests and README.
- [x] T: the `compare_design` scenario and its shipped tests. R README.
- [x] Smoke: `compare_design` in all four arms once (`run_scenarios.py --scenario rpcn-design__compare_design --runs 1`, with the judge on). Record each arm's score, judge rank and cost in Implementation Notes. (Re-run after the rebuild.)
- [ ] After review and commit: the record, `run_evals.py --with-compare`, about $75. Record its winner, scores and cost.

**Acceptance Criteria:**
- Given the repo, when T's tests and all `tools/` suites run, then all pass.
- Given the smoke, when it finishes, then all four arms ran and each has a score and a judge rank.
- Given the committed tree, when `run_evals.py --with-compare` runs, then it passes with `dirty: false`, and its compare names a Design winner. Then ask before pushing 3.6–3.9.

## Implementation Notes

Rebuild after review loop 1 (2026-11-23), from the first build's KEEP parts plus the amendments.

- **Runner (T `run_scenarios.py`):** `FILE_POINTS` gains `any_of` and `components`; `LIST_CATEGORIES` is the lookup order (`inputs`, `processors`, `outputs`, `caches`, `rate-limits`, `buffers`, `scanners`, `metrics`, `tracers`).
  - `validate_compare`: `any_of` is a non-empty list of non-empty strings; `components` as KEEP (no empty `|` alternative). Either bad value is `SetupError` on `compare.files[i].<key>`.
  - `any_of`: one point when any alternative is a case-insensitive substring; the why names the hit, or lists every alternative. `contains` is unchanged (case-sensitive), so the other three comparisons keep their scoring.
  - `components`: as KEEP (whole word, any case, first alternative found, listed on every binary via `_list_category`, cached per (script, binary, category) per run), plus `invented_components`: a backticked `^[a-z][a-z0-9_]*$` token on a line matching `COMPONENT_KIND_RE` (input, output, processor, cache, rate limit, buffer, component; plurals, any case) that isn't listed on every binary, isn't a prompt word (`\w+`, lower-cased) and isn't a field-path segment `rpcn_check fields <cat> <name>` reports on any binary. The fields lookup is lazy (only when a suspect exists) and covers the listed components the note names backticked anywhere or as a whole word on a kind line, not every prose word that happens to be a component (`file`, `log`), which kept a run's scoring to about 45 s instead of about 60 s. The why names each invented identifier.
  - The binary label comes from the `list` envelope's `binary.version` (cached per binary per run).
  - `score_files` / `score_file_entry` take the scenario `prompt`; the run passes `sc.prompt`.
- **Tests (T):** `ComponentsPointTests` (KEEP cases, plus: `` `kafka_dlq` `` on an output line loses the point; listed on one binary only; a backticked field `` `max_in_flight` `` on an output line doesn't; a prompt word doesn't; a backticked token with no kind word is ignored and calls no `fields`); `ListChecker` stubs `list` and `fields`, with the envelope version per binary. `AnyOfPointTests` (hit, case, miss, missing file, bad value, `contains` still case-sensitive). `test_compare_design` asserts the four `any_of` entries, one scoring key per entry, no `contains`, no `order_id` alternative. `test_compare_design_components_listed_on_both_pins` (real binaries) also checks that a field on an output line scores and `` `kafka_dlq` `` doesn't. T suite: 408 passed, 4 skipped without binaries; 412 passed with both pins. R: `tools/shared/rpcn_check/tests` 195 passed (both pins), `tools/tests skills` 146 passed.
- **Scenario:** `T/scenarios/rpcn-design__compare_design/` as KEEP; the four pattern entries are `any_of` only, as the Code Map lists.
- **READMEs:** T documents `any_of`, the invented-component rule and its known limit, four comparisons and about $19 at 2 runs; R says four comparisons, `any_of`, the invented rule, about +$19, about $78 in all.
- **Smoke (2026-11-23, `--runs 1`, judge on, `runs/20261123-192330`):** all four arms finished; `ours` passed its checks (visible, skill, status, note `ready`).

  | arm | score | missed | judge rank | turns | cost | time |
  |---|---|---|---|---|---|---|
  | ours | 5/5 | — | 4 | 20 | $0.46 | 46s |
  | connect-plugin | 4/5 | `components`: invented `buffer`, `o4`, `o2` | 1 | 33 | $1.05 | 252s |
  | skills-repo | 4/5 | `components`: no `fallback` | 3 | 17 | $1.09 | 247s |
  | bare | 4/5 | `components`: invented `buffer`, `fallback_error`, `output_error`, `input_received`, `output_sent` | 2 | 21 | $0.57 | 152s |

  Judge $1.51 (one retry on invalid JSON); total about $4.70. Winner on score: `ours`. All four arms scored every pattern point. Judge's evidence: connect-plugin "wrote the design note first, then a linted YAML that it tested locally against a stub server", fixing reordering and re-serialization; ours "thin design note with no YAML", a retry output around `http_client` "which multiplies attempts", ordering admitted not guaranteed. The judge also misread the request for skills-repo ("asked for a pipeline after the note").
  That smoke's scores came from the line-based rule (decision 2), whose losses for connect-plugin and bare were all false positives (`buffer`, `o4`/`o2`, metrics, a Bloblang function). Replaced by decision 2a below.
- **Decision 2a (position rule), built 2026-11-23:** `claimed_components(text)` takes a backticked token only from the cell right after a kind cell in a Markdown table row (`input`, `output`, `processor`, `cache`, `rate_limit`/`rate limit`, `buffer`; plural, any case, `**`/backticks stripped), from "`x` <kind>" (so "the/a `x` <kind>"), or from "<kind>: `x`". `invented_components` applies the same exclusions (listed on every binary, prompt words, field-path segments of listed components the note backticks). "component" is no longer a kind word. Tests: `kafka_dlq` in "the `kafka_dlq` output", "DLQ output: `kafka_dlq`", "a `kafka_dlq` processor" and a table's output cell loses the point; `buffer`, `o4`, `output_error`, `fallback_error`, `seen_orders` (as "cache resource `seen_orders`"), `source_topic` in prose on output/cache lines do not; a field in a claim position does not. T suite: 410 passed, 4 skipped; 414 passed with both pins.
- **Offline re-score with decision 2a (no new sessions):** both saved smokes, real checker, both pins, about 2-5 s a note.

  | run | arm | dlq | retries | ordering | dedupe | components | score |
  |---|---|---|---|---|---|---|---|
  | 185229 | ours | pass | pass | pass (`max_in_flight`) | pass | pass | 5/5 |
  | 185229 | connect-plugin | pass | pass | pass (`in order`) | pass | pass | 5/5 |
  | 185229 | skills-repo | pass | pass | pass | pass | pass | 5/5 |
  | 185229 | bare | pass | pass | pass | pass | pass | 5/5 |
  | 192330 | ours | pass | pass | pass | pass | pass | 5/5 |
  | 192330 | connect-plugin | pass | pass | pass | pass | pass | 5/5 |
  | 192330 | skills-repo | pass | pass | pass | pass | fail: no `fallback` (the note never names it) | 4/5 |
  | 192330 | bare | pass | pass | pass | pass | pass | 5/5 |

  No arm loses a point to a non-component; the one loss is an expected name the note doesn't contain. The claimed tokens found were all real components (`redpanda`, `http_client`, `fallback`, `dedupe`, `memory`, `retry`, `switch`, `http_server`, `stdin`, `log`, `mutation`, `cache`, `http`) or non-identifiers ignored by the bare-identifier test. With ties on score, the judge's rank decides: 192330's judge order was connect-plugin, bare, skills-repo, ours.
- **Review fixes (2026-11-23):** `_CLAIM_BEFORE_RE` takes `*`/`_` around the kind word and colon (`**Output:** \`x\``); `_CLAIM_AFTER_RE` skips a kind word followed by field, setting, metadata, key, label, option, name, config or id (plural ok); a table row's backticked cell before the kind cell is the claim when there is one; a failed `list` lookup makes a claimed token `unchecked` (error in the why), not invented. `any_of` drops `3 times` (in the prompt verbatim) and `in order` ("in order to"). The real-binary test puts `max_in_flight` in a table output cell beside `http_client`, so the real `fields` exclusion runs. READMEs use the 192330 smoke's costs (about $4.70 at 1 run, about $8 at 2; four comparisons about +$20, a record about $79). Offline re-score after the fixes: 185229 all four arms 5/5; 192330 ours, connect-plugin, bare 5/5, skills-repo 4/5 (no `fallback`). Retries now match `3 retries` (bare, connect-plugin, skills-repo) or `max_retries: 3` (ours); connect-plugin 185229's ordering matches `ordering`.
- **Not done here:** the record (`run_evals.py --with-compare`, about $78) waits on review, the decision above, and commit; then ask before pushing 3.6–3.9. Nothing is committed.

Quick pass 2 (2026-11-23, rebuild with decision 2a): 0 high, 2 medium, 6 low, 0 false. All eight route to patch.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The scenario header still describes the line-based rule | low | patch | Describe the position rule. |
| 2 | `**Output:** \`x\`` and `**Output**: \`x\`` are never seen as claims | low | patch | Allow `*`/`_` around the kind word and the colon; add a test. |
| 3 | "the \`x\` output field" / "\`x\` input metadata" is a false claim | medium | patch | A kind word followed by field, setting, metadata, key, label, option, name, config or id is not a claim; add a test. |
| 4 | A table with the name before the kind cell flags the cell after the kind | low | patch | When a backticked identifier sits before the kind cell, that one is the claim; add a test. |
| 5 | The real-binary test's `max_in_flight` case tests nothing | low | patch | Put the field in a claim position ("\`max_in_flight\` output"? no: a table cell after "output"), so the real `fields` exclusion runs. |
| 6 | Pattern points can be earned by echoing the prompt ("3 times"; "in order" matches "in order to") | medium | patch | Drop alternatives the prompt holds word for word, and drop `in order`. Keep `orders.dlq`: naming the DLQ is required. |
| 7 | The README cost figures don't match the recorded smoke | low | patch | Use the `runs/20261123-192330` figures and adjust the totals. |
| 8 | A failed `list` call reads as an invented component | low | patch | Report the error (as `not_on` does) and don't call the token invented. |

- **Eval record (2026-11-24):** `evals/results/2026-11-23-d38b0a5cc8a4.json` passed with `dirty: false` on the first run, at $87.06 (`T/runs/20261123-212320`). It is the record for 3.6, 3.7, 3.8 and 3.9. Trigger accuracy was 1.0, and all 65 scenarios passed 2/2 on 4.100.0 and 4.117.0, with sessions on 4.117.0.
- **Design comparison, winner `ours` on score:**

  | arm | score | judge rank | cost/run | time/run | point lost |
  |---|---|---|---|---|---|
  | ours | 5/5 | 4 | $0.53 | 51 s | — |
  | connect-plugin | 4.5/5 | 3 | $0.80 | 193 s | components: "invented" `seen_orders`, a cache resource label (the README's known false positive) |
  | skills-repo | 4.5/5 | 2 | $1.95 | 401 s | components: no `http_client` (fair) |
  | bare | 4.5/5 | 1 | $0.67 | 203 s | components: `seen_orders` (false positive) and `kafka_franz` (not listed on 4.117.0; fair) |

  **Caveat:** the margin is half a point. connect-plugin's loss comes only from the documented label false positive, and the judge ranks `ours` last. The judge's evidence against `ours`:
  - a `retry` output wrapped around `http_client`, which has retries of its own, so attempts multiply;
  - the 5-minute dedupe window, accepted as is;
  - a replayed order lost to dedupe, accepted, where skills-repo records an id only after a successful post;
  - only the note was written; the other arms also wrote and tested YAML.
- **Other comparisons in the record:**
  - `compare_write`: skills-repo wins (4/4 tie, judge); ours 4/4, judge rank 4.
  - `compare_diagnose`: connect-plugin wins (3/3 tie, judge); ours 3/3, judge rank 4.
  - `compare_lint`: bare wins (4/4 tie, judge); ours 4/4, judge rank 3.

- **Pushed:** `72cf82a..560f483`, with 3.6–3.9 together. CI run 45450913995 was green. The record is `evals/results/2026-11-23-d38b0a5cc8a4.json`. T commits stay local.

## Plan Change Log

- 2026-11-23, review loop 1 (bad_plan). **Trigger:** findings 2–4. The scoring can't detect an invented component, the patterns are case-sensitive substrings, and two patterns count twice. **Amended:** the Code Map below, per the user's decision in the Intent. **Known-bad state avoided:** a Design score that rewards five prose words and misses correct wording. **First build kept for reference only:** `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/3.9-try1-T.patch` and `/tmp/claude-1000/-home-aleksejjurcenko-projects-clients-personal-rpcn-skills/e8f28587-8692-460b-9a36-56b1bb18132f/scratchpad/3.9-try1-R.patch`. Re-derive from this plan.
  **KEEP:**
  - The `components` validation: list, non-empty strings, `a|b` alternatives, with a bad value raising `SetupError` naming the key.
  - The whole-word, case-insensitive name matching, and the per-run, per-binary `list` cache in a fixed category order.
  - `ComponentsPointTests`' structure.
  - The scenario's prompt and `ours` pass checks.
  - The real-binary test that every expected name is listed on both pins.
  - `components = ["redpanda", "http_client", "retry", "fallback", "dedupe"]`, with no `kafka`/`kafka_franz` (neither is listed on 4.117.0).
  - The README docs.

- 2026-11-23: the `components` entry is `["redpanda", "http_client", "retry", "fallback", "dedupe"]`, not `"redpanda|kafka_franz|kafka"`. `rpcn_check list` on 4.117.0 lists neither `kafka` nor `kafka_franz` (in any category; 4.100.0 lists them as outputs only), so those alternatives could never score, and the shipped test that every expected alternative is listed on both pins would fail. A bare `kafka` would also match ordinary prose. The `a|b` form stays in the runner and its unit tests.

## Review Triage Log

Quick pass (2026-11-23, first build): 0 high, 3 medium, 2 low, 1 false. One finding needed the user, who chose "full rework". It routes to bad_plan (loop 1). Two low findings are folded into the rebuild. One finding is false.

| # | Finding | Verdict | Route | Evidence / action |
|---|---|---|---|---|
| 1 | The record AC is not met | false | reject | The record runs after the commit, by design (Tasks, step 4). |
| 2 | `components` never sees an invented component; the matrix row `kafka_dlq` is not met, and its test covers a different row | medium | bad_plan | The scorer only looks for the expected words, so the plan's design can't meet that row. Decision 2 replaces it. |
| 3 | `contains` is case-sensitive: "Retries: 3" and "Deduplicate" score nothing, and the "3" matches any date | medium | bad_plan | A plain substring check. Decision 1 (`any_of`) replaces it. |
| 4 | `retry` and `dedupe` score twice (`contains` and `components`) | medium | bad_plan | Decision 3. |
| 5 | The "unlisted" reason labels the binary by its parent folder | low | bad_plan (fold in) | Use the version from the `list` envelope (`binary.version`), as `lint` and `run` do with `_version`. |
| 6 | T README still says three comparisons and gives the old cost | low | bad_plan (fold in) | Update the count and the total. |

## Verification

**Commands:**
- `cd T && uv run --with pytest pytest -q tests` -- pass
- `RPCN_TEST_BINARIES=<R>/.cache/rpcn/4.100.0/redpanda-connect:<R>/.cache/rpcn/4.117.0/redpanda-connect uv run --with pytest pytest -q tools/shared/rpcn_check/tests`, `uv run --with pytest pytest -q tools/tests skills` -- pass
- `cd T && RPCN_TEST_BINARIES=… uv run run_scenarios.py --source local:<R> --runs 1 --scenario rpcn-design__compare_design` -- all four arms ran, with scores
