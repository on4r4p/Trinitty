import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_gitup():
    spec = importlib.util.spec_from_file_location("trinitty_gitup_test", ROOT / "gitup.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GitupTests(unittest.TestCase):
    def test_last_sha_legacy_api_is_removed(self):
        gitup = load_gitup()

        self.assertFalse(hasattr(gitup, "read_last_sha"))
        self.assertFalse(hasattr(gitup, "write_last_sha"))
        self.assertFalse(hasattr(gitup, "LAST_SHA_RE"))

    def test_read_project_version(self):
        gitup = load_gitup()

        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            pyproject_file = Path(tmp) / "pyproject.toml"
            pyproject_file.write_text('[project]\nname = "trinitty"\nversion = "0.1.7"\n')

            self.assertEqual("0.1.7", gitup.read_project_version(pyproject_file))

    def test_version_newer_compares_multi_digit_versions(self):
        gitup = load_gitup()

        self.assertTrue(gitup.version_newer("0.1.10", "0.1.6"))
        self.assertFalse(gitup.version_newer("0.1.6", "0.1.10"))
        self.assertFalse(gitup.version_newer("", "0.1.6"))


if __name__ == "__main__":
    unittest.main()
