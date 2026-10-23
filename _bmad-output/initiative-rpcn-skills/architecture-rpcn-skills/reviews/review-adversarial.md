---
type: review
lens: adversarial (compliant-but-incompatible units)
target: _bmad-output/initiative-rpcn-skills/architecture-rpcn-skills/ARCHITECTURE-SPINE.md
inputs:
  - _bmad-output/initiative-rpcn-skills/initiative-rpcn-skills.md
  - _bmad-output/initiative-rpcn-skills/tickets/tickets.toml
created: '2026-10-22'
verdict: 'Not ready to bind epics: the spine fixes file names and one script, but leaves format-doc ownership, multi-writer files, version skew and the check-script data contract open, so compliant epics can still ship incompatible pieces.'
---

# Adversarial Review — RPCN Skills Architecture Spine

## Verdict

**Revise before epics 2-3 start.** AD-2 (one script source, drift check) is the strongest rule in the spine. The spine does not apply the same discipline to the other things skills share: format docs, the design note, the pipeline YAML, the unlisted side files (mappings, resources, env files, test files), version identity and the `data` payload of the check script. In each of the pairs below, both epics follow every AD to the letter and still produce pieces that do not fit together.

Severity scale: **High** means the tracer path (Design → Author → Test → Scale → Deploy → Tune) breaks or gives silently wrong results. **Medium** means rework or CI churn between epics. **Low** means friction.

## Summary

| # | Sev | Units | Hole | Closing rule (short) |
|---|---|---|---|---|
| H1 | High | epic-design vs epic-author-and-test (and epic-validation-foundation) | Format docs are copied by readers, but have no canonical source, no drift check and no version | AD-6a: canonical `tools/formats/`, synced and drift-checked like AD-2, plus a `format:` version |
| H2 | High | epic-design vs epic-author-and-test | The design note has two writers, and no merge rule for re-runs, `updated`, status or how Test reads Deviations | AD-7 tightened: Deviations are append-only and structured, Design preserves them, Author may touch only `updated`, Test skips mismatches that have a deviation entry |
| H3 | High | epic-author-and-test vs epic-tune / epic-migrate / epic-deploy-and-scale | `<name>.yaml` has several writers, no status and no readiness, while Tune, Test-fix and Deploy all need to change it or gate on it | AD-6b: Author is the sole YAML writer (Migrate only creates new files), YAML readiness = test-report `ready` with a matching hash, Tune and Test only recommend |
| H4 | High | epic-validation-foundation vs epic-release-sync (and installs via `npx skills -s`) | `produced_by` needs a plugin version that AD-1 makes unreadable, and skills installed at different versions mix script and format versions | AD-12 tightened: release stamps `metadata.plugin-version` into each SKILL.md, the envelope and frontmatter carry schema versions, and readers reject an unknown major |
| H5 | High | every reader vs every writer (e.g. epic-tune vs epic-deploy-and-scale) | `ready` never goes stale: an upstream rewrite leaves downstream `ready` files valid | AD-6c: `inputs: [{file, sha256}]` in frontmatter, and a reader treats a hash mismatch as not ready |
| H6 | Med-High | epic-author-and-test vs epic-validation-foundation (and epic-release-sync) | AD-4 defines `run` flags but has no `run` subcommand, `data` is untyped, and `gen_refs.py` calls `rpk` on its own | AD-4 tightened: add a `run` subcommand, a `data` schema per subcommand, all binary access through the `rpcn_check` module |
| H7 | Med-High | epic-author-and-test vs epic-migrate vs epic-deploy-and-scale | Unlisted shared files (mappings, resources, env file, `.env.example`, test files) have no names or owners, so under AD-6 nobody may write them | AD-6 table extended with fixed names and one writer for each |
| H8 | Medium | epic-release-sync vs epic-author-and-test | `references/generated/` layout and `failure-modes.md` content have two de facto owners, and nothing says which pinned version's references to load | AD-11 tightened: epic 1 owns the `gen_refs` layout, failure modes have a canonical tagged source that is synced, `rpcn_check binary` returns the refs dir |
| H9 | Medium | epic-validation-foundation vs epic-release-sync | Two epics build `validate_skills.py` | AD-14: one owner, and the checks are a registry |
| H10 | Medium | epic-deploy-and-scale / epic-tune vs epic-author-and-test | Adding a skill means editing existing skills' Next, Not-for and evals. The AD-6 "own artifact" rule covers only hand-off files, so nothing says who may make these edits | AD-9 tightened: Next and Not-for may name only shipped skills, and the PR that adds a skill updates its siblings |
| H11 | Medium | epic-design vs epic-author-and-test (headless) | `complete` vs `blocked` and draft vs ready are each decided per skill, so headless chains stall or skip gates | AD-8 tightened: a decision table |
| H12 | Low | epic-validation-foundation vs any skill epic | `evals/<skill>-<case>/` cannot be split reliably (skill names contain `-`) | AD-13: `evals/<skill>/<case>/` |

---

## H1 — Format docs: copied, but nothing keeps the copies in sync (High)

**Rules involved:** AD-6 says the readiness list lives in the writer's `references/<artifact>-format.md` and the reader copies it "byte-for-byte into its own `references/`". AD-1 forbids reading a sibling's folder. AD-2 has a sync tool and a CI drift check, but only for `rpcn_check`.

**Compliant but incompatible build:**
- **epic-validation-foundation** "defines hand-off formats" and uses them in a sample skill. Its `design-format.md` sits in the sample skill.
- **epic-author-and-test** ships before Design exists (initiative Decision: epic 2 before epic 3). It copies `design-format.md` byte-for-byte from the sample skill into `skills/rpcn-author/references/` and `skills/rpcn-test/references/`.
- **epic-design** is the writer, so AD-6 makes it the owner of `design-format.md`. While refining R1 it adds an `Idempotency` section and a readiness item ("every output names its delivery guarantee"), and edits *its own* `design-format.md`. That is legal.
- Author and Test still carry the old copy. No CI check compares them. Author accepts notes Design would call not ready, and Test checks against the old sections.

The same thing happens with `test-report-format.md` (writer rpcn-test, readers rpcn-scale and rpcn-deploy) and `capacity-format.md` (writer rpcn-scale, reader rpcn-deploy, and rpcn-tune if it reads capacity).

There is a second hole inside this one: AD-7 fixes the design sections in the spine, while AD-6 says the format doc is the authority. When the two disagree, nothing says which wins.

**Closing rule — AD-6a, format docs are synced like scripts:**
- The canonical source of every hand-off format is `tools/formats/<artifact>-format.md`. Each one declares a `format: <artifact>@<major>.<minor>` in its own frontmatter, and its owner epic is the writer skill's epic.
- `tools/sync_scripts.py` (rename it `sync_shared.py`) copies each format doc into the writer and every reader listed in a `tools/formats/readers.toml`. CI fails on drift, as in AD-2.
- Every hand-off file carries `format: <artifact>@<major>.<minor>`. A reader rejects a different major, and accepts a newer minor while ignoring unknown sections.
- AD-7's section list is the content of `design-format@1`. Changing it is a format bump, not a spine edit.

## H2 — The design note has two writers and no merge rule (High)

**Rules involved:** AD-6 says only the writer edits its artifact, "except AD-7". AD-7 lets Author append a Deviations entry (what, why, date) and says "that is the only edit another skill may make to it". AD-6 requires `updated: <ISO date>`.

**Compliant but incompatible build:**
- **epic-author-and-test**: Author appends a deviation (for example, it used `retry` with a cap instead of the DLQ the note asked for, because the output does not support DLQ on 4.100.0). AD-7 says this is the *only* edit, so Author leaves `updated` stale and leaves `status: ready`.
- **epic-design**: the developer re-runs Design to change Batching. Design owns the file and rewrites it from its template, and the Deviations section comes back empty. That is legal, because Design creates and updates its own artifact. Author's recorded deviation is gone, and nothing marks the YAML as diverging.
- **Test** (epic-author-and-test) checks the pipeline against Error handling. It finds no DLQ and reports a mismatch, even though a deviation was recorded. Or, in a different build of the same epic, Test reads Deviations as prose and suppresses the mismatch. Both builds comply with AD-7.

Also, `status: superseded` has no defined writer or trigger, because there is only ever one file per name.

**Closing rule — AD-7 tightened:**
- Deviations entries are structured and append-only: `- section: <AD-7 section>; what: …; why: …; date: <ISO>; by: rpcn-author@<ver>`.
- Design must preserve every existing Deviations entry when it rewrites the note. When it changes a section that a deviation refers to, it adds `resolved: <date>` to that entry. It never deletes one.
- When Author appends, it may also set `updated`. It may not touch any other frontmatter field.
- Test reports a mismatch in a section as `deviation-recorded` (not a failure) when there is an unresolved deviation for that section. Otherwise it reports `mismatch`.
- `superseded` is used only on a file that is moved aside as `<name>.<artifact>.<date>.md`. In-place rewrites keep `draft` or `ready`.

## H3 — `<name>.yaml`: several writers, no status, and changes that have no path (High)

**Rules involved:** AD-6 lists `rpcn-author, rpcn-migrate` as YAML writers and says "a skill only creates or updates its own artifact". YAML cannot carry the Markdown frontmatter, so it has no `status`. AD-6's readiness rule applies only to "an input file … when its `status` is `ready`".

**Compliant but incompatible builds:**
- **epic-tune**: R4 is met only when the changes "measurably raise throughput". Tune may not edit the YAML (it is not Tune's artifact), so it writes `tune-report.md` with recommended patches. One build of **epic-author-and-test** has Author read `tune-report.md` as an input. Another build does not, and Author knows nothing about Tune reports. Both comply. The tune loop works in one and is a dead end in the other.
- **epic-author-and-test** (Test): R3 requires "a fix that passes". Test may not edit the YAML. Also, `rpk connect test` cases can live either inside the config (`tests:`) or in a separate `*_test.yaml`. A Test build that writes `tests:` into `<name>.yaml` becomes a third YAML writer. A build that writes a separate file creates a file that AD-6 does not list (see H7).
- **epic-migrate**: Migrate writes `<name>.yaml` for a connector whose name matches an existing Author pipeline, and overwrites it. Both are listed writers, so this is legal.
- **epic-deploy-and-scale**: Deploy needs metrics and http settings for Tune (for example, a `metrics.prometheus` exporter, or `http.enabled=true` in-cluster). It cannot change the YAML, so it either overrides those settings in the manifests or silently changes the YAML.
- **Readiness**: Scale and Deploy read the YAML. It has no status, so one reader treats "exists" as ready, and another requires `test-report.status == ready`.

**Closing rule — AD-6b, pipeline config ownership:**
- `rpcn-author` is the only skill that updates an existing `<name>.yaml`. `rpcn-migrate` only *creates* new configs and refuses (or headless-blocks) when the target exists.
- Test, Tune and Deploy never edit the config. They write proposed changes as a `## Proposed changes` section in their own report, as unified diffs. Author's input list includes `test-report.md` and `tune-report.md`, and it applies those diffs as edits.
- Deploy-only overrides (http, metrics, replicas) live only under `<name>.deploy/` as overlay or `--set` values, never in the config.
- `rpk connect test` cases go in `<name>_test.yaml` (listed in AD-6, writer rpcn-test). Author never writes `tests:`.
- The config counts as ready only when `<name>.test-report.md` is `ready` and its `inputs` hash matches the current YAML (see H5).

## H4 — Plugin version cannot be read, and versions skew across skills (High)

**Rules involved:**
- AD-6 requires `produced_by: rpcn-<job>@<plugin version>`.
- AD-12 says "the plugin version lives only in `.claude-plugin/plugin.json`", and the release stamps only `rpcn-refs-version`.
- AD-1 forbids repo-root reads, and through `npx skills` there is no `plugin.json` at all.
- AD-2 guarantees identical scripts *inside one repo commit*, not on a user's machine.

**Compliant but incompatible builds:**
- **epic-validation-foundation** builds the sample skill to write `produced_by: rpcn-sample@unknown`, because it cannot read `plugin.json`.
- **epic-release-sync** has the release add `metadata.version` to each SKILL.md and expects `produced_by` to carry it. That contradicts AD-12's "lives only in plugin.json". So does the alternative, a `version` in `marketplace.json`.
- A user runs `npx skills add … -s rpcn-author` at 1.3.0, and later `-s rpcn-test` at 1.1.0. AD-2 holds in both releases, but the user's machine now has two `rpcn_check.py` versions. If the 1.3 envelope added a field, or the format docs moved (H1), Test 1.1 parses Author 1.3's files with no way to notice. `produced_by` is free text, and nothing reads it.

**Closing rule — AD-12 tightened:**
- `plugin.json` is the *source* of the version. The release stamps `metadata: { plugin-version, rpcn-refs-version }` into every SKILL.md, and the validator checks that they equal `plugin.json`. A skill reads its own SKILL.md metadata, never `plugin.json`.
- The AD-4 envelope gets `"schema": "rpcn-check@<major>"`, and hand-off files get `format:` (H1). Compatibility is decided on these fields, never on `produced_by`.
- A reader that sees an unknown major `format` tells the user to update all `rpcn-*` skills together. In headless mode it ends `blocked`.

## H5 — `ready` never goes stale (High)

**Rules involved:** AD-6 status is set only by the writer, and no rule says that changing an upstream file invalidates a downstream one.

**Compliant but incompatible build:**
- **epic-tune** recommends raising `batching.count` and threads, and Author applies the change.
- **epic-deploy-and-scale**: `capacity.md` (status `ready`) and `test-report.md` (status `ready`) still describe the old config. Deploy obeys AD-6, because every input is `ready`, and ships the stale memory request. R6's ±20% check fails, and every skill followed the rules.
- The same thing happens when Design is re-run (H2): `test-report.md` stays `ready` against a changed note.

**Closing rule — AD-6c, provenance hashes:**
- Every Markdown hand-off adds `inputs: [{file: <relative path>, sha256: <hex>}]` listing exactly the files it was produced from.
- A reader treats an input as not ready when any listed hash differs from the current file. It tells the user which upstream skill to re-run (its Next step). In headless mode it ends `blocked`, with reason `stale:<file>`.
- `rpcn_check.py` gets a `hash <files…>` subcommand, so every skill computes hashes the same way. Skills must not shell out to `sha256sum`, in keeping with AD-3's no-`jq` spirit.

## H6 — Check-script contract gaps: `run`, `data`, and a second binary path (Medium-High)

**Rules involved:**
- AD-4 lists the subcommands `binary | lint | blobl | list | test`, but defines argument mirroring for `run`.
- R3 requires dry runs.
- The envelope's `data` is just `object`.
- AD-2's "No skill runs `rpk connect` except through `rpcn_check.py`" applies to skills only. AD-11 has `tools/gen_refs.py` run `rpk connect list --format jsonschema`.

**Compliant but incompatible builds:**
- **epic-author-and-test** needs dry runs. It cannot call `rpk`, so either it adds `run` to `tools/rpcn_check` (and changes the epic 1 interface after epic 1 closed), or it fakes a dry run with `test`. A later **epic-migrate** build relies on whichever exists.
- `list`: AD-7 has Design check every component "with `rpcn_check.py list`". Epic 1 implements `list` to return every component (`data: {components: [...]}`). Epic 3's SKILL.md tells the model to call `list <component>` and read `data.exists`. Both follow AD-4, because `data` is "object".
- **epic-release-sync** writes `gen_refs.py` with its own binary lookup (it runs the pinned binary directly, ignores `RPCN_BINARY`, and parses the version differently). The generated references and the check script can then report different versions for the same machine. AD-12's newer-binary warning compares values that were never produced the same way.

**Closing rule — AD-4 tightened:**
- The subcommands are `binary | lint | blobl | list | test | run | hash`. `run` uses the mirrored flags with a bounded timeout and returns the processed messages in `data`.
- `tools/rpcn_check/SCHEMA.md` fixes `data` for each subcommand. Examples: `list`: `{components: [{type, name, status}]}`, with an optional `--name` filter. `binary`: `{refs_dir, newer_than_refs: bool}`. Unit tests assert the schema. SCHEMA.md is synced into skills with the script (AD-2).
- Every tool in `tools/` that touches the binary imports `tools/rpcn_check` for lookup and version parsing. No second implementation is allowed.

## H7 — Shared files that nobody owns (Medium-High)

**Rules involved:**
- AD-6 lists the files skills write, and "a skill only creates or updates its own artifact".
- The secrets convention requires `.env.example`.
- AD-4 passes `--resources <file>` and `--env-file <file>`.
- AD-13 lints "every YAML and mapping file".

None of these are in the AD-6 table: Bloblang mapping files, resource file names, the env file, `.env.example`, or `rpk connect test` files. Under a strict reading, no skill may create them.

**Compliant but incompatible builds:**
- Mappings: **epic-author-and-test** writes `mappings/<name>.blobl`, and **epic-migrate** writes `<name>.mapping.bloblang`. The AD-13 lint gate built in **epic-validation-foundation** globs `*.blobl` and misses Migrate's mappings, so the 100% lint gate passes on unlinted files.
- Resources: Author writes `resources/*.yaml`, and Migrate writes `<name>.resources.yaml`. Test has to find them to pass `--resources`, and each build guesses differently.
- `.env.example`: one file per project, shared by every pipeline. Author (epic 2), Migrate (epic 7) and Deploy (epic 5) all add names to it. Under AD-6 none of them owns it. If one build regenerates it, another pipeline's variables disappear.
- The env file: Test passes `--env-file .env`, while Deploy expects `<name>.env`.

**Closing rule — extend the AD-6 table (fixed names, one writer each):**

| File | Writer | Readers |
|---|---|---|
| `<name>.mappings/<mapping>.blobl` | rpcn-author (rpcn-migrate on create) | test, lint gate |
| `<name>.resources.yaml` (one file) | rpcn-author (rpcn-migrate on create) | test, deploy |
| `<name>_test.yaml` | rpcn-test | test |
| `<name>.env.example` (per pipeline, names only) | rpcn-author (rpcn-migrate on create) | test, deploy |

- The env file passed to `--env-file` is the developer's `<name>.env`, and no skill ever writes it.
- The AD-13 lint gate takes its globs from this table, from one constants module in `tools/`.

## H8 — Generated references and failure modes: two owners and no selection rule (Medium)

**Rules involved:** AD-11 says `gen_refs.py` writes `references/generated/` "for each pinned version", and puts `failure-modes.md` in each skill. R11 and R10 belong to **epic-release-sync**, which comes after epic 2.

**Compliant but incompatible build:**
- **epic-author-and-test** needs generated component facts for R2 now. It writes a first `gen_refs.py` (or hand-commits JSON) as `references/generated/components.json`.
- **epic-release-sync** later owns `gen_refs.py` and writes `references/generated/4.112.0/inputs/kafka_franz.json`. Author's SKILL.md step "load `references/generated/components.json`" now points at nothing. The validator's file-reference check catches this only after the change has merged.
- Version selection: with a binary at 4.105.0, Author loads the 4.100.0 refs (the nearest lower) while Test loads 4.112.0 (the newest, as AD-12's stamp implies). The two disagree about whether a field exists.
- Failure modes: Test writes its own diagnosis entries (R3) into `rpcn-test/references/failure-modes.md`. Release-sync mines GitHub into each skill's `failure-modes.md` and overwrites it, or both edit the same entry differently in two skills. There is no canonical source, and copies of one entry drift.

**Closing rule — AD-11 tightened:**
- **epic-validation-foundation** owns `gen_refs.py` and the layout `references/generated/<version>/<type>/<name>.json` plus `index.json`. **epic-release-sync** only schedules it and bumps pins.
- `rpcn_check.py binary` returns `data.refs_dir`, chosen as the highest pinned version not above the binary's version (or the lowest pin if the binary is older). All skills load that directory and nothing else.
- Failure modes have one canonical file, `tools/failure-modes/<id>.md`, each with `skills: [rpcn-…]` tags. The sync tool assembles each skill's `failure-modes.md` from it. Skills never edit their copy, and drift is checked in CI.

## H9 — Two builders of the validator (Medium)

**Rules involved:** epic 1 covers R9, R12 and R19 ("the convention, harness and CI"), and that includes size and description checks. Epic 4 covers R18 ("A CI validator checks names, descriptions and file references"). AD-14 names one `tools/validate_skills.py`.

**Divergence:** epic 1 builds `validate_skills.py` with size and description checks. Epic 4 builds the names, clash-list and retired checks either as a second script or by rewriting the first, with different output and exit codes. CI ends up with two gates that disagree on what a "description" is (for example, whether "Not for" is required when no sibling collides).

**Closing rule — AD-14 tightened:** **epic-validation-foundation** owns `validate_skills.py` as a registry of named checks, each one a function reporting through the AD-4 `errors` shape. Later epics add checks; they never fork the script. The tickets should say so in epic 4's `after` needs.

## H10 — New skills must edit existing skills, and no rule says who may (Medium)

**Rules involved:**
- AD-9 requires Next to name siblings from "that skill's own table" and needs Not-for lines for "each colliding sibling".
- AD-13 needs near-miss negatives for every sibling named in Not-for.
- The validator checks file references.

**Divergence:**
- **epic-author-and-test** ships Test with a Next row "load-ready → rpcn-scale", although rpcn-scale does not exist until epic 5. The validator either fails it (as a dangling reference) or passes it (because it checks only file references). Users who installed with `npx skills -s` are pointed at a skill they do not have.
- **epic-deploy-and-scale** adds rpcn-deploy, which collides with Test on "check my config before shipping". It must add a Not-for line to rpcn-test, plus new negatives in `evals/rpcn-test-*`. The spine says nothing about whether epic 5 may change epic 2's SKILL.md and evals. One build does it, and another leaves Test's trigger accuracy to drop under the coexistence fixture.

**Closing rule — AD-9 tightened:**
- Next and Not-for may name only skills present under `skills/`. The validator enforces this.
- Next must say what to do when the named sibling is not installed ("install rpcn-<x>").
- The PR that adds a skill must update every colliding sibling's Not-for lines and evals, and the eval gate runs on all skills on every PR. This is the one sanctioned cross-skill edit in the repo, and it is the repo-level counterpart of AD-6's file ownership.

## H11 — Headless semantics decided per skill (Medium)

**Rules involved:**
- AD-8 says the skill "never asks, each gap becomes `open_questions`".
- AD-7 says a note is `ready` only when Open decisions holds nothing that blocks Author.
- The status block has `checks.lint` and `checks.tests`, but no Bloblang check.

**Divergence:**
- **epic-design**, headless with gaps, writes the note `status: draft` and ends `complete` with open questions. **epic-author-and-test**'s Author, headless, sees `draft`, ends `blocked`, and the CI chain stops.
- Another Design build resolves the gaps with defaults, marks the note `ready` and ends `complete`. Author then builds from guesses.
- Migrate folds Bloblang results into `checks.lint`, and Test reports them under `checks.tests`. The graders cannot compare the two.

**Closing rule — AD-8 tightened, with a decision table:**
- End `blocked` if any required input is missing, not ready or stale (H5), or any check is `fail`. Otherwise end `complete`.
- A skill never sets its own artifact to `ready` while it holds unresolved blocking questions. It writes `draft` and ends `blocked`, with reason `open-decisions`.
- `checks` gains `"blobl": "pass"|"fail"|"skipped"`.
- `artifacts` are paths relative to the pipeline config's directory.
- The status block gets `"schema": "rpcn-status@1"`.

## H12 — Eval folder names cannot be split (Low)

**Rules involved:** AD-13 puts cases at `evals/<skill>-<case>/`, and skill names are `rpcn-<job>`.

**Divergence:** the trigger-accuracy aggregator (epic 1) splits on the first `-` and gets skill `rpcn`. A skill epic names a case `rpcn-test-dlq-retry`. The 90% gate is then computed over the wrong groups.

**Closing rule:** `evals/<skill>/<case>/`, and the validator checks that `<skill>` exists.

---

## Other observations (not holes, but worth fixing while editing)

- `<name>.deploy/` is a directory with no frontmatter, so Tune cannot check that it is ready. Add `<name>.deploy/deploy.md` with `artifact: deploy`, and add `deploy` and `test` to the AD-6 `artifact:` enum.
- `<name>.samples.json`: confirm the file name is the one the VS Code extension looks up. R14 parity depends on the name as well as the schema. Also state that no other skill (for example Design writing sample inputs) may write it.
- The paradigm ("skills never … read each other's folders") and AD-1 are fine. All of the holes above are about *shared content* that crosses folders by copying or through the user's project, which only AD-2 governs today.
- AD-2 copies "`tools/rpcn_check/`" but the seed shows one file, `scripts/rpcn_check.py`. State that the copied unit is the single file `tools/rpcn_check/rpcn_check.py` (plus SCHEMA.md), and that tests are never copied. Otherwise `sync_scripts.py` and the drift check (possibly written by different stories) disagree on what to compare.
- Any other script needed by more than one skill (for example a resource-unit parser shared by Scale and Deploy) should follow AD-2. Generalise AD-2 from "check scripts" to "any code used by more than one skill".
