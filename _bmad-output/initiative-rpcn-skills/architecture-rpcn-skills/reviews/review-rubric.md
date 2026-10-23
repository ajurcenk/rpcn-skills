---
reviewer: rubric-walker
target: ARCHITECTURE-SPINE.md (draft, 2026-10-22)
inputs: initiative-rpcn-skills.md (R1-R19, Constraints, Notes), tickets/tickets.toml (epics 1-7), .memlog.md
date: 2026-10-22
---

# Rubric review: RPCN Skills architecture spine

## Verdict

**Revise before the epics start.** The paradigm (pipes and filters, one adapter) fits. AD-1 to AD-4 and AD-10 to AD-13 are mostly concrete and enforceable. The problems:

- **Contradictions inside the spine.** The plugin version cannot be read from inside a skill. The generated references break the one-level-deep rule.
- **Missing subcommand.** The check-script interface has no `run` subcommand, but R3 needs dry runs and AD-2 bans calling `rpk` any other way.
- **Copied content has no sync rule.** Only the check scripts are covered. Readiness lists, failure modes and generated references are not.
- **Thin operational envelope.** Nothing is decided about how CI gets the binaries, the parity corpus, eval credentials, the release mechanism, or the load-test environment for epics 5 and 6.

Severity: **High** means two epics will build the same thing differently, or an AD cannot be followed as written. **Medium** means a rule is not enforceable or a capability is not covered. **Low** means wording or completeness.

---

## 1. Divergence points: fixed and missed

### Fixed well
- **Install layout** (AD-1) and the **script copy and drift check** (AD-2). These close the `npx skills -s` subset risk logged in the memlog.
- **Check-script output envelope and exit codes** (AD-4). One JSON shape means Author, Test and Migrate parse results the same way.
- **Hand-off file names and frontmatter** (AD-6). These give every epic the same pipe names.
- **Design note sections and the Deviations rule** (AD-7). This is the exact seam between epics 2 and 3, and it is fixed before either starts.
- **Headless status block shape** (AD-8), and **eval layout plus the lint gate** (AD-13).

### Missed or only half fixed

**H1. `rpk connect test` case files have no owner or location (AD-6). High.**
- R3 has Test write `rpk connect test` cases. AD-6's table does not list them.
- RPCN lets tests live in the config's `tests:` key or in separate `*_test.yaml` files.
- If Test writes `tests:` into `<name>.yaml`, it edits Author's (or Migrate's) artifact. AD-6 forbids that, and AD-7's Deviations exception does not cover it.
- Epics 2 and 7 will each pick a different answer.
- **Fix:** add a row `<name>.tests.yaml` (or a `<name>.tests/` directory), written by rpcn-test. State that pipeline YAML never contains a `tests:` key. The validator or lint gate should reject `tests:` in generated pipeline configs.

**H2. Pipeline YAML and `<name>.deploy/` carry no readiness signal (AD-6, R16). High.**
- R16 says each hand-off file carries a `status`. AD-6 only gives frontmatter to Markdown files.
- Scale, Deploy, Tune and Migrate consumers (epics 5 to 7) need to know whether `<name>.yaml` has passed Test. Nothing says how they find out.
- One epic will gate on `test-report.status: ready`. Another will re-lint and carry on.
- **Fix:** state that `<name>.yaml` is consumable only when `<name>.test-report.md` has `status: ready` and its `rpcn_version` matches the installed binary.
- Give `<name>.deploy/` a `README.md` manifest with the AD-6 frontmatter (`artifact: deploy`), and add `deploy` to the `artifact` enum.

**H3. AD-6 readiness lists are copied with no source and no drift check. High.**
- "The reader copies it byte-for-byte into its own `references/`" has no canonical location, no sync tool and no CI check. Compare AD-2, which has all three.
- Build order makes this worse. Epic 2 (Author, a reader of `design-format.md`) ships before epic 3 (Design, the writer). So the writer's file does not exist when the reader copies it.
- The same gap applies to `references/failure-modes.md`. AD-11 doesn't say whether it is one shared list or a per-skill subset, or where its source lives. It also applies to `references/generated/`: which skills get a copy, and is it drift-checked?
- **Fix:** widen AD-2 into a general "synced content" rule.
  - Canonical formats go in `tools/formats/<artifact>-format.md`, owned by epic 1.
  - Failure modes go in `tools/failure-modes/` with per-skill tags.
  - Generated references go in `tools/generated/<version>/`.
  - `sync_scripts.py` (renamed `sync.py`) copies each item into the skills that declare it. The same drift check fails CI.

**H4. The plugin version is unreachable from inside a skill (AD-6 vs AD-1 and AD-12). High.**
- AD-6 needs `produced_by: rpcn-<job>@<plugin version>`.
- AD-12 says the version lives *only* in `.claude-plugin/plugin.json`.
- AD-1 forbids a skill from reading repo-root paths. Under `npx skills` that file is not installed at all.
- **Fix:** the release stamp (AD-12) also writes `metadata.plugin-version` into each SKILL.md. Better, it writes a constant into the synced `rpcn_check.py`, which `rpcn_check.py binary` then returns as `data.plugin_version`. Keep `plugin.json` as the single source that the stamp reads.

**H5. Version selection for `references/generated/` is undefined (AD-11, AD-12). High.**
- References are generated per pinned version (4.100.0, 4.112.0, and later pins).
- No rule says which set a skill loads for an installed binary of, say, 4.105.0. Two skills will choose differently.
- That violates the constraint that the binary is the source of truth.
- **Fix:** rule that a skill loads the highest pinned set that is less than or equal to the installed version. `rpcn_check.py binary` should compute this and return `data.refs_version` and `data.newer_than_refs`, so SKILL.md never does the comparison itself. That also makes AD-12's "warn when newer" enforceable in one place.

**M1. Tune's and Migrate's inputs are not named (AD-6).**
- Tune reads logs and metrics. Migrate reads Kafka Connect connector configs. Neither has a defined location, name or format.
- Epics 6 and 7 are separate, so the risk is lower. But R16 says "any stage can start from files alone", and Tune has no files to start from.
- **Fix:** add input rows, for example `<name>.metrics/` (a Prometheus scrape dump or log excerpt) for Tune, and `<connector>.connect.json` for Migrate. Or move both to Deferred, assigned to their epics, and say that is safe because each has a single reader.

**M2. Who applies Tune's recommendations is unstated.**
- If Tune edits `<name>.yaml` or `<name>.deploy/`, it breaks AD-6's own-artifact rule. If it does not, its Next step must hand off to Author or Deploy.
- **Fix:** one line in AD-6: Tune and Scale only write reports, and edits go through Author or Deploy, named in the Next step.

---

## 2. Is each AD's Rule enforceable, and does it prevent its divergence?

| AD | Enforceable? | Issue | Fix |
|---|---|---|---|
| AD-1 | Yes | The validator can scan for `../` and repo-root paths, but AD-14's validator list leaves this out. | Add "intra-skill path check" to AD-14's validator list. |
| AD-2 | Yes | Fine. | Widen to all synced content (H3). |
| AD-3 | Mostly | "standard library first" is not testable. | Say "standard library only, unless a dependency is declared in the PEP 723 header and listed in the AD-3 allow-list". The validator checks headers. |
| AD-4 | **Partly** | **No `run` subcommand.** R3 needs dry runs, AD-4 lists run flags, and AD-2 forbids running `rpk connect` outside `rpcn_check.py`. So Test cannot do a dry run without breaking AD-2. Also, `data: object` is unspecified per subcommand, so `list` and `test` results will be parsed differently by Author (R2 field checks), Design (AD-7 component checks) and Test. Arguments for `test` are not given. | Add `run` (with a timeout, `--set http.enabled=false`, and a bounded input such as the stdin-or-generate sample) and define each subcommand's `data` schema. State whether R2 field checks use the live `rpk connect list --format jsonschema` (the constraint says yes) or the generated references, for example a `fields <type> <name>` subcommand. |
| AD-5 | Partly | "Parity check" is named but not defined anywhere. The 15-config corpus is at `../rpcn-vscode-byoc-plugin/test/corpus`, which CI cannot reach. AD-14's PR list does not include the parity check. | Vendor the corpus into `tests/fixtures/vscode-corpus/` at a recorded extension commit, with expected results. Add a parity job to AD-14. |
| AD-6 | Partly | H1, H2, H3. | As above. |
| AD-7 | Yes | "every component named … is checked with `list`" has no enforcer, because Design is an LLM step. | The lint gate (AD-13) should also parse Components in eval-produced design notes and run `list`. |
| AD-8 | **No** | A SKILL.md cannot see `RPCN_HEADLESS`, because environment variables reach scripts, not skill bodies (memlog). "Prompt says unattended" is an assumption. Nothing in AD-13 grades the status block, which R17 requires for Test and Migrate. | `rpcn_check.py binary` returns `data.headless` from `RPCN_HEADLESS`, and every skill's first step calls `binary`. Add a regex or llm grader on the status block to AD-13 for Test and Migrate cases. Settle the assumption. |
| AD-9 | Partly | The size rule only warns. "Next … from that skill's own table" is vague. **It conflicts with AD-11:** `references/generated/<version>/…` is two levels deep, which breaks R9 and the Agent Skills one-level rule that AD-9 restates. | Flatten to `references/generated-<version>-<kind>.json`, or explicitly exempt generated references with a reason. Define the Next table format (situation → skill) and have the validator check that every named skill exists. |
| AD-10 | Yes | Nobody owns refreshing `clash-list.txt` when the coexisting sets change. | Give that to epic 4's scheduled job, or note it under Deferred. |
| AD-11 | Partly | R11's "CI blocks merges that **mention** removed or deprecated components" is not covered. The lint gate only checks eval outputs, not hand-written references, SKILL.md examples or failure-mode entries. | Validator rule: scan hand-written `references/` and SKILL.md for component names, and fail on any marked removed or deprecated in the newest generated set. |
| AD-12 | Partly | H4, H5. | As above. |
| AD-13 | Partly | No pass criterion for R12's "out-of-scope prompts trigger none". The 90% threshold covers in-scope only. R12 task cases with fixture files are not mentioned. The coexistence fixture does not pin which versions of `redpanda-data/connect` and `redpanda-data/skills` it installs. There is no pass rule for the baseline comparison. | Add: fail on any out-of-scope trigger (or set a stated threshold). Add task-case shape (`fixtures/`). Pin coexisting set refs in Stack. State the baseline rule, or say it is reported only. |
| AD-14 | Partly | See section 5. The parity check and path check are missing from the PR list. "Bumps the pin" conflicts with the constraint that pins match the extension. | Define the pin policy (section 5). |

---

## 3. Deferred items: could any let two epics diverge?

| Deferred item | Safe? | Note |
|---|---|---|
| Org-facts file | Mostly | Safe only if no epic invents its own registry or naming-rules input meanwhile. Add: "until decided, skills ask (or record an `open_question` when headless) and never write such a file." |
| Capacity model | Safe | Scale and Deploy are both in epic 5. But the `capacity.md` section shape should be fixed when epic 5 is refined, because Tune (epic 6) may read it. |
| Deployment specifics | **At risk** | Tune (epic 6) reads the deployed pipeline after epic 5. With no `deploy/` manifest (H2), epic 6 has to reverse-engineer epic 5's layout. Defer the internals, but fix the manifest now. |
| Migrate internals | Safe | Single owner. |
| VS Code code sharing | Safe | AD-4 copies its conventions. |
| Windows | Safe | Should be an open question with an owner, not an `[ASSUMPTION]` buried in Deferred. |
| More failure-mode sources | Safe | As long as H3 fixes the canonical location. |
| Telemetry | Safe | |

**Not deferred but should be** (silent today): the load-test environment, eval CI credentials and cost, the release mechanism, and CI binary acquisition. See section 5.

---

## 4. Capability coverage

| Req | Covered? | Gap |
|---|---|---|
| R1, R15 | Partly | R15 (under 10 minutes) has no architectural support: no eval case shape, no timing measurement. Add an end-to-end task case (Design → Author → Test) with a wall-clock grader, or name it a manual check. |
| R2 | Partly | Field-level checking is not in AD-4 (see the AD-4 row). |
| R3 | **No for dry runs** | Missing `run` subcommand. Test case files have no home (H1). |
| R4 | Thin | AD-6 and AD-9 only. Metric and log input is undefined (M1), and so is the measurement environment. |
| R5, R6 | Thin | The ±20% load-test check needs a cluster. Not decided, deferred or raised as a question. |
| R7 | OK | |
| R8 | OK | Plus H5. |
| R9, R19 | Partly | One-level conflict (AD-9 vs AD-11). |
| R10 | OK | Plus H3. |
| R11 | Partly | The removed-component scan of hand-written content is missing. |
| R12 | Partly | Out-of-scope criterion and task cases missing. |
| R13 | OK | |
| R14 | Partly | Corpus access and the parity job are undefined. |
| R16 | Partly | H1, H2, H3. |
| R17 | Partly | AD-8 is not enforceable, and there is no status-block grader. |
| R18 | Partly | H4. |

---

## 5. Operational envelope (the altitude owns these)

| Dimension | State | Finding |
|---|---|---|
| Environments | **Missing** | Developer machine only is implied. There is no decision on the Kubernetes or BYOC environment for the R5, R6 and R4 acceptance runs: kind/k3d in CI, a shared test cluster, or BYOC credentials. Epics 5 and 6 will each make one up. Decide, or log an open question owned by epic 5 that epic 6 inherits. |
| CI infra | **Assumed** | GitHub Actions is `[ASSUMPTION]`. Undecided: (a) how CI gets each pinned binary (GitHub release download plus checksum? a `redpanda-connect` image? `rpk` or the standalone binary?); (b) eval credentials (`ANTHROPIC_API_KEY` secret). Fork PRs cannot read secrets, so the "every PR" eval gate fails or skips there. Decide `pull_request_target`, a label gate, or maintainer-only runs. (c) Eval cost and runtime: 3 runs × every case × the coexistence variant on every PR. A budget or path filter is needed. (d) How the corpus is reached (see AD-5). |
| Release and distribution | **Underspecified** | What a "release" is (git tag? GitHub release? marketplace ref?) is undecided. `npx skills` and the marketplace (`source: "./"`) install from the default branch, so the AD-12 stamp only means something if the stamping commit lands on `main`. Decide: a release PR stamps SKILL.md metadata and `plugin.json`, merges, and is tagged `vX.Y.Z`. Say whether the marketplace entry pins a ref. Also define the pin policy: does the weekly job *add* pins (the matrix grows) or roll a "latest" pin while 4.100.0 stays the floor? Parity (R14) runs only on the extension's pins. |
| Operations | Thin | The scheduled RPCN-release job needs a detection source (the GitHub releases API on `redpanda-data/connect`) and a failure owner (who is told when the regen PR fails lint). Clash-list refresh has no owner. Failure-mode curation is manual by Aleksej, which is fine to state. |

---

## 6. Smaller items (Low)

- The Consistency Conventions "Script names" row has tests at `tests/test_<name>.py`, but the Structural Seed puts tests under `tools/rpcn_check/`. Pick one place for synced scripts, because tests must not be copied into skills.
- AD-8 `checks` covers only `lint` and `tests`. Add `blobl` and `parity`, or say the list is closed.
- The epic 1 "sample skill" (tickets) needs a name. If it is removed later, AD-12 says its name goes into `retired.toml` forever. Pick a name you are content to retire, or make the sample one of the real skills.
- AD-3 `compatibility` text is near the 500-character limit only if it grows. Fine for now.
- The Stack row "Agent Skills spec: current" is not a version. Pin a date or commit.
