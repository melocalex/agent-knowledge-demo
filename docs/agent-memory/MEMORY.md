# MEMORY.md

Curated facts and preferences for agents in this repo. One line each.
Loaded at the start of every session, so it must stay under 200 lines and 25 KB
(Claude Code loads only the first 200 lines or 25 KB of its memory index).
The long history lives in decisions.md and is read on demand.

## Writing rules (enforced in review and partly in CI)
- Search before appending. Update an existing line instead of adding a near-duplicate.
- Do not store what can be derived from the code or git history.
- No secrets, tokens, customer data, personal data or raw tool output.
- Change this file only through a PR. Never edit it on main.
- Prune on a schedule: each quarter, remove lines nobody needs and merge overlaps.
  Last pruned: 2026-10-22.

## Facts
- Amounts are integers in minor units everywhere. Never use float for money.
- Invoice tax rate is passed in basis points (2000 = 20%).
- Tax is rounded half-up once per invoice, not per line item.
- Every SQL migration needs a matching .down.sql file.
- Release notes are drafts in docs/releases/; a human publishes them.

## Preferences
- Prefer the standard library. Ask before adding any dependency.
- Keep PRs small. Knowledge updates go in their own PR, not mixed with code.
