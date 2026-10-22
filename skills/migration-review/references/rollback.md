# Rollback checklist (loaded only when step 3 of SKILL.md applies)

Use this when a migration is destructive or its down file is not a pure
inverse of the up file.

1. Data loss: list every column or table the down file drops. For each, state
   what data written after the up migration would be lost.
2. Two-step changes: renames and type changes should ship as
   expand (add new, dual-write) then contract (remove old) in separate PRs.
   If the PR does both at once, mark it blocking.
3. Defaults and NOT NULL: adding NOT NULL to an existing column needs a
   backfill step first. Check that the backfill exists and is idempotent.
4. Locking: note any statement that rewrites a whole table or takes a long
   exclusive lock. Ask for the expected row count if it is not in the PR.
5. Order: the down files must be runnable in reverse order of the up files.
6. Verification: the PR should say how a human checks the rollback worked
   (for example a row count or a schema diff). If it does not, ask for it.

Report each item as pass, fail or not applicable, with one line of reason.
