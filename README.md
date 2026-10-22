# agent-knowledge-demo

A small, copyable example of keeping coding-agent knowledge in the repository
instead of on one engineer's laptop. It implements the layout and practices
from the article "Agent knowledge that outlives its author: AGENTS.md, skills
and a memory log in the repo" by Alexandre Melo.

Everything an agent needs to do its job lives in plain Markdown, owned by a
team through CODEOWNERS, changed through pull requests, and checked by CI:

- **Instructions:** `AGENTS.md` at the root, plus one per package. The closest
  AGENTS.md to the edited file wins; explicit user prompts override everything.
  `CLAUDE.md` only imports `@AGENTS.md`, so there is one source of truth.
- **Procedures:** `skills/<task>/SKILL.md` folders in the Agent Skills format,
  loaded by progressive disclosure, each with eval cases.
- **Memory:** a short curated `MEMORY.md` loaded every session, and an
  append-only, dated `decisions.md` read on demand.

The example code is a tiny invoicing library under `services/invoicing/`. It
exists only so the nested AGENTS.md and the skills have something real to point
at. Nothing here depends on a particular agent vendor.

## Tree

```text
.
├── AGENTS.md                         # root instructions, loaded every session
├── CLAUDE.md                         # first line: @AGENTS.md
├── LICENSE
├── Makefile                          # make deps | test | test-invoicing | lint
├── README.md
├── .claude/
│   └── settings.json                 # read-only default mode, permissions deny-list
├── .github/
│   ├── CODEOWNERS                    # knowledge files routed to @your-org/platform
│   ├── pull_request_template.md      # template for agent-proposed knowledge updates
│   └── workflows/
│       └── agent-knowledge.yml       # CI: checker + unit tests
├── docs/
│   ├── HANDOVER.md                   # handover checklist
│   ├── SECURITY.md                   # security defaults and why
│   └── agent-memory/
│       ├── MEMORY.md                 # curated facts, under 200 lines
│       └── decisions.md              # append-only, dated
├── services/
│   └── invoicing/
│       ├── AGENTS.md                 # nearest file wins for this subtree
│       ├── invoicing/
│       │   ├── __init__.py
│       │   └── totals.py
│       ├── migrations/
│       │   ├── 0001_create_invoices.down.sql
│       │   └── 0001_create_invoices.sql
│       └── tests/
│           └── test_totals.py
├── skills/
│   ├── knowledge-update/
│   │   ├── SKILL.md
│   │   ├── evals/cases.md
│   │   └── references/entry-formats.md
│   ├── migration-review/
│   │   ├── SKILL.md
│   │   ├── evals/cases.md
│   │   └── references/rollback.md
│   └── release-notes/
│       ├── SKILL.md
│       ├── evals/cases.md
│       └── scripts/collect_prs.sh
├── tests/
│   └── test_checker.py               # tests for the checker
└── tools/
    └── check_agent_knowledge.py      # standard-library checker run by CI
```

## How the pieces load

| File | When the agent reads it | Budget |
| --- | --- | --- |
| `AGENTS.md` (root and nested) | Every session; nested file for its subtree | Under 200 lines each |
| `docs/agent-memory/MEMORY.md` | Start of every task | 200 lines, 25 KB |
| Skill `name` and `description` | Session start, about 100 tokens per skill | name 64 chars, description 1024 |
| `SKILL.md` body | When the task matches the description | Under 500 lines, about 5,000 tokens |
| `scripts/`, `references/` in a skill | Only when a step needs them | None |
| `docs/agent-memory/decisions.md` | On demand, when a task touches a past decision | None, append-only |

## The self-maintaining loop

1. The agent reads AGENTS.md, MEMORY.md and the matching skill at session start.
2. It does the work and opens a PR. Humans merge.
3. When it hits a new failure or a correction, it asks: "Would the system catch
   this automatically next time?" If not, it uses the `knowledge-update` skill
   to propose a diff to MEMORY.md, decisions.md or a SKILL.md, in a separate PR
   that uses `.github/pull_request_template.md`.
4. CODEOWNERS routes that PR to a team, never a single person.
5. CI checks the knowledge files like code (see below).
6. When a skill or the model changes, rerun that skill's `evals/` cases and
   record the result in the PR. Treat a model upgrade as a reason to rerun all of them.
7. Each quarter, prune MEMORY.md: remove what nobody needs, merge overlaps.

## What CI checks

`.github/workflows/agent-knowledge.yml` runs on pushes to main and on every PR.
It needs nothing beyond `python3`, `git` and `make` on the runner.

`tools/check_agent_knowledge.py` checks:

- **Skills:** frontmatter exists; only spec fields (`name`, `description`,
  `license`, `compatibility`, `metadata`, `allowed-tools`); `name` is 1 to 64
  chars of lowercase letters, digits and single hyphens and matches the folder;
  `description` is 1 to 1024 chars; body under 500 lines and about 5,000 tokens;
  every `scripts/`, `references/`, `assets/` or `evals/` path the body
  mentions exists.
- **Skill evals:** each skill has `evals/*.md` with at least two `## Case:`
  entries, at least one positive (should activate) and one negative (should
  not), each with `Type`, `Prompt` and at least one `Expect` bullet.
- **Size budgets:** every AGENTS.md and CLAUDE.md at most 200 lines; CLAUDE.md
  starts with `@AGENTS.md`; MEMORY.md at most 200 lines and 25 KB, with no
  duplicate lines.
- **Decisions log:** every entry is `## YYYY-MM-DD  Title` with `Why:`, `Ref:`
  and `Supersedes:` lines; dates are valid, not in the future, and in order.
  With `--base <ref>` (CI passes the PR base, or the previous main commit on
  push), every existing entry must be unchanged and in the same position.
- **Secret scan:** knowledge files (AGENTS.md, CLAUDE.md, README.md,
  CODEOWNERS, `skills/`, `docs/`, `.claude/`, `.github/`) are scanned for
  common token formats, private key blocks, credentials in URLs, hard-coded
  credentials and email addresses. It is a tripwire, not a full scanner.
- **CODEOWNERS:** every owner is a team (`@org/team`), and the knowledge paths
  have rules.

Run the same checks locally:

```bash
make test lint
python3 tools/check_agent_knowledge.py --base origin/main   # include the append-only check
```

## Security defaults

See `docs/SECURITY.md`. In short: sessions start read-only (`plan` mode in
`.claude/settings.json`); a `permissions.deny` list blocks reading secrets,
editing CI and settings, force pushes and raw network tools; tool output,
including fetched pages and issue or PR text, is untrusted input; pushes,
merges, deploys, migrations, publishing and third-party skill installs need a
human. AGENTS.md explains these rules, but the settings file and CI enforce them.

## How to adopt

1. Copy `AGENTS.md`, `CLAUDE.md`, `docs/agent-memory/`, `.github/CODEOWNERS`,
   `.github/pull_request_template.md`, `.github/workflows/agent-knowledge.yml`,
   `tools/check_agent_knowledge.py` and `docs/HANDOVER.md` into your repo.
2. Replace `@your-org/platform` in CODEOWNERS and the skills with your team handle.
3. Rewrite AGENTS.md for your commands and boundaries. Add a nested AGENTS.md
   only where a package has rules of its own.
4. Clear the example entries from MEMORY.md and decisions.md and start your own.
5. Write one skill for a task your team already runs with an agent. Start from
   its eval cases: run the agent on representative prompts, note where it
   struggles, then write the steps.
6. Adapt `.claude/settings.json` (or your harness's equivalent) to your paths.
7. Turn on branch protection for main and require the `agent-knowledge` check.
8. When someone leaves, work through `docs/HANDOVER.md`.

The checker reads a subset of YAML that covers normal SKILL.md frontmatter.
For full validation against the spec you can also run the reference validator
(`skills-ref validate skills/<name>`) from the Agent Skills project.

## Sources

From the article:

- agents.md, AGENTS.md open format: https://agents.md/
- Agent Skills specification: https://agentskills.io/specification
- Anthropic Engineering, "Equipping agents for the real world with Agent Skills": https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- Anthropic Engineering, "Effective context engineering for AI agents": https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
- Claude Code docs, "How Claude remembers your project": https://code.claude.com/docs/en/memory
- Claude API docs, memory tool: https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool
- Yichao "Peak" Ji, "Context Engineering for AI Agents: Lessons from Building Manus": https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus
- Cline docs, Memory Bank: https://docs.cline.bot/best-practices/memory-bank
- Every, Compound Engineering guide: https://every.to/guides/compound-engineering
- Simon Willison, "Claude Skills are awesome, maybe a bigger deal than MCP": https://simonwillison.net/2025/Oct/16/claude-skills/
- GitHub Spec Kit: https://github.com/github/spec-kit

Also used for the settings example:

- Claude Code docs, settings and permissions: https://code.claude.com/docs/en/settings

## License

Apache-2.0. See `LICENSE`.
