---
type: review
lens: adversarial (compliant-but-divergent units), scoped to AD-15
target: _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md
section: AD-15 — Content sources (uncommitted draft, 2026-11-10)
inputs:
  - _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/architecture-rpcn-skills.md
  - _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/.memlog.md
  - _bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/epic-author-and-test.md (and tickets.toml)
  - _bmad-output/initiative-rpcn-skills/tickets/epic-design/epic-design.md
  - _bmad-output/initiative-rpcn-skills/tickets/epic-release-sync/epic-release-sync.md
  - SOURCES.md, skills/rpcn-test/references/lint-errors.md, tools/rpcn_versions.txt
created: '2026-11-10'
verdict: 'Revise before stories 2.7-2.11 bind to it. AD-15 names sources by kind, but the kinds overlap, the pins and the proof are undefined, provenance has three possible homes, and it contradicts AD-11 twice. Compliant stories can still ship the same fact with different answers, which is exactly what AD-15 says it prevents.'
---

# Adversarial Review: AD-15 Content Sources

## Verdict

**Revise before stories 2.7–2.11 and epic 3 start.** The intent is sound: the binary is the truth at runtime, and each kind of distilled fact has one source. But the rule is keyed on *kind of fact*, and real facts belong to more than one kind. It never says *which* tag or commit, or *what* counts as a test or eval proof. It puts provenance in a root file that a skill installed alone via `npx skills` doesn't carry. It also clashes with AD-11 on failure-mode sources and on who owns component facts. Every pair below follows every AD to the letter and still diverges.

Severity: **High** means two shipped skills give the user different answers for the same fact, or a stale fact ships with a "confirmed" stamp. **Medium** means rework, churn or a licence gap. **Low** means friction.

## Summary

| # | Sev | Units | Hole | Smallest tightening |
|---|---|---|---|---|
| S1 | High | rpcn-design (epic 3) vs rpcn-test design check (story 2.10) | The same fact falls under two kinds (behaviour and best practice), so it gets two sources and two homes | Classify by claim, not by consumer: any claim about what the binary does is a behaviour fact. A fact used by more than one skill lives in one `tools/shared/` file (AD-2) |
| S2 | High | rpcn-author / rpcn-design (AD-4 `fields`) vs any story distilling defaults from source; epic 4 release sync vs gen_refs | AD-11's generated refs and AD-15's distilled refs both own component facts, and "the binary is the only source" contradicts reading `references/` at runtime | Anything `rpcn_check list`/`fields` reports is AD-11's alone and never restated by hand. Rewrite the runtime sentence. Release sync diffs the generated output, and rows name their components |
| S3 | High | story 2.7 (distilled at 4.115.0) vs epic 3 story (distilled after a weekly roll) | "A pinned tag" is never fixed. The skill-set commit can differ from the AD-13 benchmark commit. "The binary wins" doesn't say which binary | One pin registry. Connect = the AD-5 newest pin at writing time, and skill sets = the AD-13 benchmark commit. A fact that differs between the pins ships version-qualified |
| S4 | High | story 2.10 (eval proof) vs story 2.8 (binary test proof) | "Confirmed by a test or an eval" lets an LLM-graded scenario stand in for a binary fact. It has two arbiters, and best-practice facts can't be confirmed at all | A proof per kind, named in the provenance row. Behaviour proofs are binary-backed tests that run on every AD-5 version. Evals arbitrate skill output, never facts |
| S5 | Medium | epic 4 failure-mode story vs story 2.11 diagnosis references; any skill installed alone | Provenance has three homes (root `SOURCES.md`, the AD-11 entry's Source, and nothing in the installed skill). Row granularity differs. AD-15 allows support cases, but AD-11 requires a GitHub URL | `SOURCES.md` holds one row per (file, source, pin), synced into each skill. The AD-11 Source field covers failure-mode entries. Drop "support cases" until the Deferred item lands |
| S6 | Low | epic 5 rpcn-deploy (Helm) / epic 7 rpcn-migrate (Kafka Connect) vs either | The table has no row for facts outside RPCN (Helm, BYOC, Kafka Connect), or for Bloblang semantics, so any source is compliant | Add a fallback: a fact of an unlisted kind needs a table row first. Bloblang counts as behaviour |

---

## S1: One fact, two kinds, two sources, two homes (High)

**Rules involved:** AD-15's table maps "Behaviour: retry and backoff, ack and delivery, batching, `fallback`, ordering under `max_in_flight`" to the connect source, and "Best practice for Design, Deploy and Tune" to official docs and cookbooks. AD-2 forces one canonical source only for *files* used by more than one skill, not for *facts*. AD-7 has Design write Error handling, Delivery and ordering, and Idempotency, and has Test check the pipeline against those same sections.

**Compliant but divergent build:**
- **rpcn-design (epic 3)** writes `skills/rpcn-design/references/error-handling.md`. It is "best practice for Design", so it is distilled from the docs cookbook: "wrap the output in `fallback` with a DLQ second; `fallback` tries outputs in order and acks once any succeeds; set `max_in_flight: 1` for ordering". SOURCES.md row: docs URL. Compliant.
- **rpcn-test design check (story 2.10)** writes `skills/rpcn-test/references/design-check.md`. To decide `mismatch`, it needs what `fallback` and `max_in_flight` *do*. That is "behaviour", so it is distilled from `internal/impl/pure/output_fallback.go` at a tag. Say the source shows a subtlety the cookbook glosses over: ordering also depends on batching and the input's own concurrency, so `max_in_flight: 1` alone isn't enough. SOURCES.md row: connect tag. Compliant.
- **Result:** Design recommends a config as "ordered", and Test reports the same config as `mismatch` on Delivery and ordering. Both facts are sourced, proven (S4) and in separate hand-written files, so AD-2 doesn't apply. The user sees the chain contradict itself. That is AD-15's own "Prevents" case.

The same split happens for retry and backoff (the docs' recommended values vs the source defaults), for Tune vs Scale on batching, and for Author vs Design on idempotency keys.

**Smallest tightening (add to AD-15, under the table):**
- Classify by claim, not by the skill that uses it. A sentence about what the binary does (semantics, defaults, ordering, ack, error strings) is a behaviour fact and comes from the connect source, even inside a best-practice reference. Docs supply only the recommendation ("prefer X when Y"), and each recommendation cites the behaviour fact it rests on.
- A behaviour fact that more than one skill uses lives in exactly one file, `tools/shared/facts/<topic>.md`, which AD-2 syncs and drift-checks. A skill's hand-written reference links to that file and never restates it.

## S2: AD-11 generated vs AD-15 distilled: two owners for component facts (High)

**Rules involved:** AD-11: `gen_refs.py` writes `tools/shared/generated/` from `rpcn_check list` at the newest pin. Nobody edits it, and its deprecated marks drive the validator. AD-4: Author and Design check fields with `fields` (from `list --format json-full`, which carries defaults, descriptions and examples), not with generated refs. AD-15: "canonical config and test examples" come from the connect source at a pinned tag. "At runtime, the installed binary… is the only source a skill consults." Release sync "diffs the component specs" between pins.

**Compliant but divergent builds:**
1. **Defaults and examples.** Story 2.9 (Test writes `rpk connect test` cases) distills a canonical example from `config/test/*.yaml` at tag 4.115.0 into `references/test-cases.md`, including `max_in_flight: 64`. Story 2.6/2.7 (Author) takes the same default live from `fields` on the user's 4.100.0 binary, where it may differ. Both are compliant: AD-15 permits the distilled default, and AD-4 mandates the live one. The two skills disagree on a default, and only one of them came from the user's binary.
2. **The runtime sentence.** Read literally, "the only source a skill consults" bans reading `references/` at runtime, including the generated refs that AD-11, AD-12 ("warns before using its references") and AD-9 (generated refs are loaded at a step) all assume skills read. One rpcn-design story lists candidate components from `references/generated-inputs.json`, which is fine under AD-11 and AD-12. Another, written strictly to AD-15, calls `rpcn_check list` only. Two skills, two component catalogues, and both are compliant.
3. **Release sync.** One epic 4 story implements "diff the component specs" as a `git diff` of `tools/shared/generated/` between pins (the `list` output). Another diffs `internal/impl/**` spec definitions between connect tags (the AD-15 behaviour source). They flag different stale references. Neither can map a changed component to a hand-written reference anyway, because `SOURCES.md` rows name files and sources, not components.

**Smallest tightening:**
- AD-15, runtime bullet: "At runtime, a skill takes every fact the binary can report (components, fields, defaults, deprecation, lint and run results) from `rpcn_check`. Its `references/` supply only what the binary can't report. It never reads RPCN source, docs or the network."
- AD-11 owns everything `rpcn_check list`/`fields` reports. A hand-written or distilled reference never restates a field name, type, default or deprecation. It tells the reader to run `fields` instead. Distilled examples are config shapes that must lint on both pins (S4), with no default values stated in prose.
- Release sync diffs `tools/shared/generated/` between the old and new pin. Every `SOURCES.md` row names the components it covers, and release sync flags every row whose components changed.

## S3: Which pin? (High)

**Rules involved:** AD-15 says "distilled into `references/` at a pinned version" and "`redpanda-data/connect` source at a pinned tag". AD-5 pins 4.100.0 (floor) and a rolling newest (4.115.0 today, `tools/rpcn_versions.txt`). AD-14's weekly job rolls the newest. AD-13 installs the benchmark sets "at a recorded commit". The proof clause says "the binary's observed behaviour wins".

**Compliant but divergent builds:**
- **Story 2.7** distills Bloblang sample-runner behaviour from connect `v4.115.0`, the newest pin that week. **An epic 3 story** months later distills the same `fallback` behaviour from `v4.118.0` after two rolls. **A third story** picks `v4.100.0` "to match the floor". Each tag is "a pinned tag". Three references now describe three versions, and nothing marks the older ones as needing a re-check after a roll.
- `lint-errors.md` is adapted from `redpanda-data/skills` at `a4562333…`. AD-13 installs the `skills-repo` arm "at a recorded commit", which is never required to be the same commit. Phrasing gets adapted from one commit, and the benchmark compares against another. The R20 baseline then measures something other than what was adapted.
- **"The binary wins":** 4.100.0 and 4.115.0 can legitimately disagree, for example a lint message string reworded between versions, or a new default. One story ships the 4.115.0 behaviour ("newest is the reference build", AD-5). Another ships the 4.100.0 behaviour ("floor is the minimum"). A user on 4.108.0 matches neither, and both stories are compliant.

**Smallest tightening:**
- One pin registry, `tools/source_pins.toml`: `connect` = the AD-5 newest pin when the fact is written; `redpanda-data/skills` and the connect plugin = the commits AD-13's benchmark installs; docs = URL plus retrieval date. Every `SOURCES.md` row cites a pin from the registry. The weekly pin-roll PR lists the rows whose pin is now older (the S2 component diff narrows the list).
- "Observed behaviour" means observed on both AD-5 pins. A fact that differs between them ships version-qualified ("4.100.0: …; from 4.N: …"), or it is left out and the skill checks it at runtime through `rpcn_check`.

## S4: "Confirmed by a test or an eval" (High)

**Rules involved:** AD-15 Proof: "confirmed on 4.100.0 and the newest pin by a test or an eval before it ships. Where sources disagree, the binary's observed behaviour wins, and the evals are the final arbiter." AD-13: scenarios run locally, 3 times each, graded by `expect.toml`, lint, and a quality judgement. AD-14: CI runs `rpcn_check` unit tests on every AD-5 version but no evals. The Deferred section leaves open who runs evals for a pin-roll PR.

**Compliant but divergent builds:**
- **Story 2.10** confirms "an unresolved Deviations row covers a `fallback` mismatch" with a scenario: the skill writes a report, `expect.toml` matches `deviation-recorded`, and it passes 3/3 on both binaries. That proves the *skill* follows its reference. It proves nothing about `fallback`. If the reference is wrong, the eval was written from the same wrong reference, so it passes anyway. That counts as "confirmed by an eval".
- **Story 2.8** confirms "`run` with a bounded file exits after the input ends" with an `rpcn_check` unit test against both binaries in CI. That also counts as "confirmed by a test".
- Both are compliant. Only the second actually checked the binary, and only the second gets re-checked on a pin roll, because CI runs unit tests on every AD-5 version while eval re-runs for a roll are undecided.
- **Two arbiters:** "the binary wins" and "the evals are the final arbiter" disagree when an eval's LLM grader accepts output the binary contradicts. One story resolves toward the eval, another toward the binary.
- **Facts that can't be confirmed:** "Prefer a DLQ for poison messages" (best practice) and adapted phrasing have no binary behaviour to confirm. A strict story blocks shipping them. A lenient one calls any passing trigger eval a confirmation.

**Smallest tightening:**
- Replace the clause with a proof per kind, named in a new `SOURCES.md` column, **Proof**, that gives a test id:
  - Behaviour and lint strings: a binary-backed test (`tools/tests/` or `rpcn-test-skills` unit tests) that runs in CI on every AD-5 version, so a pin roll re-proves it.
  - Examples: the snippet lints (and, if it is a test case, passes `rpcn_check test`) on both pins.
  - Best practice and phrasing: there is no binary proof. Each item cites the behaviour fact it rests on (S1), and is checked by an eval scenario.
- One arbiter: the binary decides facts. Evals decide only whether a skill applies its references correctly.
- The validator fails on a behaviour or example row with no Proof.

## S5: Provenance in three places, at two granularities (Medium)

**Rules involved:** AD-15: "every adapted or distilled fact has a row in `SOURCES.md` giving the file, the source, the commit or tag, and the licence". Today's `SOURCES.md` says "Add one row per file", has columns File | Source | Licence | Notes, and puts the commit inside Source. AD-11: each failure-mode entry carries its own Source (a GitHub issue URL). AD-1: `npx skills` installs one skill folder alone. AD-15's table lists "resolved GitHub issues **and support cases**" for failure modes. AD-11 requires a GitHub URL, and the Deferred section says "Failure-mode sources beyond GitHub: later".

**Compliant but divergent builds:**
- **Granularity:** story 2.11 adds one `SOURCES.md` row per *fact* in `diagnosis.md` (20 rows), as AD-15 says. Story 2.7 adds one row per *file*, as `SOURCES.md` says. Both comply with a text. Release sync (S2) and pin re-checks (S3) can't treat the two the same way.
- **Two homes:** the epic 4 failure-mode story records each entry's issue URL in the entry, as AD-11 requires, and nothing in `SOURCES.md`. A second skill's failure-mode entries also get a `SOURCES.md` row per entry. Both are compliant, so a validator can't tell a missing row from a deliberate omission.
- **No home in the installed skill:** `SOURCES.md` lives at the repo root. AD-1 installs `skills/rpcn-test/` alone, so the adapted Apache-2.0 text in `lint-errors.md` ships without its attribution. One story fixes this with a `references/SOURCES.md` inside the skill. Another doesn't. Both comply.
- **Licence:** parts of `redpanda-data/connect` are under the Redpanda Community License, not Apache-2.0. The Licence column records the licence, but no rule says which licences may be distilled into an Apache-2.0 repo. One story copies an example from an enterprise component and another refuses to, and both comply.
- **Support cases:** an epic 4 story adds an entry from a support case, as AD-15 allows. Its Source can't be a GitHub URL, so it breaks AD-11. Another story refuses support cases, which follows AD-11 and the Deferred section. The ADs contradict each other.

**Smallest tightening:**
- Root `SOURCES.md` is the only register. It has one row per (file, source, pin), with columns File | Source | Pin | Licence | Components | Proof. That makes "every fact" "every file-source pair".
- `sync_shared.py` writes each skill's rows into `skills/rpcn-<job>/SOURCES.md`, and CI checks it for drift (AD-2).
- Failure-mode entries: each entry's AD-11 Source field is its provenance. `failure-modes.md` gets one `SOURCES.md` row, with Source "per entry".
- Allowed licences for distilled text: Apache-2.0, MIT or BSD. Anything else is paraphrased with no copied text, or left out.
- Drop "and support cases" from AD-15 until the Deferred item "Failure-mode sources beyond GitHub" is decided.

## S6: Facts with no table row (Low)

**Rules involved:** AD-15's table has four kinds. The Deferred section gives epic 5 the deployment specifics (Helm chart source, BYOC API or CLI) and epic 7 the Migrate mapping tables.

**Compliant but divergent builds:** rpcn-deploy takes Helm values from the chart repo at `main`, and rpcn-scale takes the same resource defaults from a docs page. rpcn-migrate maps Kafka Connect connector options from Confluent docs in one story and from connector source in another. Bloblang function semantics (story 2.7) could fit "behaviour" or no row at all. No row applies, so any source complies.

**Smallest tightening:** add a last table row: "Any other kind: add a row to this table (an AD-15 amendment) before the first story that writes it ships." Add "Bloblang functions and methods" to the behaviour row explicitly.

---

## What AD-15 gets right (keep)

- The binary is the runtime truth, consistent with AD-4 and the initiative constraints.
- One source per kind is the right shape. It only needs keying by claim (S1).
- It ties release sync to stale-reference detection, the missing half of AD-11.
- It keeps the benchmark sets as installed comparisons, not copied source (AD-13).

## Order of fixes

S2 and S4 change what stories 2.7–2.11 write and test, so settle them before story 2.7. S1 and S3 are needed before epic 3, when the second writer of Error handling and ordering facts appears. S5 can land with story 2.7's first `SOURCES.md` row. S6 can wait for epic 5.
