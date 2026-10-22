---
name: knowledge-update
description: Proposes updates to agent knowledge files (MEMORY.md, decisions.md, a SKILL.md) after a task surfaced a new failure, correction or decision. Use at the end of a task when the answer to "would the system catch this automatically next time?" is no, or when asked to record a lesson.
metadata:
  owner: "@your-org/platform"
  version: "1"
---

# Knowledge update

1. Decide where the lesson belongs:
   - A current fact or preference: `docs/agent-memory/MEMORY.md`.
   - A decision with a reason, or a recorded mistake: `docs/agent-memory/decisions.md`.
   - A step or pitfall in a repeatable task: that skill's SKILL.md ("Known mistakes").
2. Search the target file first. If a line already covers the lesson, edit that
   line instead of adding a near-duplicate.
3. Skip it if the agent could derive it from the code or git history.
4. Strip secrets, tokens, customer data, personal data and raw tool output.
   Paraphrase; do not paste logs.
5. Write the entry using `references/entry-formats.md`. Decisions are appended
   at the end of decisions.md; never edit or reorder past entries. To reverse a
   decision, append a new one with a `Supersedes:` line.
6. Run `make lint`. Open a separate PR with the knowledge-update template.
   Do not mix knowledge changes with code changes. Never push to main.

## Known mistakes
- Putting a one-off debugging detail in MEMORY.md. If it will not matter next
  month, it belongs in the PR description, not in memory.
