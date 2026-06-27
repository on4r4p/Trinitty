import importlib.util
import os
import re
import subprocess
import unittest
import ast
from glob import glob
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRINITTY = ROOT / "trinitty.py"


class TrinittyStaticRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TRINITTY.read_text()

    def test_script_path_concatenations_keep_path_separator(self):
        bad_matches = re.findall(r'SCRIPT_PATH\s*\+\s*"[^/]', self.source)
        self.assertEqual([], bad_matches)

    def test_wikipedia_import_is_enabled(self):
        self.assertIn('wikipedia = Optional_Import("wikipedia")', self.source)
        self.assertNotIn("#,wikipedia", self.source)

    def test_history_best_answer_uses_append(self):
        self.assertNotIn("Best_Answer(hist_output)", self.source)
        self.assertEqual(2, self.source.count("Best_Answer.append(hist_output)"))

    def test_sigint_handler_is_not_overwritten(self):
        self.assertEqual(1, self.source.count("signal.signal(signal.SIGINT"))

    def test_runtime_queues_are_not_read_with_blocking_get(self):
        queue_names = {
            "record_on",
            "chunks",
            "wake_me_up",
            "awake",
            "cancel_operation",
            "No_Input",
            "score_sentiment",
            "audio_datas",
            "last_sentence",
        }
        tree = ast.parse(self.source)
        blocking_gets = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
                continue
            if node.keywords:
                continue
            if isinstance(node.func.value, ast.Name) and node.func.value.id in queue_names:
                blocking_gets.append((node.func.value.id, node.lineno))

        self.assertEqual([], blocking_gets)

    def test_local_config_override_is_ignored(self):
        gitignore = (ROOT / ".gitignore").read_text()
        conf = (ROOT / "datas" / "conf.trinity").read_text()

        self.assertIn("datas/*.local.trinity", gitignore)
        self.assertIn("SAVED_ANSWER = default", conf)
        self.assertIn("CHECK_UPDATE = False", conf)
        self.assertIn("DEBUG = False", conf)
        self.assertIn("RESPONSE_STREAMING_ENABLED = False", conf)
        self.assertIn("HISTORY_INDEX_ENABLED = True", conf)
        self.assertIn("datas/conf.local.trinity", self.source)
        self.assertNotIn("g4f.Provider.you", self.source)

    def test_private_runtime_directories_keep_only_gitkeep(self):
        gitignore = (ROOT / ".gitignore").read_text()

        self.assertIn("keys/*", gitignore)
        self.assertIn("!keys/.gitkeep", gitignore)
        self.assertIn("history/*", gitignore)
        self.assertIn("!history/.gitkeep", gitignore)
        self.assertIn("tools/", gitignore)
        self.assertTrue((ROOT / "keys" / ".gitkeep").exists())
        self.assertTrue((ROOT / "history" / ".gitkeep").exists())

    def test_install_dependencies_creates_clean_user_launcher(self):
        installer = (ROOT / "install_dependencies.sh").read_text()
        pyproject = (ROOT / "pyproject.toml").read_text()

        self.assertIn("install_user_launcher()", installer)
        self.assertIn("--no-launcher", installer)
        self.assertIn('"trinitty" = ["install_dependencies.sh", "requirements.txt"]', pyproject)
        self.assertIn("export PYTHONNOUSERSITE=1", installer)
        self.assertIn("unset PYTHONPATH", installer)
        self.assertIn('"$launcher_dir/$LAUNCHER_NAME"', installer)

    def test_pyproject_packages_all_local_sound_wavs(self):
        pyproject = (ROOT / "pyproject.toml").read_text()
        patterns = re.findall(r'"(local_sounds/[^"]+\.wav)"', pyproject)
        covered = set()
        for pattern in patterns:
            covered.update(Path(path).relative_to(ROOT).as_posix() for path in glob(str(ROOT / pattern)))

        excluded_prefixes = ("local_sounds/saved_answer/saved_error/",)
        local_wavs = {
            path.relative_to(ROOT).as_posix()
            for path in (ROOT / "local_sounds").rglob("*.wav")
            if not path.relative_to(ROOT).as_posix().startswith(excluded_prefixes)
        }

        self.assertEqual([], sorted(local_wavs - covered))

    def test_pyproject_packages_update_info_note(self):
        pyproject = (ROOT / "pyproject.toml").read_text()

        self.assertTrue((ROOT / "datas" / "update_info.trinity").exists())
        self.assertIn('"datas/update_info.trinity"', pyproject)

    def test_update_info_matches_project_version_and_contains_recap(self):
        pyproject = (ROOT / "pyproject.toml").read_text()
        update_info = (ROOT / "datas" / "update_info.trinity").read_text()
        pyproject_version = re.search(r'^version = "([^"]+)"', pyproject, flags=re.MULTILINE)
        update_version = re.search(r"^Version:\s*(\S+)", update_info, flags=re.MULTILINE)

        self.assertIsNotNone(pyproject_version)
        self.assertIsNotNone(update_version)
        self.assertEqual(pyproject_version.group(1), update_version.group(1))

        for heading in ["Titre:", "Résumé:", "Changements principaux:"]:
            self.assertIn(heading, update_info)

        summary_match = re.search(
            r"Résumé:\s*(.+?)\n\s*Changements principaux:",
            update_info,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(summary_match)
        self.assertGreaterEqual(len(summary_match.group(1).strip()), 80)

    def test_project_uses_trinitty_entrypoint_name(self):
        gitignore = (ROOT / ".gitignore").read_text()
        project_files = [
            ROOT / "README.md",
            ROOT / "pyproject.toml",
            ROOT / "install_dependencies.sh",
            ROOT / ".gitignore",
            ROOT / "trinitty.py",
        ]
        combined = "\n".join(path.read_text() for path in project_files)

        self.assertTrue(TRINITTY.exists())
        self.assertFalse((ROOT / "trinity.py").exists())
        self.assertFalse((ROOT / "Trinity.py").exists())
        self.assertIn(".venv-trinitty/", gitignore)
        self.assertNotIn(".venv-trinity/", gitignore)
        self.assertNotRegex(combined, r"\b(?:Trinity|trinity)\.py\b")

    def test_add_trigger_writes_function_before_trigger(self):
        self.assertIn("Write_csv(funcname, trigger, ALTFILE)", self.source)
        self.assertIn("Write_csv(funcname, to_check, ALTFILE)", self.source)
        self.assertIn("Write_csv(func_name_to_add, trigger_input, ALTFILE)", self.source)
        self.assertNotIn("Write_csv(trigger, funcname, ALTFILE)", self.source)
        self.assertNotIn("Write_csv(to_check, funcname, ALTFILE)", self.source)
        self.assertNotIn("Write_csv(trigger_input, func_name_to_add, ALTFILE)", self.source)

    def test_installer_installs_packaging_tools_for_local_builds(self):
        installer = (ROOT / "install_dependencies.sh").read_text()

        self.assertIn('"build>=1.2"', installer)
        self.assertIn('"twine>=5.1"', installer)
        self.assertIn("TRINITTY_INSTALL_DEV_TOOLS", installer)
        self.assertIn("--no-dev-tools", installer)

    def test_pypi_workflow_uses_trusted_publishing_without_required_environment(self):
        workflow = (ROOT / ".github" / "workflows" / "publish-pypi.yml").read_text()
        publish_job = workflow.split("  publish:", 1)[1]

        self.assertIn("quality:", workflow)
        self.assertIn("secrets:", workflow)
        self.assertIn("python -m ruff check", workflow)
        self.assertIn("python -m pytest", workflow)
        self.assertIn("python -m build", workflow)
        self.assertIn("python -m twine check --strict dist/*", workflow)
        self.assertIn("gitleaks/gitleaks-action@v3", workflow)
        self.assertIn("actions/checkout@v6", workflow)
        self.assertIn("id-token: write", publish_job)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", publish_job)
        self.assertNotIn("environment:", publish_job)
        self.assertNotIn("name: pypi", publish_job)

    def test_pre_commit_runs_ruff_and_gitleaks(self):
        precommit = (ROOT / ".pre-commit-config.yaml").read_text()
        gitleaks = (ROOT / ".gitleaks.toml").read_text()

        self.assertIn("ruff-pre-commit", precommit)
        self.assertIn("github.com/gitleaks/gitleaks", precommit)
        self.assertIn("v8.30.1", precommit)
        self.assertIn("^keys/\\.gitkeep$", gitleaks)
        self.assertNotIn("README", gitleaks)

    def test_tracked_files_do_not_include_secret_locations(self):
        tracked = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines()
        forbidden = [
            "keys/google_adc.json",
            "old/token.py",
            "keys/openai.key",
            "keys/google_search.key",
            "keys/google_translate.key",
            "keys/detectlanguage.key",
            "keys/pico.key",
        ]

        for path in forbidden:
            self.assertNotIn(path, tracked)

        sensitive_patterns = [
            re.compile(r"keys/.*\.(key|id)$"),
            re.compile(r"google_adc\.json$"),
            re.compile(r"old/token\.py$"),
        ]
        offenders = [
            path
            for path in tracked
            if any(pattern.search(path) for pattern in sensitive_patterns)
            and path not in {"keys/.gitkeep"}
        ]
        self.assertEqual([], offenders)

    def test_source_and_package_config_do_not_contain_obvious_secrets(self):
        files = [
            ROOT / "trinitty.py",
            ROOT / "gitup.py",
            ROOT / "pyproject.toml",
            ROOT / "README.md",
            ROOT / "datas" / "conf.trinity",
        ]
        combined = "\n".join(path.read_text(errors="ignore") for path in files)

        self.assertNotRegex(combined, r"sk-[A-Za-z0-9_-]{20,}")
        self.assertNotRegex(combined, r"AIza[0-9A-Za-z_-]{20,}")
        self.assertNotRegex(combined, r"refresh_token\s*[:=]")
        self.assertNotRegex(combined, r"-----BEGIN PRIVATE KEY-----")
        self.assertNotRegex(combined, r"private_key\s*[:=]")

    def test_import_does_not_override_google_credentials_env(self):
        env_name = "GOOGLE_APPLICATION_CREDENTIALS"
        original = os.environ.get(env_name)
        existing_credentials = "/opt/trinitty/existing-google-credentials.json"
        os.environ[env_name] = existing_credentials
        try:
            spec = importlib.util.spec_from_file_location("trinitty_env_regression", TRINITTY)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(existing_credentials, os.environ[env_name])
        finally:
            if original is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = original

    def test_literal_asset_references_exist(self):
        ignored_literals = {
            "datas/conf.local.trinity",
            "datas/command_classifier.keras",
            "local_sounds/cmd/hit",
            "local_sounds/cmd/intro_",
            "local_sounds/cmd/outro_",
            "models/vosk-model-small-fr-0.22",
        }
        missing = []
        for path in [TRINITTY]:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                text = node.value
                if "\n" in text:
                    continue
                for token in ("local_sounds/", "models/", "datas/"):
                    if token not in text:
                        continue
                    rel = text[text.find(token):]
                    for separator in ("%", "{", '"', "'", " "):
                        rel = rel.split(separator, 1)[0]
                    rel = rel.strip().rstrip("/")
                    if not rel or rel in ignored_literals:
                        continue
                    if not (ROOT / rel).exists():
                        missing.append(f"{path.relative_to(ROOT)}:{node.lineno}:{rel}")

        self.assertEqual([], missing)

    def test_add_trigger_help_covers_declared_command_functions(self):
        declared_functions = set()
        for csv_name in ("cmd.trinity", "alt_cmd.trinity"):
            for line in (ROOT / "datas" / csv_name).read_text().splitlines()[1:]:
                if not line.strip() or "," not in line:
                    continue
                function_id = line.split(",", 1)[0 if csv_name == "cmd.trinity" else 1].strip()
                if function_id.startswith("F_"):
                    declared_functions.add(function_id)

        for line in (ROOT / "datas" / "action.trinity").read_text().splitlines()[1:]:
            if not line.strip() or "," not in line:
                continue
            for raw_function_id in line.rsplit(",", 1)[-1].split("***"):
                function_id = raw_function_id.strip()
                if function_id.startswith("F_"):
                    declared_functions.add(function_id)

        tree = ast.parse(self.source)
        add_trigger = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "Add_Trigger")
        add_trigger_functions = {
            node.value
            for node in ast.walk(add_trigger)
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("F_")
        }

        self.assertLessEqual(declared_functions, add_trigger_functions)


if __name__ == "__main__":
    unittest.main()
