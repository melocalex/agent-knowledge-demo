<!--
Use this template for agent-proposed knowledge updates: AGENTS.md, CLAUDE.md,
skills/, docs/agent-memory/. For code changes, delete the knowledge section.
Knowledge updates go in their own PR, separate from code.
-->

## Knowledge update

**Files changed:**
- [ ] `docs/agent-memory/MEMORY.md`
- [ ] `docs/agent-memory/decisions.md` (appended at the end only)
- [ ] `skills/<name>/SKILL.md` or its `references/`, `scripts/`, `evals/`
- [ ] `AGENTS.md` (root or nested)

**What happened:** <!-- The failure, correction or decision that triggered this, in one or two sentences. Paraphrase; no raw logs. -->

**Would the system catch this automatically next time?** <!-- Why this change makes the answer yes. -->

**Source:** <!-- Link to the PR, issue, review comment or session that taught this. -->

## Checklist
- [ ] Searched the target file first; this edits an existing line where one already covers it.
- [ ] Not derivable from the code or git history.
- [ ] No secrets, tokens, customer data, personal data or raw tool output.
- [ ] decisions.md: past entries unchanged; new entry is dated and has Why, Ref and Supersedes.
- [ ] Skill changes: eval cases in `evals/` updated and rerun; results noted below.
- [ ] `make lint` passes locally.
- [ ] Proposed by an agent: yes / no. Reviewed by a human from CODEOWNERS before merge.

## Eval results (skill changes only)
<!-- Case id: pass / fail, model used, date. -->
