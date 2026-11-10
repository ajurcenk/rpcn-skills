# Sources

Third-party material copied, adapted or distilled into this repository (AD-15).
Add one row per file and source.

- **Pin** is the connect tag plus the benthos version it pins, a skill set's
  AD-13 commit, or a docs URL and the date it was read.
- **Proof** says how the fact is confirmed on 4.100.0 and the newest pin.
- Text is copied or adapted only from Apache-2.0, MIT or BSD files. Redpanda
  Community License files and the docs may inform a fact, in our own words,
  but are never copied.

| File | Source | Pin | Licence | Proof | Notes |
|---|---|---|---|---|---|
| `skills/rpcn-test/references/lint-errors.md` | `redpanda-data/skills` `skills/connect-debugging/references/lint-and-validate.md` | commit `a4562333b774d963066e11dfa1282646b8490550` | Apache-2.0 | Checked by hand against `rpcn_check lint` output on 4.100.0 and 4.115.0. No CI test yet. | Adapted: the "What lint catches" and "What lint does NOT catch" sections, rewritten as a message-pattern table. The file has no closing attribution line yet (AD-15). |
| `tools/shared/formats/blobl-files.md` (copied to `skills/rpcn-author/references/` and `skills/rpcn-test/references/`) | `redpanda-data/benthos` Bloblang import resolution (`from "<path>"` in a mapping is opened relative to the process's working directory, not the config file's folder) | connect `v4.100.0` (benthos `v4.76.0`) and `v4.115.0` (benthos `v4.84.0`) | MIT | `RealBinaryCommandsTest.test_from_resolves_against_the_working_directory` in `tools/shared/rpcn_check/tests/test_rpcn_check.py`: lint and run from the project root load `./pipes/p.double.blobl`, and lint from `pipes/` fails with `failed to read import`, on 4.100.0 and 4.115.0 | A behaviour fact in our own words; no text copied. Decision 2026-11-10: `.blobl` paths are from the project root |
| `tools/shared/formats/samples-format.md` (copied to `skills/rpcn-test/references/`), `tools/shared/rpcn_check/SCHEMA.md` (`blobl --samples`) | `redpanda-data/benthos` `blobl` CLI output: a string root prints raw, without quotes (`root = "123"` prints `123`; `format_json()` prints JSON text), and a deleted message prints an empty line | connect `v4.100.0` (benthos `v4.76.0`) and `v4.115.0` (benthos `v4.84.0`) | MIT | `RealBinaryCommandsTest.test_blobl_samples` in `tools/shared/rpcn_check/tests/test_rpcn_check.py`: a `facts.blobl` prints `123`, an empty line and `{"a":1}`, and its string, `deleted` and JSON-text samples pass, on 4.100.0 and 4.115.0 | A behaviour fact in our own words; no text copied. `compare_sample` relies on it |
