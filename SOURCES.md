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
