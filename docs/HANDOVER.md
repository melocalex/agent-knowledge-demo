# Handover checklist

Run this when someone who configured or heavily used the team's coding agents
leaves or changes teams. The goal: nothing the agents rely on lives only on
that person's machine. Each item is done through a normal pull request.

- [ ] Everything in the leaver's `~/.claude/`, `~/.codex/` or personal rules that matters is promoted into the repo via PR.
- [ ] Their machine-local auto memory has been reviewed and the useful lines moved into `docs/agent-memory/MEMORY.md` or `docs/agent-memory/decisions.md`.
- [ ] Every recurring task they ran with an agent has a `skills/<task>/SKILL.md` that someone else has executed end to end.
- [ ] Their review judgment is captured as a skill, with an eval set, if they were a frequent reviewer.
- [ ] `.github/CODEOWNERS` lists teams only. No path is owned by the person leaving.
- [ ] Their tokens and personal API keys are revoked, and nothing in the files references them.
- [ ] CI passes on all agent files after the changes above.

## Where to look on the leaver's machine

Paths vary by tool and version. Common places:

- Claude Code: `~/.claude/CLAUDE.md`, `~/.claude/settings.json`,
  `~/.claude/projects/<project>/memory/` (auto memory, machine-local by design),
  `.claude/settings.local.json` in each project.
- Codex: `~/.codex/` (config and personal instructions).
- Any personal rules files, prompt snippets or notes they kept outside the repo.

Do not copy files wholesale. Read them, keep what is still true and useful,
and rewrite it to the rules at the top of MEMORY.md. Strip anything personal
or secret before it reaches a PR.

## Capturing review judgment as a skill

If the person reviewed many PRs, collect a sample of their review comments,
split it into a training set and a held-out set, write a review skill from
the training set, and keep the held-out comments as eval cases in the
skill's `evals/` folder. Rerun those cases when the skill or the model changes.
