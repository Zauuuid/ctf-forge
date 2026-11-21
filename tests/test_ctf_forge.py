import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from ctf_forge import kit, memory, skills, tools
from ctf_forge.cli import main
from ctf_forge.core import Runner


def run_cli(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(list(argv))
    return code, out.getvalue()


def make_skill_repo(root: Path, names):
    """Create a local git repo that looks like an upstream skills repository."""
    root.mkdir(parents=True)
    for name in names:
        (root / name).mkdir()
        (root / name / "SKILL.md").write_text("---\nname: {}\n---\n".format(name))
    (root / "README.md").write_text("upstream\n")
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.check_call(git + ["init", "-q", "-b", "main"], cwd=root)
    subprocess.check_call(git + ["add", "-A"], cwd=root)
    subprocess.check_call(git + ["commit", "-q", "-m", "init"], cwd=root)


class ToolsTests(unittest.TestCase):
    def test_package_sets_cover_all_platforms(self):
        for table in (tools.BASE, tools.TOOLS, tools.FULL_EXTRA):
            self.assertEqual(set(table), {"arch", "debian", "macos"})
            for names in table.values():
                self.assertEqual(len(names), len(set(names)), "duplicate package")

    def test_dry_run_prints_commands_for_each_distro(self):
        expectations = {
            "arch": "pacman -S --needed --noconfirm binwalk",
            "debian": "apt-get install -y binwalk",
            "macos": "brew install binwalk",
        }
        for distro, expected in expectations.items():
            code, out = run_cli("tools", "install", "--dry-run", "--distro", distro)
            self.assertEqual(code, 0)
            self.assertIn(expected, out)

    def test_skip_groups(self):
        _, out = run_cli("tools", "install", "--dry-run", "--distro", "debian",
                         "--skip", "base,tools,pipx,rsactftool,zsteg")
        self.assertNotIn("apt-get install", out)

    def test_no_aur_skips_aur_only_packages(self):
        _, out = run_cli("tools", "install", "--dry-run", "--distro", "arch", "--no-aur")
        self.assertNotIn("--noconfirm bkcrack", out)
        self.assertNotIn("yay -S", out)
        self.assertIn("skipped (AUR)", out)


class SkillsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.upstream = self.tmp / "upstream-skills"
        make_skill_repo(self.upstream, ["ctf-web", "ctf-crypto", "solve-challenge"])
        self.target = self.tmp / "agent" / "skills"
        self.store = self.tmp / "store"

    def install(self, **kw):
        return skills.install(Runner(), self.target, str(self.upstream), store=self.store, **kw)

    def test_install_links_every_skill(self):
        names = self.install()
        self.assertEqual(sorted(names), ["ctf-crypto", "ctf-web", "solve-challenge"])
        for name in names:
            self.assertTrue((self.target / name / "SKILL.md").is_file())

    def test_install_is_idempotent(self):
        self.install()
        self.assertEqual(len(self.install()), 3)

    def test_foreign_directory_is_not_overwritten(self):
        (self.target / "ctf-web").mkdir(parents=True)
        (self.target / "ctf-web" / "SKILL.md").write_text("mine")
        names = self.install()
        self.assertNotIn("ctf-web", names)
        self.assertEqual((self.target / "ctf-web" / "SKILL.md").read_text(), "mine")

    def test_copy_mode_and_update(self):
        self.install(copy=True)
        self.assertTrue((self.target / "ctf-web" / skills.MARKER).exists())
        (self.upstream / "ctf-new").mkdir()
        (self.upstream / "ctf-new" / "SKILL.md").write_text("x")
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.check_call(git + ["add", "-A"], cwd=self.upstream)
        subprocess.check_call(git + ["commit", "-q", "-m", "more"], cwd=self.upstream)
        names = self.install(copy=True, update=True)
        self.assertIn("ctf-new", names)

    def test_installed_lists_only_ctf_skills(self):
        self.install()
        (self.target / "other").mkdir()
        self.assertEqual(skills.installed(self.target),
                         ["ctf-crypto", "ctf-web", "solve-challenge"])

    def test_dry_run_changes_nothing(self):
        before = {str(p) for p in self.tmp.rglob("*")}
        run = Runner(dry_run=True)
        skills.install(run, self.target, str(self.upstream), store=self.store)
        self.assertEqual(before, {str(p) for p in self.tmp.rglob("*")})


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.vault = Path(tempfile.mkdtemp()) / "vault"

    def test_init_creates_template_and_keeps_existing_files(self):
        self.assertGreater(memory.init(self.vault), 5)
        (self.vault / "Home.md").write_text("custom")
        self.assertEqual(memory.init(self.vault), 0)
        self.assertEqual((self.vault / "Home.md").read_text(), "custom")

    def test_log_and_recall(self):
        memory.init(self.vault)
        note = memory.log(self.vault, "PicoCTF", "Small Exponent", "crypto", "solved",
                          "flag{x}", "cube root of the ciphertext")
        self.assertTrue(note.exists())
        hits = memory.recall(self.vault, ["cube", "root"])
        self.assertEqual(hits[0][0], note)
        self.assertEqual(memory.recall(self.vault, ["zzzz-nothing"]), [])

    def test_log_twice_appends(self):
        memory.log(self.vault, "ev", "chal", status="unsolved")
        note = memory.log(self.vault, "ev", "chal", status="solved", flag="f{1}")
        self.assertIn("Update", note.read_text())

    def test_slug_keeps_arabic(self):
        self.assertEqual(memory.slug("تحدي 1"), "تحدي-1")


class KitTests(unittest.TestCase):
    def test_list_contains_known_scripts(self):
        names = kit.list_scripts()
        self.assertIn("analyze/triage.sh", names)
        self.assertIn("crypto/identify-hash.sh", names)
        self.assertTrue(all("_lib" not in n for n in names))

    def test_run_rejects_unknown_and_escaping_paths(self):
        self.assertEqual(kit.run_script("nope/none.sh", []), 2)
        self.assertEqual(kit.run_script("../cli.py", []), 2)


class CliTests(unittest.TestCase):
    def test_help_and_version(self):
        code, out = run_cli()
        self.assertEqual(code, 0)
        self.assertIn("ctf-forge", out)

    def test_memory_commands(self):
        vault = str(Path(tempfile.mkdtemp()) / "v")
        self.assertEqual(run_cli("memory", "init", vault)[0], 0)
        code, _ = run_cli("memory", "log", "--vault", vault, "--event", "e", "--name", "n")
        self.assertEqual(code, 0)
        code, out = run_cli("memory", "recall", "--vault", vault, "n")
        self.assertEqual(code, 0)
        self.assertIn("Challenges", out)

    def test_kit_list(self):
        code, out = run_cli("kit", "list")
        self.assertEqual(code, 0)
        self.assertIn("analyze/triage.sh", out)


if __name__ == "__main__":
    unittest.main()
