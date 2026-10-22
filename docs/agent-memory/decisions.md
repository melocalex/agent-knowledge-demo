# Decisions log

Append-only. Add new entries at the end. Never edit, reorder or delete a past
entry; to reverse one, append a new entry with a `Supersedes:` line.
CI checks the format and, on pull requests, that existing entries are unchanged.

Format, one entry per decision:

    ## YYYY-MM-DD  One-line decision
    Why: reason. Ref: PR, issue or incident link
    Supersedes: none | YYYY-MM-DD title of the entry it replaces

Recorded mistakes belong here too. A failed approach is evidence the next
session can use. In this demo, Ref points at files; in a real repo,
link the PR, issue or incident.

## 2026-10-14  Amounts are integer minor units everywhere
Why: float rounding produced a one-cent mismatch in the example totals test. Ref: services/invoicing/invoicing/totals.py
Supersedes: none

## 2026-10-15  Tax is rounded half-up once per invoice
Why: per-item rounding drifted from the invoice total on many small items. Ref: services/invoicing/tests/test_totals.py
Supersedes: none

## 2026-10-20  Migrations ship with a down file
Why: a reviewer could not tell whether a schema change was reversible. Ref: skills/migration-review/SKILL.md
Supersedes: none

## 2026-10-22  Knowledge files are validated in CI
Why: Markdown instructions are context, not enforcement; CI makes limits hold. Ref: tools/check_agent_knowledge.py
Supersedes: none
