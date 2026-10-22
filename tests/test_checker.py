"""Tests for tools/check_agent_knowledge.py. Run with: make test"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "tools"))

import check_agent_knowledge as ck  # noqa: E402


def write(root, path, text):
    full = os.path.join(root, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)


class RepoTest(unittest.TestCase):
    """Each test starts from a copy of this repo and breaks one thing."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "repo")
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(".git", "__pycache__"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def errors(self, base=None):
        return ck.run(self.root, base).errors

    def assertError(self, fragment, base=None):
        errs = self.errors(base)
        self.assertTrue(any(fragment in e for e in errs), f"{fragment!r} not in {errs}")

    def test_repo_is_clean(self):
        self.assertEqual(self.errors(), [])

    def test_skill_name_must_match_folder(self):
        p = os.path.join(self.root, "skills/release-notes/SKILL.md")
        text = ck.read(p).replace("name: release-notes", "name: release-note")
        write(self.root, "skills/release-notes/SKILL.md", text)
        self.assertError("must match folder name")

    def test_skill_name_charset(self):
        write(self.root, "skills/Bad--Name/SKILL.md", "---\nname: Bad--Name\ndescription: x\n---\nbody\n")
        self.assertError("lowercase letters, digits and single hyphens")

    def test_description_limit(self):
        desc = "a" * 1025
        write(self.root, "skills/long/SKILL.md", f"---\nname: long\ndescription: {desc}\n---\nbody\n")
        self.assertError("max 1024")

    def test_missing_referenced_file(self):
        p = os.path.join(self.root, "skills/migration-review/references/rollback.md")
        os.remove(p)
        self.assertError("referenced file 'references/rollback.md' does not exist")

    def test_skill_without_evals(self):
        shutil.rmtree(os.path.join(self.root, "skills/release-notes/evals"))
        self.assertError("skill has no eval cases")

    def test_eval_needs_negative_case(self):
        write(self.root, "skills/release-notes/evals/cases.md",
              "## Case: one\n- Type: positive\n- Prompt: hi\n- Expect:\n  - ok\n\n"
              "## Case: two\n- Type: positive\n- Prompt: hi\n- Expect:\n  - ok\n")
        self.assertError("need at least one negative case")

    def test_eval_case_needs_expectations(self):
        write(self.root, "skills/release-notes/evals/cases.md",
              "## Case: one\n- Type: positive\n- Prompt: hi\n- Expect:\n\n"
              "## Case: two\n- Type: negative\n- Prompt: hi\n- Expect:\n  - ok\n")
        self.assertError("at least one indented bullet")

    def test_agents_md_budget(self):
        write(self.root, "services/invoicing/AGENTS.md", "line\n" * 201)
        self.assertError("201 lines, budget is 200")

    def test_claude_md_must_import_agents(self):
        write(self.root, "CLAUDE.md", "# Claude instructions\n")
        self.assertError("first line must be @AGENTS.md")

    def test_memory_budget(self):
        p = os.path.join(self.root, ck.MEMORY_PATH)
        extra = "".join(f"- fact {i}\n" for i in range(200))
        write(self.root, ck.MEMORY_PATH, ck.read(p) + extra)
        self.assertError("budget is 200")

    def test_memory_duplicate_line(self):
        p = os.path.join(self.root, ck.MEMORY_PATH)
        write(self.root, ck.MEMORY_PATH, ck.read(p) + "- Keep PRs small. Knowledge updates go in their own PR, "
              "not mixed with code.\n")
        self.assertError("duplicate line")

    def test_decision_heading_format(self):
        p = os.path.join(self.root, ck.DECISIONS_PATH)
        write(self.root, ck.DECISIONS_PATH, ck.read(p) + "\n## 2026-10-30 one space\nWhy: x. Ref: y\n"
              "Supersedes: none\n")
        self.assertError("two spaces after the date")

    def test_decision_dates_in_order(self):
        p = os.path.join(self.root, ck.DECISIONS_PATH)
        write(self.root, ck.DECISIONS_PATH, ck.read(p) + "\n## 2026-01-01  Backdated\nWhy: x. Ref: y\n"
              "Supersedes: none\n")
        self.assertError("earlier than the previous entry")

    def test_decision_needs_supersedes(self):
        p = os.path.join(self.root, ck.DECISIONS_PATH)
        write(self.root, ck.DECISIONS_PATH, ck.read(p) + "\n## 2026-10-22  No supersedes\nWhy: x. Ref: y\n")
        self.assertError("Supersedes")

    def test_append_only(self):
        base = "# Log\n\n## 2026-10-01  A\nWhy: a. Ref: x\nSupersedes: none\n"
        report = ck.Report()
        ck.check_append_only(base, base + "\n## 2026-10-02  B\nWhy: b. Ref: y\nSupersedes: none\n", "d.md", report)
        self.assertEqual(report.errors, [])
        ck.check_append_only(base, base.replace("Why: a.", "Why: edited."), "d.md", report)
        self.assertTrue(any("changed or reordered" in e for e in report.errors))
        report = ck.Report()
        ck.check_append_only(base, "# Log\n", "d.md", report)
        self.assertTrue(any("entry removed" in e for e in report.errors))

    def test_append_only_against_git_base(self):
        def git(*args):
            subprocess.run(["git", "-C", self.root, *args], check=True, capture_output=True)
        git("init", "-q")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "add", "-A")
        git("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-qm", "base")
        p = os.path.join(self.root, ck.DECISIONS_PATH)
        write(self.root, ck.DECISIONS_PATH, ck.read(p).replace("float rounding", "rounding"))
        self.assertError("changed or reordered", base="HEAD")

    def test_secret_patterns(self):
        fake = "gh" + "p_" + "A" * 36
        write(self.root, "skills/release-notes/references/notes.md", f"token is {fake}\n")
        self.assertError("possible secret (GitHub token)")

    def test_private_key_block(self):
        write(self.root, ck.MEMORY_PATH, "-----BEGIN RSA " + "PRIVATE KEY-----\n")
        self.assertError("Private key block")

    def test_email_is_flagged(self):
        write(self.root, "docs/agent-memory/MEMORY.md", "- Ask jane.doe@" + "corp.test about tax.\n")
        self.assertError("email address")

    def test_codeowners_must_be_teams(self):
        write(self.root, ".github/CODEOWNERS", "/AGENTS.md @someone\n**/AGENTS.md @a/b\n/skills/ @a/b\n"
              "/docs/agent-memory/ @a/b\n")
        self.assertError("is not a team")


class FrontmatterTest(unittest.TestCase):
    def test_folded_and_nested(self):
        fm = 'name: x\ndescription: first line\n  second line\nmetadata:\n  owner: "@a/b"\n  version: "3"\n'
        data, problems = ck.parse_frontmatter(fm)
        self.assertEqual(problems, [])
        self.assertEqual(data["description"], "first line second line")
        self.assertEqual(data["metadata"], {"owner": "@a/b", "version": "3"})


if __name__ == "__main__":
    unittest.main()
