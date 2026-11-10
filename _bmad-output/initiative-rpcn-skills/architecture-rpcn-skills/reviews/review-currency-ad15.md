---
review: currency
target: architecture-rpcn-skills.md, AD-15 "Content sources" (recorded 2026-11-10)
lens: every decision web-researched or reality-checked, not asserted from training data
reviewed: 2026-11-10
verdict: sources exist and fit, with rework needed — the behaviour source is the wrong repo for most named facts, the pin is stale, and the licence/provenance rule does not fit two sources
---

# Currency review: AD-15, Content sources

## Verdict

All four named sources exist today and are live: `redpanda-data/connect` and its tags, `redpanda-data/skills`, the
Claude plugin under `.claude-plugin/` in connect, and the official docs and cookbooks. But AD-15 reads as a decision
the user made on 2026-11-10 (memlog lines 57-59). Nothing in the memlog shows that the sources were checked against
reality when it was recorded. The check turns up three problems that matter before stories 2.7-2.11 begin:

1. Most of the "behaviour" facts the rule sends to `redpanda-data/connect` are not in that repo. They are in
   `redpanda-data/benthos`, which connect pins through `go.mod`.
2. The "newest pin" is already two minor releases behind.
3. The provenance rule ("the licence" per row) does not cleanly fit the connect repo, which has two licences, or the docs
   source repo, which is private and has no licence file.

## Method

- **`gh api` / `gh release`:** `redpanda-data/connect` (releases, `.claude-plugin/` tree and history, `go.mod` at
  v4.100.0, v4.115.0 and v4.117.0, `docs/` at several tags), `redpanda-data/skills` (metadata, history, file
  history), `redpanda-data/benthos` (metadata), and `redpanda-data/rp-connect-docs` (visibility, tree).
- **Web:** fetched `https://docs.redpanda.com/connect/` and `https://docs.redpanda.com/connect/cookbooks/`, and
  checked the redirect from `curl -I https://docs.redpanda.com/redpanda-connect/home/`.
- **Local clones:** `/home/aleksejjurcenko/projects/redpanda-replicator/v4.112.0/connect` (git describe,
  `.claude-plugin/`, `go.mod`, `licenses/`), the benthos module cache at `~/go/pkg/mod/github.com/redpanda-data/benthos`,
  `/home/aleksejjurcenko/projects/skills` (HEAD, compared with origin), and
  `/home/aleksejjurcenko/projects/clients/personal/rpcn-skills/SOURCES.md` and `tools/rpcn_versions.txt`.

## Spot-check ledger

| # | Claim in AD-15 (or implied by it) | Status | Evidence |
|---|---|---|---|
| 1 | `redpanda-data/connect` exists and publishes release tags | **Confirmed** | Public, not archived, pushed 2026-11-10. Latest release is v4.117.0 (2026-11-06). Before it: v4.116.1 (10-30), v4.116.0 (10-30), v4.115.1 (10-23), v4.115.0 (10-22) |
| 2 | Retry and backoff, ack and delivery, batching, `fallback`, `max_in_flight` ordering and lint message strings all come from the connect source at a pinned tag | **Mostly contradicted** | The `fallback`, `retry` output and processor, broker and fan-out code is in `redpanda-data/benthos` `internal/impl/pure/` (`output_fallback.go`, `output_retry.go`, `processor_retry.go`, `output_broker*.go`). Lint strings such as `field not recognised` and `type '%v' was not recognised` are in benthos `internal/docs/`. Connect holds only per-connector behaviour (for example `internal/impl/kafka/franz_writer.go`). The `redpanda-data/skills` source map says the same: "`rpk connect lint`/`run`/`test`/`list` ... is a managed-plugin passthrough to the upstream Benthos framework" |
| 3 | A connect tag fixes the behaviour code | **Confirmed, indirectly** | Connect pins benthos in `go.mod`: v4.100.0 uses benthos v4.76.0, v4.112.0 (local) uses v4.81.0, and v4.115.0 and v4.117.0 use v4.84.0. So the pin works only if provenance records the benthos version too |
| 4 | Canonical config and test examples are in the connect source | **Confirmed** | `config/test/` exists at v4.117.0, including `cookbooks/filtering.yaml` and `filtering_benthos_test.yaml` |
| 5 | The newest pin (AD-5 and the Stack table) is 4.115.0 "(rolling)" | **Stale** | `tools/rpcn_versions.txt` = `4.100.0`, `4.115.0`. v4.116.0 came out 11 days ago and v4.117.0 4 days ago. AD-14 promises a roll PR "within one week", and that window has already passed for 4.116.0 |
| 6 | The Redpanda Connect Claude plugin is in the connect repo | **Confirmed** | `.claude-plugin/marketplace.json` (`redpanda-connect-plugins`) → `.claude-plugin/plugins/redpanda-connect/`, plugin.json `version: 0.2.0`, `license: Apache-2.0`. It has the skills `bloblang-authoring`, `component-search` and `pipeline-assistant` (with `resources/recipes/*.md`), the commands `blobl`, `pipeline` and `search`, and `dist/*.zip` 0.2.0. All of this is present at tag v4.117.0 |
| 7 | The plugin is a living baseline | **Confirmed, slow-moving** | Added 2025-12-18. Since then the commits are only a docs-URL fix (2026-01-06), antora partials (2026-10-08) and a docs-URL change to `docs.redpanda.com/connect` (2026-10-13). Version 0.2.0 has not changed |
| 8 | `redpanda-data/skills` exists and fits as an AD-13 arm and as a phrasing source | **Confirmed** | Public, Apache-2.0, very active (last push 2026-11-09). It has `connect` and `connect-debugging`, plus 9 `connect-cdc-*` skills that the spine does not mention |
| 9 | The local skills clone matches upstream | **Behind** | Local HEAD `a4562333` (2026-10-20) is 18 commits behind `origin/main`, including "Connect skill updates for v4.115.0", "v4.115.1" and "drift audit (2026-11)". The `lint-and-validate.md` file cited in `SOURCES.md` has not changed since `56db59e1` (10-16), so that one row is still accurate |
| 10 | The official docs and cookbooks are a source | **Confirmed** | `docs.redpanda.com/connect/` is live and shows latest = 4.117.0. The `/connect/cookbooks/` index lists 21 cookbooks. The old `/redpanda-connect/...` URLs return a 301 to `/connect/...` |
| 11 | The docs sit at "a pinned version" | **Does not fit** | The docs site serves `page-version: master` and is unversioned. Docs best practice cannot be pinned the way a tag can, so only the fetch date can be recorded |
| 12 | Docs source for provenance rows | **Moved, and private** | Connect's in-repo `docs/modules/{components,configuration,guides}` exist at v4.100.0 but are gone by v4.115.0 (only `docs/benchmarking.md` is left). The docs source is `redpanda-data/rp-connect-docs`, which is **private** and has no LICENSE file. Deploy and Tune pages exist there (`guides/performance_tuning.adoc`, `monitoring.adoc`, `delivery_semantics.adoc`, `configuration/batching.adoc`, `error_handling.adoc`, `install/kubernetes-operator.adoc`). The `redpanda-data/skills` source map still cites the old `docs/modules/components/pages/` paths in connect |
| 13 | `SOURCES.md` row gives "the licence" | **Partly fits** | connect: GitHub reports `license: null`. `licenses/README.md` says Apache-2.0 covers most of the code and RCL covers enterprise features. benthos: MIT. The plugin and `redpanda-data/skills`: Apache-2.0. Docs: no licence published. The licence is not checked against the source |
| 14 | Failure modes from resolved GitHub issues and support cases | **Unverified** | No check was made of how reachable or licensed the support cases are. `redpanda-data/skills` already ships `connect-debugging/references/failure-modes.md`, so there is an overlapping source that AD-15 does not name |
| 15 | Redpanda Docs MCP is an authoring source | **Dropped from the spine** | The memlog (line 58) names it, but the AD-15 table does not. It exists (`ask_redpanda_question`, `get_connect_component`) |

## Findings

### F1 (HIGH): the behaviour row names the wrong repo for most of its facts

Retry and backoff, `fallback`, broker ordering, batching policy, `max_in_flight` handling in the output pipeline, and
the lint message strings are all implemented in `redpanda-data/benthos` (MIT), not in `redpanda-data/connect`.
Connect contributes only connector-specific behaviour (for example how a Kafka writer acks). If stories 2.7-2.11 follow
the rule as written, they will search connect for code that is not there, or cite the wrong file in `SOURCES.md`.
**Fix:** make the row "`redpanda-data/connect` at a pinned tag, plus `redpanda-data/benthos` at the version that
tag's `go.mod` pins". Record both in provenance, for example `connect v4.115.0 → benthos v4.84.0`. Note that
4.100.0 pins benthos v4.76.0, so the 4.100.0-to-newest proof spans eight benthos minors.

### F2 (MEDIUM): the newest pin is stale, and the one-week roll promise is already broken

The pins are `4.100.0` and `4.115.0`, but v4.116.0 (2026-10-30) and v4.117.0 (2026-11-06) are out. The weekly job
in AD-14 does not exist yet, so the Stack's "(rolling)" is aspirational. Facts "confirmed on the newest pin" are
today confirmed on a pin that is two releases old. **Fix:** roll to 4.117.0 before stories 2.7 and later write
references, or state that the pin rolls by hand until epic 4.

### F3 (MEDIUM): docs facts cannot meet the "pinned version" and "licence" parts of the rule

The docs site is unversioned (`master`). The docs source moved out of the connect repo after 4.100.0 into the
private, unlicensed `redpanda-data/rp-connect-docs`. As written, a Design, Deploy or Tune fact can't carry a tag, and
it can't carry a licence. **Fix:** for docs rows, record the URL and fetch date, and treat docs as "distilled in our
words, not copied", since no licence is published. Add the Docs MCP back in, or drop it on purpose. Confirm with
Redpanda whether quoting the docs is allowed.

### F4 (LOW): the licence column needs per-file care for connect

The connect repo is dual-licensed: Apache-2.0, plus RCL for enterprise code, and GitHub's SPDX is null. A fact
adapted from an enterprise connector's file falls under RCL. **Fix:** `SOURCES.md` rows that cite connect should
name the licence of the specific path.

### F5 (LOW): the local reality-check clones are not at pinned points

The connect clone is at `v4.112.0-26-gf15e3064a`, which is neither a release tag nor a current pin. The skills clone is
18 commits behind and misses three Connect updates. Neither one is a valid local stand-in for "source at a pinned tag"
or for "the AD-13 baseline" until it is checked out or pulled. Also, the `redpanda-data/skills` `connect-cdc-*`
skills and `failure-modes.md` overlap the failure-mode and Design sources, and AD-15 doesn't say whether they count.

## What is confirmed and fine

- The runtime rule (only the binary, through `rpcn_check`) fits the facts: the docs are unversioned and the source
  spans two repos, so the binary is the only version-exact authority.
- The plugin location, its contents and its Apache-2.0 licence. It is present at v4.117.0.
- `redpanda-data/skills` is Apache-2.0, matching the existing `SOURCES.md` row and commit.
- The cookbooks exist (21), and the Deploy and Tune guides exist in the docs.
- Release sync by diffing component specs is feasible, because the specs come from the binary
  (`rpk connect list --format json-full`, per the earlier currency review), not from the moved docs folder.
