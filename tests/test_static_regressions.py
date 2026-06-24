import importlib.util
import contextlib
import io
import os
import re
import tempfile
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
        self.assertIn("datas/conf.local.trinity", self.source)
        self.assertNotIn("g4f.Provider.you", self.source)

    def test_private_runtime_directories_keep_only_gitkeep(self):
        gitignore = (ROOT / ".gitignore").read_text()

        self.assertIn("keys/*", gitignore)
        self.assertIn("!keys/.gitkeep", gitignore)
        self.assertIn("history/*", gitignore)
        self.assertIn("!history/.gitkeep", gitignore)
        self.assertIn("tools/tool_history/*", gitignore)
        self.assertIn("!tools/tool_history/*.py", gitignore)
        self.assertIn("tools/*.wav", gitignore)
        self.assertTrue((ROOT / "keys" / ".gitkeep").exists())
        self.assertTrue((ROOT / "history" / ".gitkeep").exists())

    def test_install_dependencies_creates_clean_user_launcher(self):
        installer = (ROOT / "install_dependencies.sh").read_text()

        self.assertIn("install_user_launcher()", installer)
        self.assertIn("--no-launcher", installer)
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

    def test_tool_scripts_import_without_running_main(self):
        env_name = "GOOGLE_APPLICATION_CREDENTIALS"
        original_google_credentials = os.environ.get(env_name)
        scripts = [
            ROOT / "gitup.py",
            ROOT / "tools" / "changerate.py",
            ROOT / "tools" / "check_server.py",
            ROOT / "tools" / "checkinput.py",
            ROOT / "tools" / "checksrate.py",
            ROOT / "tools" / "cookies.py",
            ROOT / "tools" / "gitup.py",
            ROOT / "tools" / "makesound.py",
            ROOT / "tools" / "nbr.py",
            ROOT / "tools" / "rename.py",
        ]

        try:
            for index, path in enumerate(scripts):
                module_name = f"trinitty_tool_import_{index}_{path.stem}"
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)
                stdout = io.StringIO()
                stderr = io.StringIO()

                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    spec.loader.exec_module(module)

                self.assertEqual("", stdout.getvalue(), path.as_posix())
                self.assertEqual("", stderr.getvalue(), path.as_posix())
                self.assertTrue(callable(getattr(module, "main", None)), path.as_posix())
            self.assertEqual(original_google_credentials, os.environ.get(env_name))
        finally:
            if original_google_credentials is None:
                os.environ.pop(env_name, None)
            else:
                os.environ[env_name] = original_google_credentials

    def test_makesound_google_credentials_are_file_gated(self):
        env_name = "GOOGLE_APPLICATION_CREDENTIALS"
        original_google_credentials = os.environ.get(env_name)
        spec = importlib.util.spec_from_file_location("trinitty_makesound_credentials_test", ROOT / "tools" / "makesound.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                os.environ.pop(env_name, None)
                module.DEFAULT_GOOGLE_CREDENTIALS = str(root / "missing-google-adc.json")
                module.ensure_google_credentials()
                self.assertNotIn(env_name, os.environ)

                credentials = root / "google_adc.json"
                credentials.write_text("{}")
                module.DEFAULT_GOOGLE_CREDENTIALS = str(credentials)
                module.ensure_google_credentials()
                self.assertEqual(str(credentials), os.environ.get(env_name))

                user_credentials = root / "user-google.json"
                os.environ[env_name] = str(user_credentials)
                module.ensure_google_credentials()
                self.assertEqual(str(user_credentials), os.environ.get(env_name))
            finally:
                if original_google_credentials is None:
                    os.environ.pop(env_name, None)
                else:
                    os.environ[env_name] = original_google_credentials

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

    def test_installer_installs_packaging_tools_for_local_builds(self):
        installer = (ROOT / "install_dependencies.sh").read_text()

        self.assertIn('"build>=1.2"', installer)
        self.assertIn('"twine>=5.1"', installer)
        self.assertIn("TRINITTY_INSTALL_DEV_TOOLS", installer)
        self.assertIn("--no-dev-tools", installer)

    def test_pypi_workflow_uses_trusted_publishing_without_required_environment(self):
        workflow = (ROOT / ".github" / "workflows" / "publish-pypi.yml").read_text()
        publish_job = workflow.split("  publish:", 1)[1]

        self.assertIn("id-token: write", publish_job)
        self.assertIn("pypa/gh-action-pypi-publish@release/v1", publish_job)
        self.assertNotIn("environment:", publish_job)
        self.assertNotIn("name: pypi", publish_job)

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
            "datas/command_classifier.keras",
            "local_sounds/cmd/hit",
            "local_sounds/cmd/intro_",
            "local_sounds/cmd/outro_",
        }
        missing = []
        for path in [TRINITTY, *sorted((ROOT / "tools").glob("*.py"))]:
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
