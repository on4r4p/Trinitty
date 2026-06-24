import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_gitup():
    spec = importlib.util.spec_from_file_location("trinitty_gitup_test", ROOT / "gitup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GitupTests(unittest.TestCase):
    def test_read_and_write_last_sha(self):
        gitup = load_gitup()
        old_sha = "1" * 40
        new_sha = "2" * 40

        with tempfile.TemporaryDirectory() as tmp:
            trinitty_file = Path(tmp) / "trinitty.py"
            trinitty_file.write_text('LAST_SHA = "%s"\nprint("keep")\n' % old_sha)

            self.assertEqual(old_sha, gitup.read_last_sha(trinitty_file))
            self.assertTrue(gitup.write_last_sha(trinitty_file, new_sha))
            self.assertEqual(new_sha, gitup.read_last_sha(trinitty_file))
            self.assertIn('print("keep")', trinitty_file.read_text())

    def test_write_last_sha_rejects_short_sha(self):
        gitup = load_gitup()

        with tempfile.TemporaryDirectory() as tmp:
            trinitty_file = Path(tmp) / "trinitty.py"
            trinitty_file.write_text('LAST_SHA = "%s"\n' % ("1" * 40))

            with self.assertRaises(ValueError):
                gitup.write_last_sha(trinitty_file, "abc123")

    def test_read_project_version(self):
        gitup = load_gitup()

        with tempfile.TemporaryDirectory() as tmp:
            pyproject_file = Path(tmp) / "pyproject.toml"
            pyproject_file.write_text('[project]\nname = "trinitty"\nversion = "0.1.7"\n')

            self.assertEqual("0.1.7", gitup.read_project_version(pyproject_file))

    def test_version_newer_compares_multi_digit_versions(self):
        gitup = load_gitup()

        self.assertTrue(gitup.version_newer("0.1.10", "0.1.6"))
        self.assertFalse(gitup.version_newer("0.1.6", "0.1.10"))
        self.assertFalse(gitup.version_newer("", "0.1.6"))

    def test_tools_wrapper_delegates_without_import_side_effects(self):
        spec = importlib.util.spec_from_file_location("trinitty_tools_gitup_test", ROOT / "tools" / "gitup.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(callable(module.main))


if __name__ == "__main__":
    unittest.main()
