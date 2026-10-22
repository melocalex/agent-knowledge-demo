---
name: migration-review
description: Reviews database schema migrations for safety and reversibility before merge. Use when a PR adds or changes files under a migrations/ directory, or when asked to review a schema change. Not for application-level data fixes.
metadata:
  owner: "@your-org/platform"
  version: "2"
---

# Migration review

1. List the migration files in the change. Each `NNNN_name.sql` must have a
   matching `NNNN_name.down.sql`. Missing rollback is a blocking finding.
2. For each statement, classify it as additive (new table, nullable column,
   new index) or destructive (drop, rename, type change, NOT NULL on an
   existing column). Destructive changes are blocking unless the PR links a
   two-step plan.
3. If any statement is destructive or the rollback is not a pure inverse,
   read `references/rollback.md` and apply its checklist.
4. Check that money columns are integer minor units (`BIGINT ..._minor`).
5. Write findings as a PR review comment draft for a human to post. Never run
   a migration against a shared database. Never approve the PR yourself.

## Known mistakes
- `DROP COLUMN` in a down migration loses data written after the up ran.
  Say so explicitly; do not call that rollback "safe".
- Adding an index on a large table without a concurrent option locks writes.
