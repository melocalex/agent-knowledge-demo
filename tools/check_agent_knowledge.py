#!/usr/bin/env python3
"""Validate agent knowledge files. Standard library only.

Checks:
  skills     SKILL.md frontmatter and limits (agentskills.io spec), referenced files exist
  evals      each skill has evals/*.md with well-formed cases
  budgets    AGENTS.md / CLAUDE.md line budget, MEMORY.md line and byte budget
  decisions  decisions.md entry format, dates, and append-only against a base ref
  secrets    secret-like strings and email addresses in knowledge files
  owners     CODEOWNERS entries are teams, not individuals

Usage:
  python3 tools/check_agent_knowledge.py [--root DIR] [--base GIT_REF]

--base compares docs/agent-memory/decisions.md against that git ref and fails
if any existing entry was edited, removed or reordered. Exit code 1 on errors.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

INSTRUCTION_MAX_LINES = 200
MEMORY_MAX_LINES = 200
MEMORY_MAX_BYTES = 25 * 1024
SKILL_NAME_MAX = 64
SKILL_DESCRIPTION_MAX = 1024
SKILL_COMPATIBILITY_MAX = 500
SKILL_BODY_MAX_LINES = 500
SKILL_BODY_MAX_TOKENS = 5000  # estimated as characters / 4
SKILL_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_REF_RE = re.compile(r"(?<![\w/.-])((?:scripts|references|assets|evals)/[\w./-]*[\w])")
EVAL_MIN_CASES = 2

MEMORY_PATH = "docs/agent-memory/MEMORY.md"
DECISIONS_PATH = "docs/agent-memory/decisions.md"
DECISION_HEADING_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})  (\S.*)$")

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
KNOWLEDGE_DIRS = ("skills", "docs", ".claude", ".github")
KNOWLEDGE_NAMES = {"AGENTS.md", "CLAUDE.md", "README.md", "CODEOWNERS"}

SECRET_PATTERNS = [
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("Slack token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("OpenAI/Anthropic-style key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}\b")),
    ("Private key block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("JSON web token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("Credential in URL", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s:@]+@")),
    (
        "Hard-coded credential",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|passw(?:or)?d)\b[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9/+_.=-]{16,}"
        ),
    ),
]
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
EMAIL_ALLOWED_DOMAINS = ("example.com", "example.org", "example.net", "users.noreply.github.com")


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.checked: dict[str, int] = {}

    def error(self, path: str, message: str, line: int | None = None) -> None:
        where = f"{path}:{line}" if line else path
        self.errors.append(f"{where}: {message}")

    def count(self, check: str) -> None:
        self.checked[check] = self.checked.get(check, 0) + 1


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def rel(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def walk(root: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            yield os.path.join(dirpath, name)


# ---------------------------------------------------------------- frontmatter

def split_frontmatter(text: str) -> tuple[str | None, str, int]:
    """Return (frontmatter, body, body_start_line). frontmatter is None if absent."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text, 1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1 :]), i + 2
    return None, text, 1


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(fm: str) -> tuple[dict, list[str]]:
    """Parse the small YAML subset used by SKILL.md frontmatter.

    Supports top-level `key: value`, plain multi-line scalars continued on
    indented lines, block scalars (| and >), and one level of nested mapping
    (for metadata). For full YAML validation use the skills-ref tool.
    """
    data: dict = {}
    problems: list[str] = []
    key = None
    mode = None  # "scalar", "block", "map"
    for raw in fm.split("\n"):
        if not raw.strip() or raw.lstrip().startswith("#"):
            if mode == "block" and key:
                data[key] += "\n"
            continue
        indented = raw[0] in " \t"
        if not indented:
            m = re.match(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$", raw)
            if not m:
                problems.append(f"cannot parse frontmatter line: {raw!r}")
                key = mode = None
                continue
            key, value = m.group(1), (m.group(2) or "").strip()
            if key in data:
                problems.append(f"duplicate frontmatter key: {key}")
            if value in ("|", ">", "|-", ">-"):
                data[key], mode = "", "block"
            elif value == "":
                data[key], mode = {}, "map"
            else:
                data[key], mode = unquote(value), "scalar"
            continue
        if key is None:
            problems.append(f"indented line without a key: {raw!r}")
            continue
        stripped = raw.strip()
        if mode == "map":
            m = re.match(r"^([A-Za-z0-9_.-]+):\s*(.*)$", stripped)
            if m and isinstance(data[key], dict):
                data[key][m.group(1)] = unquote(m.group(2))
            else:
                problems.append(f"cannot parse nested line under {key}: {raw!r}")
        elif mode == "block":
            data[key] += ("\n" if data[key] else "") + stripped
        else:
            data[key] = f"{data[key]} {stripped}"
    for k, v in data.items():
        if isinstance(v, str):
            data[k] = v.strip()
    return data, problems


# --------------------------------------------------------------------- skills

def check_skills(root: str, report: Report) -> None:
    skills_dir = os.path.join(root, "skills")
    if not os.path.isdir(skills_dir):
        return
    for entry in sorted(os.listdir(skills_dir)):
        skill_dir = os.path.join(skills_dir, entry)
        if not os.path.isdir(skill_dir):
            continue
        path = os.path.join(skill_dir, "SKILL.md")
        rpath = rel(root, path)
        if not os.path.isfile(path):
            report.error(rel(root, skill_dir), "skill folder has no SKILL.md")
            continue
        report.count("skills")
        text = read(path)
        fm, body, body_start = split_frontmatter(text)
        if fm is None:
            report.error(rpath, "missing YAML frontmatter delimited by --- lines", 1)
            continue
        data, problems = parse_frontmatter(fm)
        for p in problems:
            report.error(rpath, p)
        for k in sorted(set(data) - SKILL_FIELDS):
            report.error(rpath, f"unknown frontmatter field {k!r} (allowed: {', '.join(sorted(SKILL_FIELDS))})")

        name = data.get("name")
        if not isinstance(name, str) or not name:
            report.error(rpath, "frontmatter 'name' is required")
        else:
            if len(name) > SKILL_NAME_MAX:
                report.error(rpath, f"name is {len(name)} chars, max {SKILL_NAME_MAX}")
            if not SKILL_NAME_RE.match(name):
                report.error(rpath, "name must be lowercase letters, digits and single hyphens, "
                             "not starting or ending with a hyphen")
            if name != entry:
                report.error(rpath, f"name {name!r} must match folder name {entry!r}")

        desc = data.get("description")
        if not isinstance(desc, str) or not desc:
            report.error(rpath, "frontmatter 'description' is required")
        elif len(desc) > SKILL_DESCRIPTION_MAX:
            report.error(rpath, f"description is {len(desc)} chars, max {SKILL_DESCRIPTION_MAX}")

        compat = data.get("compatibility")
        if isinstance(compat, str) and len(compat) > SKILL_COMPATIBILITY_MAX:
            report.error(rpath, f"compatibility is {len(compat)} chars, max {SKILL_COMPATIBILITY_MAX}")
        if "metadata" in data and not isinstance(data["metadata"], dict):
            report.error(rpath, "metadata must be a mapping")

        body_lines = body.strip("\n").split("\n") if body.strip() else []
        if not body_lines:
            report.error(rpath, "SKILL.md body is empty")
        if len(body_lines) > SKILL_BODY_MAX_LINES:
            report.error(rpath, f"body is {len(body_lines)} lines, keep it under {SKILL_BODY_MAX_LINES}")
        tokens = len(body) // 4
        if tokens > SKILL_BODY_MAX_TOKENS:
            report.error(rpath, f"body is about {tokens} tokens, keep it under {SKILL_BODY_MAX_TOKENS}")

        for offset, line in enumerate(body.split("\n")):
            for ref in SKILL_REF_RE.findall(line):
                target = os.path.join(skill_dir, ref.rstrip("/."))
                if not os.path.exists(target) and not re.search(r"[<>*]", ref):
                    report.error(rpath, f"referenced file {ref!r} does not exist in the skill folder",
                                 body_start + offset)

        check_evals(root, skill_dir, report)


def check_evals(root: str, skill_dir: str, report: Report) -> None:
    evals_dir = os.path.join(skill_dir, "evals")
    rdir = rel(root, evals_dir)
    files = sorted(f for f in os.listdir(evals_dir) if f.endswith(".md")) if os.path.isdir(evals_dir) else []
    if not files:
        report.error(rdir, "skill has no eval cases (expected evals/*.md)")
        return
    cases: list[dict] = []
    for fname in files:
        path = os.path.join(evals_dir, fname)
        rpath = rel(root, path)
        current = None
        for lineno, line in enumerate(read(path).split("\n"), 1):
            m = re.match(r"^## Case:\s*(.*)$", line)
            if m:
                current = {"id": m.group(1).strip(), "file": rpath, "line": lineno,
                           "type": None, "prompt": False, "expect": 0, "in_expect": False}
                cases.append(current)
                continue
            if line.startswith("## ") or current is None:
                current = None if line.startswith("## ") else current
                continue
            t = re.match(r"^- Type:\s*(\S+)\s*$", line)
            if t:
                current["type"] = t.group(1)
                current["in_expect"] = False
            elif re.match(r"^- Prompt:\s*\S", line):
                current["prompt"] = True
                current["in_expect"] = False
            elif re.match(r"^- Expect:\s*$", line):
                current["in_expect"] = True
            elif current["in_expect"] and re.match(r"^\s{2,}- \S", line):
                current["expect"] += 1
    seen: set[str] = set()
    for c in cases:
        report.count("eval cases")
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", c["id"]):
            report.error(c["file"], f"case id {c['id']!r} must be lowercase-hyphenated", c["line"])
        if c["id"] in seen:
            report.error(c["file"], f"duplicate case id {c['id']!r}", c["line"])
        seen.add(c["id"])
        if c["type"] not in ("positive", "negative"):
            report.error(c["file"], f"case {c['id']!r} needs '- Type: positive' or '- Type: negative'", c["line"])
        if not c["prompt"]:
            report.error(c["file"], f"case {c['id']!r} needs a non-empty '- Prompt:' line", c["line"])
        if c["expect"] == 0:
            report.error(c["file"], f"case {c['id']!r} needs '- Expect:' with at least one indented bullet",
                         c["line"])
    if len(cases) < EVAL_MIN_CASES:
        report.error(rdir, f"{len(cases)} eval cases, need at least {EVAL_MIN_CASES}")
    types = {c["type"] for c in cases}
    if "positive" not in types:
        report.error(rdir, "need at least one positive case (the skill should activate)")
    if "negative" not in types:
        report.error(rdir, "need at least one negative case (the skill should not activate)")


# -------------------------------------------------------------------- budgets

def check_budgets(root: str, report: Report) -> None:
    root_agents = os.path.join(root, "AGENTS.md")
    if not os.path.isfile(root_agents):
        report.error("AGENTS.md", "root AGENTS.md is missing")
    for path in walk(root):
        name = os.path.basename(path)
        if name not in ("AGENTS.md", "CLAUDE.md"):
            continue
        report.count("instruction files")
        n = len(read(path).splitlines())
        if n > INSTRUCTION_MAX_LINES:
            report.error(rel(root, path), f"{n} lines, budget is {INSTRUCTION_MAX_LINES}")
        if name == "CLAUDE.md":
            first = (read(path).splitlines() or [""])[0].strip()
            sibling = os.path.join(os.path.dirname(path), "AGENTS.md")
            if os.path.isfile(sibling) and first != "@AGENTS.md":
                report.error(rel(root, path), "first line must be @AGENTS.md so AGENTS.md stays the "
                             "single source of truth", 1)

    mem = os.path.join(root, MEMORY_PATH)
    if os.path.isfile(mem):
        report.count("memory files")
        data = read(mem)
        n = len(data.splitlines())
        size = len(data.encode("utf-8"))
        if n > MEMORY_MAX_LINES:
            report.error(MEMORY_PATH, f"{n} lines, budget is {MEMORY_MAX_LINES} (only the first "
                         f"{MEMORY_MAX_LINES} load); prune or move history to decisions.md")
        if size > MEMORY_MAX_BYTES:
            report.error(MEMORY_PATH, f"{size} bytes, budget is {MEMORY_MAX_BYTES}")
        bullets = [l.strip().lower() for l in data.splitlines() if l.startswith("- ")]
        dupes = sorted({b for b in bullets if bullets.count(b) > 1})
        for d in dupes:
            report.error(MEMORY_PATH, f"duplicate line: {d!r}")


# ------------------------------------------------------------------ decisions

def parse_decisions(text: str, path: str, report: Report) -> list[tuple[int, str]]:
    """Return (line number, heading) of each entry; report format errors."""
    lines = text.split("\n")
    entries: list[tuple[int, int]] = []  # (start index, end index)
    for i, line in enumerate(lines):
        if line.startswith("## "):
            entries.append((i, len(lines)))
        elif line.startswith("# ") and i > 0 and entries:
            report.error(path, "only one '# ' title is allowed, at the top", i + 1)
    entries = [(s, entries[k + 1][0] if k + 1 < len(entries) else len(lines)) for k, (s, _) in enumerate(entries)]
    today = dt.datetime.now(dt.timezone.utc).date()
    prev_date = None
    out = []
    for start, end in entries:
        heading = lines[start]
        out.append((start + 1, heading))
        m = DECISION_HEADING_RE.match(heading)
        if not m:
            report.error(path, "entry heading must be '## YYYY-MM-DD  Decision' (two spaces after the date)",
                         start + 1)
            continue
        try:
            date = dt.date.fromisoformat(m.group(1))
        except ValueError:
            report.error(path, f"invalid date {m.group(1)}", start + 1)
            continue
        if date > today + dt.timedelta(days=1):
            report.error(path, f"date {date} is in the future", start + 1)
        if prev_date and date < prev_date:
            report.error(path, f"date {date} is earlier than the previous entry ({prev_date}); "
                         "append new entries at the end", start + 1)
        prev_date = date
        body = [l for l in lines[start + 1 : end] if l.strip()]
        if not any(l.startswith("Why: ") and len(l) > 5 for l in body):
            report.error(path, "entry needs a 'Why: ...' line", start + 1)
        if not any("Ref: " in l for l in body):
            report.error(path, "entry needs a 'Ref: ...' (PR, issue, incident or file)", start + 1)
        if not any(re.match(r"^Supersedes: \S", l) for l in body):
            report.error(path, "entry needs a 'Supersedes: none | <date title>' line", start + 1)
    return out


def git_show(root: str, ref: str, path: str) -> str | None:
    try:
        res = subprocess.run(["git", "-C", root, "show", f"{ref}:{path}"], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return res.stdout if res.returncode == 0 else None


def check_append_only(base_text: str, current_text: str, path: str, report: Report) -> None:
    """Every entry in base must still be present, unchanged, in the same order, at the start."""
    def entries(text: str) -> list[str]:
        parts = re.split(r"(?m)^(?=## )", text)
        return [p.rstrip() for p in parts[1:]]

    old, new = entries(base_text), entries(current_text)
    for i, entry in enumerate(old):
        if i >= len(new):
            report.error(path, f"entry removed: {entry.splitlines()[0]!r}")
            continue
        if new[i] != entry:
            report.error(path, f"existing entry changed or reordered: {entry.splitlines()[0]!r}. "
                         "decisions.md is append-only; add a new entry with Supersedes instead")


def check_decisions(root: str, base: str | None, report: Report) -> None:
    path = os.path.join(root, DECISIONS_PATH)
    if not os.path.isfile(path):
        return
    report.count("decision logs")
    text = read(path)
    parse_decisions(text, DECISIONS_PATH, report)
    if base:
        base_text = git_show(root, base, DECISIONS_PATH)
        if base_text is None:
            print(f"note: {DECISIONS_PATH} not found at {base}; skipping append-only check")
        else:
            report.count("append-only comparisons")
            check_append_only(base_text, text, DECISIONS_PATH, report)


# -------------------------------------------------------------------- secrets

def knowledge_files(root: str):
    for path in walk(root):
        r = rel(root, path)
        top = r.split("/", 1)[0]
        if os.path.basename(path) in KNOWLEDGE_NAMES or top in KNOWLEDGE_DIRS:
            yield path, r


def check_secrets(root: str, report: Report) -> None:
    for path, r in knowledge_files(root):
        try:
            text = read(path)
        except (UnicodeDecodeError, OSError):
            continue
        report.count("files scanned for secrets")
        for lineno, line in enumerate(text.split("\n"), 1):
            for label, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    report.error(r, f"possible secret ({label}); remove it and rotate it if real", lineno)
            for email in EMAIL_RE.findall(line):
                domain = email.rsplit("@", 1)[1].lower()
                if not domain.endswith(EMAIL_ALLOWED_DOMAINS):
                    report.error(r, "email address in a knowledge file; use a team handle instead", lineno)


# --------------------------------------------------------------------- owners

def check_codeowners(root: str, report: Report) -> None:
    for candidate in (".github/CODEOWNERS", "CODEOWNERS", "docs/CODEOWNERS"):
        path = os.path.join(root, candidate)
        if os.path.isfile(path):
            break
    else:
        report.error(".github/CODEOWNERS", "missing; knowledge files must be routed to a team")
        return
    covered = set()
    for lineno, line in enumerate(read(path).split("\n"), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        pattern, *owners = line.split()
        covered.add(pattern)
        if not owners:
            report.error(candidate, f"{pattern} has no owner", lineno)
        for owner in owners:
            if not re.match(r"^@[\w.-]+/[\w.-]+$", owner):
                report.error(candidate, f"owner {owner!r} is not a team (@org/team); "
                             "no path should be owned by one person", lineno)
    for needed in ("/AGENTS.md", "**/AGENTS.md", "/skills/", "/docs/agent-memory/"):
        if needed not in covered:
            report.error(candidate, f"no rule for {needed}")


# ----------------------------------------------------------------------- main

def run(root: str, base: str | None = None) -> Report:
    report = Report()
    check_skills(root, report)
    check_budgets(root, report)
    check_decisions(root, base, report)
    check_secrets(root, report)
    check_codeowners(root, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    parser.add_argument("--base", help="git ref to compare decisions.md against (append-only check)")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    report = run(root, args.base)
    summary = ", ".join(f"{v} {k}" for k, v in report.checked.items())
    print(f"checked: {summary}")
    if report.errors:
        print(f"\n{len(report.errors)} error(s):")
        for e in report.errors:
            print(f"  {e}")
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
