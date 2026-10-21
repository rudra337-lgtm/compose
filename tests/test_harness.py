import hermetic  # first: no test sees the real home
import os, stat, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
os.environ["HERDR_ENV"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))
for _m in [m for m in sys.modules if m.startswith("fc_") and m not in ("fc_cost", "fc_mcp", "fc_sessions")]: del sys.modules[_m]
import fc_checks, fc_links


class CodexSkillLink(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.bin, self.home, self.co = tmp / "bin", tmp / "home", tmp / "co"
        for d in (self.bin, self.home, self.co): d.mkdir()
        p = mock.patch.dict(os.environ, {"PATH": str(self.bin), "HOME": str(self.home)}); p.start(); self.addCleanup(p.stop)
        os.environ.pop("CODEX_HOME", None)
        h = self.home
        self.three = [("compose CLI link", h / ".local/bin/compose", self.co / "bin/compose"),
                      ("compose skill link", h / ".claude/skills/compose", self.co), ("bp link", h / ".local/bin/bp", self.co / "bp/bin/bp.mjs")]

    def codex(self):
        (self.bin / "codex").write_text("#!/bin/sh\n"); (self.bin / "codex").chmod(stat.S_IRWXU)

    def test_codex_skills_follows_codex_home_else_home(self):
        self.assertEqual(fc_checks.codex_skills(), self.home / ".codex/skills")
        os.environ["CODEX_HOME"] = ""
        self.assertEqual(fc_checks.codex_skills(), self.home / ".codex/skills")
        os.environ["CODEX_HOME"] = str(self.home / "elsewhere")
        self.assertEqual(fc_checks.codex_skills(), self.home / "elsewhere/skills")

    def test_codex_on_path_adds_a_fourth_link(self):
        self.codex()
        self.assertEqual(fc_checks.owned_links(self.co), self.three + [("Codex skill link", self.home / ".codex/skills/compose", self.co)])
        os.environ["CODEX_HOME"] = str(self.home / "elsewhere")
        self.assertEqual(fc_checks.owned_links(self.co)[3], ("Codex skill link", self.home / "elsewhere/skills/compose", self.co))

    def test_no_codex_is_exactly_the_three_links(self):
        self.assertEqual(fc_checks.owned_links(self.co), self.three)
        os.environ["CODEX_HOME"] = str(self.home / "elsewhere")
        self.assertEqual(fc_checks.owned_links(self.co), self.three)

    def test_relink_without_codex_creates_no_codex_folder(self):
        os.environ["CODEX_HOME"] = str(self.home / "elsewhere")
        fc_links.relink_owned(self.co)
        self.assertFalse((self.home / ".codex").exists())
        self.assertFalse((self.home / "elsewhere").exists())

    def test_relink_with_codex_links_the_skill(self):
        self.codex()
        fc_links.relink_owned(self.co)
        self.assertEqual((self.home / ".codex/skills/compose").resolve(), self.co.resolve())
