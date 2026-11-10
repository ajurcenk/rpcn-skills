- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-validation-foundation/tickets/story-tracer-rpcn-test-installs-both-ways-and-reports-the-binary-plan.md`
  summary: Check whether `rpk connect --version` auto-downloads Redpanda Connect when the plugin is missing, which would make rpcn_check's read-only probe time out or install a plugin as a side effect.
  evidence: Unverified (maybe-false, medium if true). The unit tests use a fake rpk that always fails. Settle it by running `rpk connect --version` on a machine where `rpk connect uninstall` has been run; if it downloads, skip the rpk probe when the plugin is absent (for example by checking rpk's plugin directory first).
  resolved: 2026-11-03, story 1.12. With no Connect plugin, rpk v26.2.2 prints its help text and exits 0, with no download. rpcn_check exits 2 with the install hint, which a unit test pins.
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-validation-foundation/tickets/story-tracer-rpcn-test-installs-both-ways-and-reports-the-binary-plan.md`
  summary: Verify the Claude Code marketplace install (`claude plugin marketplace add ajurcenk/rpcn-skills`, then `claude plugin install rpcn-skills@rpcn-skills`) offers rpcn-test and that it triggers on "check my Redpanda Connect binary".
  evidence: Skipped by the user on 2026-10-23. Already shown: `claude plugin validate` passes, a `--plugin-dir` run triggered the skill, and `npx skills add ajurcenk/rpcn-skills --list` from GitHub lists only rpcn-test. Must pass before epic 1 closes, because epic 1's R1 covers both channels.
  resolved: 2026-11-03 — closed as out of scope, not run. The user dropped the marketplace channel; R13 and epic 1's R1 now require only `npx skills`.
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-validation-foundation/tickets/story-trigger-evals-and-the-accuracy-gate-for-rpcn-test-plan.md`
  summary: AD-11's deprecated-component scan (epic 4) must not flag the plain phrase "Kafka Connect" in the trigger negative `evals/rpcn-test__miss_kafka_connect/prompt.md`, or that case must be exempt.
  evidence: AD-11 names `kafka` as a deprecated example and scans eval prompts. The negative case is required by story 1.7's frozen intent.
- source_plan: `_bmad-output/backlog/bug-rpcn-test-report-never-ready-for-a-pipeline-in-a-subfolder-plan.md`
  summary: Make the subfolder scenarios fail on the old rpcn-test, by checking that no Bash call uses `cd` and that the report's `inputs[].file` has no directory part.
  evidence: The scenario passed against the old skill (`rpcn-test-skills/runs/20261103-151201`) because the agent ran `cd pipes`. The defect depends on whether the agent cds, and the runner has no check type for either condition. That needs a runner change plus tests in rpcn-test-skills.

- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-tracer-rpcn-author-writes-a-pipeline-that-lints-clean-plan.md`
  summary: No scenario covers rpcn-author's "unknown component" matrix row (`fields` exits 1 with close matches, so the agent picks a reported one or records an open question).
  evidence: The story 2.4 matrix audit found the row untested. A made-up component is hard to assert reliably (which match it picks, or the open_questions content), so the user chose to defer it (2026-11-06).
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-tracer-rpcn-author-writes-a-pipeline-that-lints-clean-plan.md`
  summary: No scenario covers rpcn-author's "lint won't clean after 3 revisions" matrix row (headless ends blocked, with the first error as the reason).
  evidence: The story 2.4 matrix audit found the row untested. A lint failure the agent can't fix is hard to force deterministically. Story 2.11 (diagnosis) is the natural home for it. The user chose to defer it (2026-11-06).
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-tracer-rpcn-author-writes-a-pipeline-that-lints-clean-plan.md`
  summary: The AD-11 deprecated-scan exemption for "Kafka Connect" must also cover `evals/rpcn-author__miss_kafka_connect/prompt.md`, not only the rpcn-test negative.
  evidence: The existing deferred AD-11 entry names only `evals/rpcn-test__miss_kafka_connect/prompt.md`. Story 2.4 added a second prompt with the same phrase ("Write a Kafka Connect connector config …").
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-author-applies-a-test-report-s-proposed-changes-plan.md`
  summary: No scenario covers rpcn-author's "verdict pass, Proposed changes None." matrix row (nothing to apply, files unchanged, complete).
  evidence: The story 2.5 matrix audit found the row untested. The user chose to cover only the draft report and the Test-owned diff, to keep the eval cost down (2026-11-09).
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-author-applies-a-test-report-s-proposed-changes-plan.md`
  summary: No scenario covers rpcn-author's "hunk doesn't match" matrix row (the item isn't applied and goes in open_questions, the others are applied, complete).
  evidence: The story 2.5 matrix audit found the row untested. The runner has no "file does not contain" check or open_questions content check to assert it, so the user chose to defer it (2026-11-09).
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-author-applies-a-test-report-s-proposed-changes-plan.md`
  summary: No scenario covers rpcn-author's "lint still fails after applying a report" matrix row (Step 6's 3 revisions, then blocked).
  evidence: The story 2.5 matrix audit found the row untested. It is the same Step 6 path as story 2.4's deferred "lint won't clean" row, and is as hard to force. The user chose to defer it (2026-11-09).
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-author-builds-from-a-design-note-and-records-deviations-plan.md`
  summary: Scenario for a ready design note that names a component the binary doesn't list (Author must stop `blocked`, unlisted component).
  evidence: Story 2.6 matrix audit (2026-11-09). The user chose to defer it, because a deterministic fixture needs a component that is absent on every tested binary, and the block rule predates this story.
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-author-builds-from-a-design-note-and-records-deviations-plan.md`
  summary: The 2.6 scenarios don't check the design-note rows' status and reply parts: the edited note in `artifacts` (deviation), the not-ready line in `open_questions` and the reply (not_ready, draft), or that the deviation pipeline really dropped `orders.dlq`.
  evidence: Story 2.6 quick review (2026-11-09). The runner's `[status]` check uses exact equality, and it has no "does not contain" or `open_questions` content check. That limitation predates this story (see the 2.5 hunk-mismatch deferral). It needs a new runner capability.
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-bloblang-mappings-come-with-samples-and-test-runs-them-plan.md`
  summary: No scenario asserts that rpcn-author keeps a mapping of 3 lines or fewer inline (no `.blobl` written).
  evidence: Story 2.7 matrix audit (2026-11-10). The runner has no "file does not exist" check. The existing write scenarios pass but don't assert it. The user chose to defer it.
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-bloblang-mappings-come-with-samples-and-test-runs-them-plan.md`
  summary: No scenario covers rpcn-test with a `.blobl` that doesn't parse (one `fail` row with the parse error, verdict `fail`, not `blocked`).
  evidence: Story 2.7 matrix audit (2026-11-10). Only `rpcn_check` unit tests cover the exit-1 parse error. The user chose to defer the skill-level scenario to keep the eval cost down.
- source_plan: `_bmad-output/initiative-rpcn-skills/tickets/epic-author-and-test/tickets/story-bloblang-mappings-come-with-samples-and-test-runs-them-plan.md`
  summary: `rpcn-test__samples_written` proves the written samples file is valid only through the skill's own status block and substring checks. Add a runner check that validates a samples file left behind, for example by running `rpcn_check blobl --samples`.
  evidence: Story 2.7 quick review (2026-11-10). The runner has no samples-file check. That limitation predates this story, like the 2.6 status/reply assertion deferral. Adding one needs a new `expect.toml` key.
