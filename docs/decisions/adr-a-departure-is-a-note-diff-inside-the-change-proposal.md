# A departure from a ready note is a note diff inside the change proposal

When rpcn-author's headless change mode makes a change that departs from a ready design note, the Deviations row is not written to the note at proposal time. It becomes one more item in the `change@1` proposal: a diff against `<name>.design.md` that only appends the row and, when it isn't already today, sets `updated`. The note is then listed in the proposal's `inputs`, and the apply step accepts the note as a target for exactly that diff shape, from a proposal only. Interactive change mode records the same row with Edits, after the departing item has landed whole. This was story 8.4, commit `38d3486`, plan `_bmad-output/initiative-rpcn-skills/tickets/epic-existing-pipelines/tickets/story-apply-a-design-change-to-an-existing-pipeline-plan.md`.

The user chose this on 2026-11-27 so that the row lands only when the change lands, and is reviewed with it. Two alternatives were declined:
- Editing the note while writing the proposal, as building from a note does, would have needed no format change. But the row would claim a departure that hadn't happened, and it would break "headless writes only the proposal".
- Keeping an Open decisions line and having the apply step write the row would have made the apply step invent note text from prose.

The cost is an additive `change@1` wording change, with no major bump, and a new, narrowly guarded apply target.
