---
reviewer: rubric-walker
target: architecture-rpcn-skills.md, AD-15 "Content sources" (uncommitted update, 2026-11-10)
inputs: initiative-rpcn-skills.md (Requirements, Notes), architecture .memlog.md (2026-11-10 entries), SOURCES.md, epic-author-and-test tickets.toml (stories 7-13), epic-release-sync.md
date: 2026-11-10
---

# Rubric review: AD-15 Content sources

## Verdict

**Revise before story 2.7 starts.** AD-15 fixes a real divergence point: stories 2.7 to 2.11 and epics 3 to 7 all write references, and nothing before AD-15 said where a behaviour fact or a best practice comes from. The table and the "binary wins" tiebreak are the right shape. Five things need tightening, though. The runtime rule as written contradicts the skills' own references. The table has no row for component facts. The table names support cases, which Deferred keeps out. Provenance is set at fact level but has no check. The proof rule has two arbiters and cannot apply to two of its own four rows.

Severity: **High** means two stories will read the AD differently, or the AD contradicts another AD or Deferred. **Medium** means a rule cannot be enforced or does not prevent what it says it prevents. **Low** means wording.

---

## 1. Does it fix a real divergence point?

Yes. The stories this AD governs make the problem concrete:

- 2.7 (Bloblang samples), 2.8 (dry runs), 2.9 (`rpk connect test` cases), 2.10 (checks against the design note's Error handling, Delivery and Idempotency) and 2.11 (diagnosis) all need behaviour facts: retry and backoff, ack semantics, `fallback`, ordering under `max_in_flight`, lint strings, test-file shape.
- Epic 3 (Design) and epics 5 and 6 (Deploy, Tune) need best practice.
- Epic 4 needs failure modes.

Without AD-15, one story could take `max_in_flight` ordering from a docs page and another from the Go source, and get different answers. So the AD earns its place. Its runtime half mostly restates AD-4 and the initiative Constraint ("the installed binary is the source of truth"). That is fine as a pointer, but see H1.

## 2. Is the Rule enforceable, and does it prevent the stated divergence?

### H1. The runtime rule contradicts the skills' own references (Rule, "At runtime"). High.

- The rule says the installed binary "is the only source a skill consults" at runtime.
- But at runtime every skill reads its own `references/`: the generated references (AD-11), `failure-modes.md`, and hand-written files such as `lint-errors.md` and `design-note.md`. AD-12 even says a skill "warns before using its references".
- That leaves two readings. (a) Binary-checkable facts come only from the binary, and everything else comes from `references/`. (b) Skills must not rely on references at all. Reading (b) breaks AD-9 and AD-11. A story writer who takes the rule literally may route every claim through `rpcn_check`, or decide that the references are only advisory.
- The rule is also silent on doc tools the agent may have at runtime. The memlog names the Redpanda Docs MCP as an authoring source, and a user's agent may have it installed. "Never read docs" doesn't say whether calling a docs MCP tool or a web fetch counts.
- **Fix:** "At runtime a skill uses two sources only. (1) The installed binary, through `rpcn_check` (AD-4), for every fact the binary can answer: components, fields, defaults, deprecation, lint, Bloblang output, run and test results. (2) Its own `references/` for everything else. When a reference disagrees with the binary, the binary wins and the skill says so (AD-12). Skills never fetch RPCN source, docs pages or doc tools (MCP or web) while they run."

### H2. The table has no row for component facts, and "pinned tag" isn't tied to AD-5 (Rule, table; AD-11). High.

- The table's first row sends "canonical config and test examples" to the `redpanda-data/connect` source. But component names, fields, defaults and deprecated status already come from the binary through `rpcn_check list` (AD-11) and `fields` (AD-4). The table doesn't say so. A writer distilling an example from the Go source might copy a field list from a spec file, and on 4.100.0 that list can differ from the binary's.
- "At a pinned version" and "at a pinned tag" are not tied to anything. AD-5 has two pins, and the generated references use the newest only. Story 2.9 could take test-file shape from `v4.115.0` while 2.11 takes lint strings from `v4.100.0`. That is the divergence the AD is meant to prevent.
- **Fix:**
  - Add a first row: "Components, fields, defaults, deprecated or removed status: the binary, through `rpcn_check list`/`fields`. Generated (AD-11), never distilled."
  - Define the pin: "The pinned tag is the newest pin in `tools/rpcn_versions.txt` when the reference is written, recorded in its SOURCES.md row. A fact that differs between 4.100.0 and the newest pin is written once per version."

### M1. Provenance is set at fact level but checked by nothing (Rule, "Provenance"; SOURCES.md; AD-14). Medium.

- The rule says "every adapted or distilled fact has a row in SOURCES.md". The existing `SOURCES.md` (repo root) says "Add one row per file" and has the columns File | Source | Licence | Notes, with no commit or tag column. Its one row puts the commit inside Source. The rule and the file already disagree on granularity and columns.
- A row per fact cannot be enforced or reviewed. Nothing in AD-14's validator list checks SOURCES.md, and the Structural Seed doesn't list it.
- Licence: the initiative Decision (2026-10-23) says Connect files are "checked for Apache-2.0 vs the Redpanda Community License". AD-15 records the licence but doesn't say what an RCL file permits. This matters most for row 1, the Connect source, where enterprise components are RCL.
- **Fix:**
  - One row per (reference file, source), with the columns File | Source | Commit or tag | Licence | Notes.
  - Add SOURCES.md to the Structural Seed.
  - Add to AD-14's validator: every hand-written `references/*.md` either has a SOURCES.md row or is marked original, and every row's File exists.
  - State: "RCL-licensed files may inform facts, but their text is never copied into the repo."

### M2. The proof rule has two arbiters and doesn't fit two of its four rows (Rule, "Proof"). Medium.

- "Confirmed on 4.100.0 and the newest pin by a test or an eval" works for behaviour facts and lint strings. It doesn't work for:
  - best practice from the docs ("put a DLQ on X"), which is a recommendation the binary can't confirm
  - failure modes whose "Fixed in" (AD-11) is a version between the pins. Such an entry is true on one pin and false on the other by design.
- "The binary's observed behaviour wins, and the evals are the final arbiter" names two arbiters. When a scenario passes with a claim that a binary probe contradicts, the reader can't tell which one wins.
- "Before it ships" doesn't say which test or eval, or where that link is recorded. That leaves no evidence a reviewer can check.
- **Fix:**
  - Scope the proof by row. Behaviour facts and lint strings each cite a `rpcn_check` test or scenario (in SOURCES.md Notes) that passes on both pins. Best practice is proved only through the AD-13 scenario gate. Failure modes are proved by their Source and Fixed-in fields.
  - One precedence: "For facts the binary can show, observed behaviour wins over every source. For everything else, the AD-13 evals decide."
  - Add the tiebreak between rows: "A statement about what RPCN does is a behaviour fact (row 1) even inside Design, Deploy or Tune guidance. Docs supply recommendations only." Without it, Design's retry and batching advice (AD-7 sections 5 and 8) falls under both row 1 and row 2.

## 3. Contradictions or overlaps with AD-4, AD-5, AD-11, AD-13, AD-14

| AD | Relationship | Two readings? |
|---|---|---|
| AD-4 | The runtime half restates AD-4's adapter role. Consistent with "Author and Design use `fields`, not the generated references". | Yes, through H1: "only source" versus references read at runtime. |
| AD-5 | Proof on both pins matches AD-5. "Pinned tag" is undefined against AD-5's two pins. | Yes, H2. |
| AD-11 | AD-11 owns generated content and the failure-mode entry shape. AD-15's table omits generated content (H2). AD-15's failure-mode row adds "support cases", but AD-11's Source field is "a GitHub issue URL" only, so a support case can't be written in the AD-11 shape that AD-15 cites (H3). | Yes. |
| AD-13 | Row 4 names the AD-13 arms as a source of "adapted phrasing". AD-13 says the benchmark sets "are never copied into `rpcn-skills`". The initiative Decision (2026-10-23) allows adapting pieces, and SOURCES.md already has one. So AD-13's "never copied" now reads as a ban that AD-15 overrides. Adapting a competitor arm's phrasing also narrows the R20 comparison, which is worth one line. | Yes (L1). |
| AD-14 | "Release sync (epic 4)" overlaps AD-14's weekly job (`gen_refs` and the pin roll) without saying it is the same job. A component-spec diff can't find stale behaviour facts distilled from the Go source (row 1), so it doesn't fully prevent stale references. | Partly (M3). |

### M3. Release sync finds only part of what goes stale (Rule, "Release sync"; AD-14 weekly job). Medium.

- A diff of component specs between pins catches field and default changes. It misses changes to retry, ack or ordering behaviour, and to lint strings, which is row 1 of the table and the content most likely to go stale.
- The rule doesn't say what the diff runs through or what it produces. AD-2 requires `rpcn_check` for any binary call. The output could be a failing check, a PR comment or an issue.
- **Fix:** "The AD-14 weekly pin-roll job diffs `rpcn_check list` output between the previous and new pin. It lists in the pin-roll PR every reference whose SOURCES.md row names a changed component, and every row-1 fact whose proving test fails on the new pin."

## 4. Coverage of the bound requirements

| Req | Covered? | Note |
|---|---|---|
| R8 | Yes | The runtime rule reinforces AD-4. The proof rule adds both-pin confirmation for distilled facts. |
| R10 | Partly, with a conflict | Row 3 names "support cases". AD-11's shape can't hold them, and Deferred keeps them out (H3). R10's "starting with GitHub issues" fits a GitHub-only row for version 1. |
| R11 | Partly | The release sync names the stale-reference search but only for component specs (M3). Deprecated-component blocking stays with AD-11 and AD-14, which is fine. |
| R20 | Thin | AD-15 only names the arms as a phrasing source. It adds nothing to R20's "every scenario another arm wins becomes an improvement story". Either drop R20 from Binds or add: "an improvement story from a lost benchmark scenario takes its facts from the table above, not from the winning arm's text." |

## 5. Deferred conflicts

### H3. "Support cases" contradicts Deferred and the epic 4 Boundary (Rule, table row 3; Deferred "Failure-mode sources beyond GitHub"). High.

- Deferred says "Failure-mode sources beyond GitHub: later, using the AD-11 entry shape". `epic-release-sync.md` Boundaries: "Out: … failure-mode sources beyond GitHub". AD-15's row 3 says "Resolved GitHub issues and support cases".
- Epic 4's curation story could take either reading.
- **Fix:** row 3 should read "Resolved `redpanda-data/connect` GitHub issues, in the AD-11 entry shape. Support cases come later (Deferred)."

### M4. Proof on both pins makes the open pin-roll question harder (Deferred "Release stamp and the eval record (open)"). Medium.

- AD-15 requires every fact to be confirmed on the newest pin "before it ships". When the weekly job rolls the pin, every behaviour fact must be re-proved on the new pin. That means a local eval or test run on the pin-roll PR, which is exactly the open question of who runs evals for a pin-roll PR.
- This doesn't contradict Deferred, but AD-15 adds load to it without saying so.
- **Fix:** add one line to that Deferred item: "AD-15's proof rule means a pin roll re-proves row-1 facts. Epic 4 decides whether that runs as `rpcn_check` unit tests in CI, which need no Claude credentials, or as a local eval."

### L1. AD-13 "never copied" versus AD-15 adapted phrasing (AD-13 "Benchmark sources"). Low.

- **Fix:** change AD-13 to "never installed in or vendored into `rpcn-skills`. Pieces adapted from them follow AD-15 provenance."

### L2. The Redpanda Docs MCP was dropped between the memlog and the AD. Low.

- The memlog decision names "official docs/cookbooks (incl. Redpanda Docs MCP)". The AD says "Official docs and cookbooks". That's fine for authoring. Once H1 is fixed, the runtime ban on doc tools covers the MCP explicitly.

---

## Summary of fixes

1. H1: rewrite "At runtime" as two sources (the binary for checkable facts, the skill's own `references/` for the rest), with the binary winning, and ban runtime doc tools and fetches.
2. H2: add a component-facts row pointing to AD-4 and AD-11 (generated, not distilled), and define "pinned tag" as the newest pin in `tools/rpcn_versions.txt`, recorded in SOURCES.md.
3. H3: restrict row 3 to GitHub issues for version 1, matching AD-11, Deferred and epic 4.
4. M1: one SOURCES.md row per (file, source) with a Commit or tag column, add a validator check, add SOURCES.md to the seed, and state the RCL rule.
5. M2: scope the proof by row, name one precedence, and add the behaviour-versus-recommendation tiebreak.
6. M3: tie the release sync to the AD-14 weekly job, and make it flag row-1 facts as well as spec changes.
7. M4, L1, L2: a one-line Deferred note, the AD-13 wording, and the MCP mention.
