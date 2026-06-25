import builtins
import importlib.util
import contextlib
import io
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from queue import Queue
from types import SimpleNamespace

import trinitty


ROOT = Path(__file__).resolve().parents[1]


def temp_path(name):
    return str(Path(tempfile.gettempdir()) / name)


def reset_command_state():
    trinitty.DEBUG = False
    trinitty.CMD_DBG = False
    trinitty.INTERPRETOR = True
    trinitty.PUSH_TO_TALK = False
    trinitty.PLAYBACK_INTERRUPT_ENABLED = False
    trinitty.PLAYBACK_INTERRUPT_TIMEOUT = 30.0
    trinitty.COMMAND_CLASSIFIER_ENABLED = False
    trinitty.COMMAND_CLASSIFIER_THRESHOLD = 0.65
    trinitty.COMMAND_CLASSIFIER_MODEL_PATH = "datas/command_classifier.keras"
    trinitty.COMMAND_CLASSIFIER_MODEL = None
    trinitty.GOOGLE_STT_TIMEOUT = 20.0
    trinitty.GOOGLE_LANGUAGE_TIMEOUT = 8.0
    trinitty.HISTORY_CLASSIFICATION_ENABLED = True
    trinitty.GPT4FREE_COOKIES_AUTO_SYNC = True
    trinitty.GPT4FREE_COOKIES_SYNC_DIR = "tools/har_and_cookies"
    trinitty.GPT4FREE_COOKIES_LOADED = False
    trinitty.GPT4FREE_RUNTIME_AVAILABLE = None
    trinitty.SCRIPT_PATH = str(ROOT)
    trinitty.LAST_DIALOG = []
    trinitty.unidecode = lambda value: value

    trinitty.Loaded_Actions_Words_Requests = []
    trinitty.Loaded_Alternatives_Triggers = []
    trinitty.Loaded_Add_Triggers_Requests = []
    trinitty.Loaded_Trinitty_Name_Requests = []
    trinitty.Loaded_Trinitty_Mean_Requests = []
    trinitty.Loaded_Trinitty_Dev_Requests = []
    trinitty.Loaded_Trinitty_Script_Requests = []
    trinitty.Loaded_Trinitty_Help_Requests = []
    trinitty.Loaded_Prompt_Requests = []
    trinitty.Loaded_Rnd_Requests = []
    trinitty.Loaded_Repeat_Requests = []
    trinitty.Loaded_Show_History_Requests = []
    trinitty.Loaded_Search_History_Requests = []
    trinitty.Loaded_Delete_Last_History_Requests = []
    trinitty.Loaded_Search_Web_Requests = []
    trinitty.Loaded_Read_Link_Requests = []
    trinitty.Loaded_Play_Audio_File_Requests = []
    trinitty.Loaded_Wait_Words_Requests = []
    trinitty.Loaded_Quit_Words_Requests = []
    trinitty.Loaded_Sort_Results_Requests = []
    trinitty.Loaded_Read_Results = []


def reset_runtime_queues():
    trinitty.record_on = Queue()
    trinitty.chunks = Queue()
    trinitty.last_sentence = Queue()
    trinitty.No_Input = Queue()
    trinitty.score_sentiment = Queue()
    trinitty.audio_datas = Queue()
    trinitty.wake_me_up = Queue()
    trinitty.cancel_operation = Queue()
    trinitty.awake = Queue()


class TrinittyRuntimeTests(unittest.TestCase):
    def test_import_is_safe(self):
        self.assertTrue(hasattr(trinitty, "Commandes"))

    def test_default_script_path_uses_installed_asset_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packaged = root / "trinitty"
            (packaged / "datas").mkdir(parents=True)
            (packaged / "datas" / "conf.trinity").write_text("SAVED_ANSWER = default\n")
            original_prefix = trinitty.sys.prefix
            original_file = trinitty.__file__
            try:
                trinitty.sys.prefix = str(root)
                trinitty.__file__ = str(root / "site-packages" / "trinitty.py")
                self.assertEqual(str(packaged), trinitty.Default_Script_Path())
            finally:
                trinitty.sys.prefix = original_prefix
                trinitty.__file__ = original_file

    def test_default_script_path_uses_userbase_asset_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            userbase = root / "userbase"
            packaged = userbase / "trinitty"
            (packaged / "datas").mkdir(parents=True)
            (packaged / "datas" / "conf.trinity").write_text("SAVED_ANSWER = default\n")
            original_prefix = trinitty.sys.prefix
            original_file = trinitty.__file__
            original_userbase = trinitty.site.getuserbase
            try:
                trinitty.sys.prefix = str(root / "system-prefix")
                trinitty.__file__ = str(root / "site-packages" / "trinitty.py")
                trinitty.site.getuserbase = lambda: str(userbase)
                self.assertEqual(str(packaged), trinitty.Default_Script_Path())
            finally:
                trinitty.sys.prefix = original_prefix
                trinitty.__file__ = original_file
                trinitty.site.getuserbase = original_userbase

    def test_initialize_user_data_creates_common_files_without_overwriting(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = str(home)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    user_root = Path(trinitty.Initialize_User_Data())

                self.assertEqual(home / ".local" / "share" / "Trinitty", user_root)
                self.assertTrue((user_root / "datas" / "conf.trinity").exists())
                self.assertFalse((user_root / "datas" / "conf.local.trinity").exists())
                self.assertTrue((user_root / "keys" / "openai.key").exists())
                self.assertTrue((user_root / "keys" / "README.txt").exists())
                user_installer = user_root / "install_dependencies.sh"
                self.assertTrue(user_installer.exists())
                self.assertTrue(os.access(user_installer, os.X_OK))
                self.assertIn("install_user_launcher()", user_installer.read_text())
                user_requirements = user_root / "requirements.txt"
                self.assertTrue(user_requirements.exists())
                self.assertIn("google-cloud-speech", user_requirements.read_text())
                self.assertTrue((user_root / "history").is_dir())
                self.assertTrue((user_root / "saved_answer" / "saved_error").is_dir())
                user_conf = user_root / "datas" / "conf.trinity"
                user_conf_text = user_conf.read_text()
                self.assertIn("OPENAI_API_KEY_FILE = keys/openai.key", user_conf_text)
                packaged_keys = set(trinitty.Config_Keys_From_Text((ROOT / "datas" / "conf.trinity").read_text()))
                user_keys = set(trinitty.Config_Keys_From_Text(user_conf_text))
                self.assertLessEqual(packaged_keys, user_keys)
                self.assertIn(
                    "Configuration fournie avec le package:",
                    user_conf_text,
                )
                self.assertIn(trinitty.Packaged_Config_File(), user_conf_text)
                self.assertIn("Dossier utilisateur: %s" % user_root, output.getvalue())
                self.assertIn("Configuration package: %s" % trinitty.Packaged_Config_File(), output.getvalue())
                self.assertIn(
                    "Configuration modifiable: %s" % user_conf,
                    output.getvalue(),
                )

                openai_key = user_root / "keys" / "openai.key"
                openai_key.write_text("sk-existing\n")
                user_conf.write_text("OPENAI_MODEL = custom-user-model\n")
                user_installer.write_text("# custom installer\n")
                user_requirements.write_text("# custom requirements\n")
                with contextlib.redirect_stdout(io.StringIO()):
                    trinitty.Initialize_User_Data()
                self.assertEqual("sk-existing\n", openai_key.read_text())
                self.assertEqual("# custom installer\n", user_installer.read_text())
                self.assertEqual("# custom requirements\n", user_requirements.read_text())
                updated_conf = user_conf.read_text()
                self.assertTrue(updated_conf.startswith("OPENAI_MODEL = custom-user-model\n"))
                self.assertIn("SPACY_MODEL = fr_core_news_md", updated_conf)
                self.assertIn("XCB_ERROR_FIX = True", updated_conf)
            finally:
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

    def test_install_user_launcher_writes_clean_environment_wrapper(self):
        with tempfile.TemporaryDirectory() as tmp:
            launcher_path = Path(tmp) / "bin" / "trinitty"
            python_bin = Path(tmp) / "test venv" / "bin" / "python"
            installed = Path(
                trinitty.Install_User_Launcher(
                    launcher_path=str(launcher_path),
                    python_bin=str(python_bin),
                )
            )

            self.assertEqual(launcher_path, installed)
            self.assertTrue(os.access(launcher_path, os.X_OK))
            content = launcher_path.read_text()
            self.assertIn("export PYTHONNOUSERSITE=1", content)
            self.assertIn("unset PYTHONPATH", content)
            self.assertIn("'%s' -m trinitty" % python_bin, content)

    def test_migrate_user_config_disables_generated_playback_interrupt_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            user_conf = Path(tmp) / "conf.trinity"
            user_conf.write_text(
                "\n".join(
                    [
                        "DEBUG = True",
                        "PLAYBACK_INTERRUPT_ENABLED = True #True or False - listen for stop command while speaking",
                        "OPENAI_TIMEOUT = 30",
                    ]
                )
                + "\n"
            )

            self.assertTrue(trinitty.Migrate_User_Config_Defaults(str(user_conf)))
            migrated = user_conf.read_text()

        self.assertIn("PLAYBACK_INTERRUPT_ENABLED = False", migrated)
        self.assertIn("DEBUG = True", migrated)
        self.assertIn("OPENAI_TIMEOUT = 30", migrated)

    def test_migrate_user_config_keeps_custom_playback_interrupt_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            user_conf = Path(tmp) / "conf.trinity"
            user_conf.write_text("PLAYBACK_INTERRUPT_ENABLED = True # custom local choice\n")

            self.assertFalse(trinitty.Migrate_User_Config_Defaults(str(user_conf)))
            self.assertEqual("PLAYBACK_INTERRUPT_ENABLED = True # custom local choice\n", user_conf.read_text())

    def test_initialize_user_data_migrates_legacy_user_local_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            datas = home / ".local" / "share" / "Trinitty" / "datas"
            datas.mkdir(parents=True)
            legacy_conf = datas / "conf.local.trinity"
            legacy_conf.write_text("OPENAI_MODEL = old-user-model\n")
            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = str(home)
                with contextlib.redirect_stdout(io.StringIO()):
                    user_root = Path(trinitty.Initialize_User_Data())
            finally:
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

            migrated_conf = (user_root / "datas" / "conf.trinity").read_text()
            self.assertTrue(migrated_conf.startswith("OPENAI_MODEL = old-user-model\n"))
            self.assertIn("SPACY_MODEL = fr_core_news_md", migrated_conf)
            self.assertIn("XCB_ERROR_FIX = True", migrated_conf)
            self.assertEqual("OPENAI_MODEL = old-user-model\n", legacy_conf.read_text())

    def test_dependency_help_uses_absolute_installer_path_when_available(self):
        help_text = trinitty.Dependency_Install_Help("google-cloud-speech")

        self.assertIn(str(ROOT / "install_dependencies.sh"), help_text)
        self.assertIn("--system --venv", help_text)

    def test_dependency_help_prefers_user_installer_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            installer = home / ".local" / "share" / "Trinitty" / "install_dependencies.sh"
            installer.parent.mkdir(parents=True)
            installer.write_text("#!/usr/bin/env bash\n")
            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = str(home)
                help_text = trinitty.Dependency_Install_Help("google-cloud-speech")
            finally:
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

            self.assertIn(str(installer), help_text)
            self.assertIn("--no-venv", help_text)
            self.assertNotIn("--venv", help_text.replace("--no-venv", ""))

    def test_auto_dependency_installer_runs_once_per_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installer = root / "install_dependencies.sh"
            requirements = root / "requirements.txt"
            installer.write_text("#!/usr/bin/env bash\n")
            installer.chmod(0o700)
            requirements.write_text("")
            calls = []
            original_run = trinitty.subprocess.run
            original_version = trinitty.Current_Trinitty_Version_For_Installer
            original_enabled = trinitty.Auto_Dependency_Installer_Enabled

            def fake_run(command, cwd=None, env=None, check=False):
                calls.append((command, cwd, env, check))
                return SimpleNamespace(returncode=0)

            try:
                trinitty.subprocess.run = fake_run
                trinitty.Current_Trinitty_Version_For_Installer = lambda: "9.9.9"
                trinitty.Auto_Dependency_Installer_Enabled = lambda: True
                self.assertTrue(trinitty.Auto_Run_Dependency_Installer(str(root)))
                self.assertFalse(trinitty.Auto_Run_Dependency_Installer(str(root)))
            finally:
                trinitty.subprocess.run = original_run
                trinitty.Current_Trinitty_Version_For_Installer = original_version
                trinitty.Auto_Dependency_Installer_Enabled = original_enabled

            self.assertEqual(1, len(calls))
            self.assertEqual(
                [str(installer), "--system", "--no-venv", "--no-dev-tools", "--no-launcher"],
                calls[0][0],
            )
            self.assertEqual(str(root), calls[0][1])
            self.assertEqual(trinitty.sys.executable, calls[0][2]["PYTHON"])
            self.assertEqual("9.9.9\n", (root / ".install_dependencies.version").read_text())

    def test_auto_dependency_installer_does_not_mark_failed_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            installer = root / "install_dependencies.sh"
            installer.write_text("#!/usr/bin/env bash\n")
            installer.chmod(0o700)
            (root / "requirements.txt").write_text("")
            original_run = trinitty.subprocess.run
            original_version = trinitty.Current_Trinitty_Version_For_Installer
            original_enabled = trinitty.Auto_Dependency_Installer_Enabled
            try:
                trinitty.subprocess.run = lambda *_args, **_kwargs: SimpleNamespace(returncode=42)
                trinitty.Current_Trinitty_Version_For_Installer = lambda: "9.9.9"
                trinitty.Auto_Dependency_Installer_Enabled = lambda: True
                self.assertFalse(trinitty.Auto_Run_Dependency_Installer(str(root)))
            finally:
                trinitty.subprocess.run = original_run
                trinitty.Current_Trinitty_Version_For_Installer = original_version
                trinitty.Auto_Dependency_Installer_Enabled = original_enabled

            self.assertFalse((root / ".install_dependencies.version").exists())

    def test_missing_dependency_message_uses_runtime_help_when_installer_is_absent(self):
        original_script_path = trinitty.Install_Dependencies_Script_Path
        trinitty.Install_Dependencies_Script_Path = lambda: ""
        try:
            with self.assertRaises(ModuleNotFoundError) as cm:
                trinitty.MissingDependency("google.cloud.speech_v1p1beta1", "google-cloud-speech")._raise()
        finally:
            trinitty.Install_Dependencies_Script_Path = original_script_path

        self.assertIn("Optional dependency 'google-cloud-speech' is unavailable", str(cm.exception))
        self.assertIn("trinitty --dependency-help", str(cm.exception))
        self.assertNotIn("./install_dependencies.sh", str(cm.exception))

    def test_user_data_path_keeps_legacy_lowercase_directory_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            legacy = home / ".local" / "share" / "trinitty"
            legacy.mkdir(parents=True)
            original_home = os.environ.get("HOME")
            try:
                os.environ["HOME"] = str(home)
                self.assertEqual(str(legacy / "keys" / "openai.key"), trinitty.User_Data_Path("keys", "openai.key"))
            finally:
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

    def test_runtime_writable_dirs_fall_back_to_user_data_when_script_path_is_not_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_script_path = root / "installed-file"
            fake_script_path.write_text("")
            home = root / "home"
            home.mkdir()
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            original_home = os.environ.get("HOME")
            try:
                trinitty.SCRIPT_PATH = str(fake_script_path)
                os.environ["HOME"] = str(home)

                self.assertEqual(
                    str(home / ".local" / "share" / "Trinitty" / "tmp" / "current_answer.wav"),
                    trinitty.Runtime_Tmp_Path("current_answer.wav"),
                )
                self.assertEqual(
                    str(home / ".local" / "share" / "Trinitty" / "history" / "nocat"),
                    trinitty.History_File_Path("nocat"),
                )
            finally:
                if original_script_path is missing:
                    if hasattr(trinitty, "SCRIPT_PATH"):
                        delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

    def test_nbr_to_tts_uses_module_constants_without_main_bootstrap(self):
        calls = []
        missing = object()
        original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
        original_run = trinitty.Run_Playback_Command
        try:
            trinitty.SCRIPT_PATH = str(ROOT)
            expected_number_wavs = [
                str(ROOT / "local_sounds" / "dates" / "milliers" / "deux_mille.wav"),
                str(ROOT / "local_sounds" / "dates" / "nombres" / "vingt-quatre.wav"),
            ]
            self.assertEqual(
                " ".join(expected_number_wavs),
                trinitty.NbrToTts(number=2024),
            )

            trinitty.Run_Playback_Command = lambda command: calls.append(command) or 0
            self.assertEqual(0, trinitty.NbrToTts(timestamp=1707350400.0))

            expected_date_wavs = [
                str(ROOT / "local_sounds" / "dates" / "jours" / "jeudi.wav"),
                str(ROOT / "local_sounds" / "dates" / "nombres" / "huit.wav"),
                str(ROOT / "local_sounds" / "dates" / "mois" / "février.wav"),
                str(ROOT / "local_sounds" / "dates" / "milliers" / "deux_mille.wav"),
                str(ROOT / "local_sounds" / "dates" / "nombres" / "vingt-quatre.wav"),
            ]
            for wav in [*expected_number_wavs, *expected_date_wavs]:
                self.assertTrue(Path(wav).exists(), wav)
            self.assertEqual(
                [
                    [
                        trinitty.APLAY_BIN,
                        "-q",
                        *expected_date_wavs,
                    ]
                ],
                calls,
            )
        finally:
            trinitty.Run_Playback_Command = original_run
            if original_script_path is missing:
                delattr(trinitty, "SCRIPT_PATH")
            else:
                trinitty.SCRIPT_PATH = original_script_path

    def test_tools_nbr_is_importable_without_playback_side_effect(self):
        calls = []
        original_run = subprocess.run
        subprocess.run = lambda *args, **kwargs: calls.append((args, kwargs))
        try:
            spec = importlib.util.spec_from_file_location("tool_nbr_test", ROOT / "tools" / "nbr.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        finally:
            subprocess.run = original_run

        self.assertEqual([], calls)
        expected_number_wavs = [
            str(ROOT / "local_sounds" / "dates" / "milliers" / "deux_mille.wav"),
            str(ROOT / "local_sounds" / "dates" / "nombres" / "vingt-quatre.wav"),
        ]
        self.assertEqual(" ".join(expected_number_wavs), module.NbrToTts(number=2024))

        try:
            module.subprocess.run = lambda command, check=False: calls.append((command, check)) or SimpleNamespace(returncode=0)
            self.assertEqual(0, module.NbrToTts(timestamp=1707350400.0))
        finally:
            module.subprocess.run = original_run
        self.assertTrue(all(Path(path).exists() for path in calls[0][0][2:]))

    def test_run_pico2wave_does_not_use_shell(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            out_wav = str(Path(tmp) / "missing" / "out.wav")
            original_run = trinitty.subprocess.run
            try:
                trinitty.subprocess.run = lambda *args, **kwargs: calls.append((args, kwargs))
                self.assertEqual(
                    out_wav,
                    trinitty.Run_Pico2Wave(out_wav, 'texte " ; touch bad'),
                )
            finally:
                trinitty.subprocess.run = original_run

            self.assertTrue((Path(tmp) / "missing").exists())
            expected_pico2wave = trinitty.which("pico2wave") or "pico2wave"
            self.assertEqual(
                [([expected_pico2wave, "-l", "fr-FR", "-w", out_wav, 'texte " ; touch bad'],)],
                [args for args, _kwargs in calls],
            )
            self.assertTrue(calls[0][1]["check"])
            self.assertEqual(trinitty.subprocess.DEVNULL, calls[0][1]["stdout"])
            self.assertEqual(trinitty.subprocess.DEVNULL, calls[0][1]["stderr"])

    def test_bad_stt_creates_tmp_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls = []

            class FakeClient:
                def synthesize_speech(self, **_kwargs):
                    return SimpleNamespace(audio_content=b"wav")

            fake_tts = SimpleNamespace(
                TextToSpeechClient=lambda: FakeClient(),
                AudioConfig=lambda audio_encoding=None: SimpleNamespace(audio_encoding=audio_encoding),
                AudioEncoding=SimpleNamespace(LINEAR16="LINEAR16"),
                SynthesisInput=lambda text=None: SimpleNamespace(text=text),
                VoiceSelectionParams=lambda language_code=None, name=None: SimpleNamespace(
                    language_code=language_code,
                    name=name,
                ),
            )
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            original_tts = trinitty.tts
            original_play = trinitty.Play_Audio_File
            try:
                trinitty.SCRIPT_PATH = str(root)
                trinitty.tts = fake_tts
                trinitty.Play_Audio_File = lambda path: calls.append(path) or 0
                trinitty.Bad_Stt("texte mal compris")
            finally:
                if original_script_path is missing:
                    if hasattr(trinitty, "SCRIPT_PATH"):
                        delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path
                trinitty.tts = original_tts
                trinitty.Play_Audio_File = original_play

            expected = root / "tmp" / "last_bad_stt.wav"
            self.assertTrue(expected.exists())
            self.assertEqual([str(expected)], calls)

    def test_bad_stt_tts_failures_are_nonfatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            original_tts = trinitty.tts
            original_pico2wave = trinitty.Run_Pico2Wave
            original_play = trinitty.Play_Audio_File
            try:
                trinitty.SCRIPT_PATH = str(root)
                trinitty.SAVED_ANSWER = str(root / "local_sounds" / "saved_answer")
                trinitty.Runtime_Errors = []
                trinitty.tts = SimpleNamespace(TextToSpeechClient=lambda: (_ for _ in ()).throw(RuntimeError("tts down")))
                trinitty.Run_Pico2Wave = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("pico down"))
                trinitty.Play_Audio_File = lambda *_args, **_kwargs: self.fail("audio should not play")

                self.assertIsNone(trinitty.Bad_Stt("texte mal compris"))
            finally:
                if original_script_path is missing:
                    delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path
                trinitty.tts = original_tts
                trinitty.Run_Pico2Wave = original_pico2wave
                trinitty.Play_Audio_File = original_play

            self.assertEqual("Bad_Stt:pico2wave", trinitty.Runtime_Errors[-1]["context"])

    def test_parse_response_without_bootstrap_translation_globals(self):
        missing = object()
        original_dlang = getattr(trinitty, "DLANG_KEY", missing)
        original_translate = getattr(trinitty, "GOOGLE_TRANSLATE", missing)
        if original_dlang is not missing:
            delattr(trinitty, "DLANG_KEY")
        if original_translate is not missing:
            delattr(trinitty, "GOOGLE_TRANSLATE")
        try:
            self.assertEqual("bonjour", trinitty.parse_response("bonjour"))
        finally:
            if original_dlang is not missing:
                trinitty.DLANG_KEY = original_dlang
            if original_translate is not missing:
                trinitty.GOOGLE_TRANSLATE = original_translate

    def test_parse_response_removes_greater_than_symbol_for_tts(self):
        reset_command_state()
        original_dlang = getattr(trinitty, "DLANG_KEY", False)
        original_translate = getattr(trinitty, "GOOGLE_TRANSLATE", False)
        trinitty.DLANG_KEY = False
        trinitty.GOOGLE_TRANSLATE = False
        try:
            self.assertEqual(
                "La valeur 10 doit etre ignoree",
                trinitty.parse_response("La valeur > 10 doit etre ignoree"),
            )
        finally:
            trinitty.DLANG_KEY = original_dlang
            trinitty.GOOGLE_TRANSLATE = original_translate

    def test_config_option_value_preserves_hash_inside_quotes(self):
        self.assertEqual(
            ("OPENAI_INSTRUCTIONS", "Garde le # comme texte"),
            trinitty.Config_Option_Value('OPENAI_INSTRUCTIONS = "Garde le # comme texte" # commentaire'),
        )
        self.assertEqual(
            ("OPENAI_TIMEOUT", "12"),
            trinitty.Config_Option_Value("OPENAI_TIMEOUT = 12 # commentaire"),
        )

    def test_parse_gpt4free_server_list_accepts_quoted_and_unquoted_names(self):
        self.assertIsNone(trinitty.Parse_Gpt4free_Server_List("None"))
        self.assertEqual(
            ["g4f.Provider.Qwen", "g4f.Provider.OpenaiChat"],
            trinitty.Parse_Gpt4free_Server_List(
                '["g4f.Provider.Qwen", g4f.Provider.OpenaiChat, g4f.Provider.Qwen] # comment'
            ),
        )

    def test_openai_key_file_skips_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_file = root / "keys" / "openai.key"
            key_file.parent.mkdir()
            key_file.write_text("\n# commentaire\n  # autre commentaire\nsk-test-key\n")
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            try:
                trinitty.SCRIPT_PATH = str(root)
                self.assertEqual("sk-test-key", trinitty.Openai_Read_Key_File("keys/openai.key"))
            finally:
                if original_script_path is missing:
                    delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path

    def test_openai_key_file_falls_back_to_user_data_for_relative_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_script_path = root / "installed-file"
            fake_script_path.write_text("")
            home = root / "home"
            key_file = home / ".local" / "share" / "Trinitty" / "keys" / "openai.key"
            key_file.parent.mkdir(parents=True)
            key_file.write_text("sk-user-data-key\n")
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            original_home = os.environ.get("HOME")
            try:
                trinitty.SCRIPT_PATH = str(fake_script_path)
                os.environ["HOME"] = str(home)
                self.assertEqual("sk-user-data-key", trinitty.Openai_Read_Key_File("keys/openai.key"))
            finally:
                if original_script_path is missing:
                    if hasattr(trinitty, "SCRIPT_PATH"):
                        delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

    def test_openai_config_path_works_before_bootstrap(self):
        missing = object()
        original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
        try:
            if original_script_path is not missing:
                delattr(trinitty, "SCRIPT_PATH")
            resolved = trinitty.Openai_Config_Path("keys/openai.key")
        finally:
            if original_script_path is not missing:
                trinitty.SCRIPT_PATH = original_script_path

        self.assertTrue(os.path.isabs(resolved))
        self.assertTrue(resolved.endswith(os.path.join("keys", "openai.key")))

    def test_google_credentials_env_is_set_only_when_local_file_exists(self):
        env_name = "GOOGLE_APPLICATION_CREDENTIALS"
        original_env = os.environ.get(env_name)
        original_default_script_path = trinitty.Default_Script_Path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            try:
                trinitty.Default_Script_Path = lambda: str(root)
                os.environ.pop(env_name, None)

                trinitty.Configure_Default_Google_Credentials()
                self.assertNotIn(env_name, os.environ)

                credentials = root / "keys" / "google_adc.json"
                credentials.parent.mkdir()
                credentials.write_text("{}")

                trinitty.Configure_Default_Google_Credentials()
                self.assertEqual(str(credentials), os.environ.get(env_name))

                user_credentials = root / "user-google.json"
                os.environ[env_name] = str(user_credentials)
                trinitty.Configure_Default_Google_Credentials()
                self.assertEqual(str(user_credentials), os.environ.get(env_name))
            finally:
                trinitty.Default_Script_Path = original_default_script_path
                if original_env is None:
                    os.environ.pop(env_name, None)
                else:
                    os.environ[env_name] = original_env

    def test_saved_answer_path_falls_back_when_configured_directory_fails(self):
        reset_command_state()
        original_home = os.environ.get("HOME")
        original_makedirs = trinitty.os.makedirs
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fallback_home = root / "home"
            bad_saved = root / "bad_saved"

            def fake_makedirs(path, exist_ok=False):
                if str(path).startswith(str(bad_saved)):
                    raise PermissionError("not writable")
                return original_makedirs(path, exist_ok=exist_ok)

            try:
                os.environ["HOME"] = str(fallback_home)
                trinitty.os.makedirs = fake_makedirs

                resolved = trinitty.Configure_Saved_Answer_Path(str(bad_saved))
            finally:
                trinitty.os.makedirs = original_makedirs
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

            expected = fallback_home / ".local" / "share" / "Trinitty" / "saved_answer"
            self.assertEqual(str(expected), resolved)
            self.assertEqual(str(expected), trinitty.SAVED_ANSWER)
            self.assertTrue((expected / "saved_error").exists())

    def test_resolve_gpt4free_provider_rejects_executable_config(self):
        original_g4f = trinitty.g4f
        original_runtime_available = getattr(trinitty, "GPT4FREE_RUNTIME_AVAILABLE", None)
        provider = SimpleNamespace(working=True)
        trinitty.g4f = SimpleNamespace(Provider=SimpleNamespace(Qwen=provider))
        trinitty.GPT4FREE_RUNTIME_AVAILABLE = True
        try:
            self.assertIs(provider, trinitty.Resolve_Gpt4free_Provider("g4f.Provider.Qwen"))
            self.assertTrue(trinitty.Gpt4free_Provider_Working("g4f.Provider.Qwen"))
            with self.assertRaises(ValueError):
                trinitty.Resolve_Gpt4free_Provider("__import__('os').system('id')")
            with self.assertRaises(ValueError):
                trinitty.Resolve_Gpt4free_Provider("g4f.Provider.__class__")
        finally:
            trinitty.g4f = original_g4f
            trinitty.GPT4FREE_RUNTIME_AVAILABLE = original_runtime_available

    def test_runtime_gpt4free_filter_removes_nonworking_without_prompt(self):
        original_status = getattr(trinitty, "GPT4FREE_SERVERS_STATUS", "Active")
        original_working = trinitty.Gpt4free_Provider_Working
        try:
            trinitty.GPT4FREE_SERVERS_STATUS = "Active"
            trinitty.Gpt4free_Provider_Working = lambda provider: provider.endswith(".Good")

            self.assertEqual(
                ["g4f.Provider.Good"],
                trinitty.Filter_Gpt4free_Providers_For_Runtime(
                    ["g4f.Provider.Bad", "g4f.Provider.Good"]
                ),
            )
        finally:
            trinitty.GPT4FREE_SERVERS_STATUS = original_status
            trinitty.Gpt4free_Provider_Working = original_working

    def test_result_text_extracts_readable_fields(self):
        result = {
            "google_title": "Titre",
            "google_description": "Description",
            "google_url": "https://example.invalid",
        }

        self.assertEqual("Titre\nDescription", trinitty.Result_Text(result))

    def test_result_display_text_includes_number_and_fields(self):
        result = {
            "google_title": "Titre",
            "google_description": "Description",
            "google_url": "https://example.invalid",
        }

        display = trinitty.Result_Display_Text(result, result_number=2)

        self.assertIn("Resultat 2", display)
        self.assertIn("Titre: Titre", display)
        self.assertIn("URL: https://example.invalid", display)

    def test_command_routes_trinitty_script(self):
        reset_command_state()
        trinitty.Loaded_Actions_Words_Requests = ["affiche"]
        trinitty.Loaded_Trinitty_Script_Requests = ["affiche*code source"]

        self.assertTrue(trinitty.Commandes("affiche ton code source"))

    def test_trinitty_script_profile_describes_script_and_todo(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "trinitty.py").write_text("def alpha():\n    pass\n\ndef beta():\n    pass\n")
            (root / "TODO").write_text(
                "# PARTIAL - finir une chose\n# TODO - corriger une autre chose\n"
            )
            trinitty.SCRIPT_PATH = str(root)

            profile = trinitty.Trinitty_Script_Profile()
            text = trinitty.Trinitty_Script_Text(profile)

        self.assertEqual(5, profile["line_count"])
        self.assertEqual(["alpha", "beta"], profile["functions"])
        self.assertIn("corriger une autre chose", profile["todo_open"])
        self.assertIn("Prioriser: corriger une autre chose", profile["suggestions"])
        self.assertIn("2 fonctions", text)

    def test_special_syntax_expands_nested_brackets(self):
        reset_command_state()

        self.assertEqual(
            ["a b", "a c", "d"],
            trinitty.Special_Syntax("[a [b/c]/d]", "test", 1),
        )
        self.assertEqual(
            ["x a b z", "x a c z", "x d z"],
            trinitty.Special_Syntax("x [a [b/c]/d] z", "test", 1),
        )

    def test_special_syntax_keeps_existing_non_nested_outputs(self):
        reset_command_state()

        self.assertEqual(["salut", "bonjour"], trinitty.Special_Syntax("[salut/bonjour]", "test", 1))
        self.assertEqual(
            ["rappelles-tu", "rappelle toi", "rappelle", "souviens-tu", "souviens toi", "souviens"],
            trinitty.Special_Syntax("[rappelle{s-tu/ toi/}/souviens{-tu/ toi/}]", "test", 1),
        )

    def test_seeknreturn_respects_trigger_word_order(self):
        reset_command_state()
        triggers = ["ouvre*historique"]

        self.assertEqual(["ouvre*historique"], trinitty.SeeknReturn("ouvre historique", triggers))
        self.assertEqual([], trinitty.SeeknReturn("historique ouvre", triggers))
        self.assertEqual(
            ["ouvre*historique"],
            trinitty.SeeknReturn("historique puis ouvre historique", triggers),
        )

    def test_command_routes_read_results(self):
        reset_command_state()
        calls = []
        trinitty.Loaded_Actions_Words_Requests = ["lis"]
        trinitty.Loaded_Read_Results = ["lis*resultats"]
        trinitty.LAST_DIALOG = [{"google_title": "Titre"}]
        original_read_results = trinitty.Read_Results
        trinitty.Read_Results = lambda result_object: calls.append(result_object) or "Titre"
        try:
            self.assertTrue(trinitty.Commandes("lis les resultats"))
        finally:
            trinitty.Read_Results = original_read_results

        self.assertEqual([[{"google_title": "Titre"}]], calls)

    def test_command_ignores_broad_read_results_trigger_in_prompt(self):
        reset_command_state()
        calls = []
        trinitty.Loaded_Actions_Words_Requests = ["dis"]
        trinitty.Loaded_Read_Results = ["dis * "]
        trinitty.LAST_DIALOG = ()
        original_read_results = trinitty.Read_Results
        trinitty.Read_Results = lambda result_object: calls.append(result_object) or "Titre"
        try:
            self.assertFalse(
                trinitty.Commandes(
                    "tu m'as dis a propos des trou noir est ce que tu comprends mon probleme"
                )
            )
        finally:
            trinitty.Read_Results = original_read_results

        self.assertEqual([], calls)

    def test_read_results_handles_empty_tuple(self):
        reset_command_state()
        self.assertEqual("", trinitty.Read_Results(()))

    def test_command_routes_polite_show_history_request(self):
        reset_command_state()
        calls = []
        trinitty.Loaded_Actions_Words_Requests = ["afficher"]
        trinitty.Loaded_Show_History_Requests = ["est ce que tu peux afficher l'historique"]
        original_show_history = trinitty.Show_History
        trinitty.Show_History = lambda: calls.append("show-history") or True
        try:
            self.assertTrue(trinitty.Commandes("est ce que tu peux afficher l'historique"))
        finally:
            trinitty.Show_History = original_show_history

        self.assertEqual(["show-history"], calls)

    def test_command_routes_polite_internet_search_request_without_csv_trigger(self):
        reset_command_state()
        calls = []
        original_google = trinitty.Google
        trinitty.Google = lambda text: calls.append(text) or "google"
        try:
            self.assertTrue(
                trinitty.Commandes("est-ce que tu peux faire une recherche sur Antoine Daniel sur Internet")
            )
        finally:
            trinitty.Google = original_google

        self.assertEqual(["est-ce que tu peux faire une recherche sur antoine daniel sur internet"], calls)

    def test_direct_web_search_detection_ignores_history_requests(self):
        reset_command_state()
        self.assertFalse(
            trinitty.Detect_Web_Search_Request("cherche dans l historique Antoine Daniel sur Internet")
        )

    def test_prompt_empty_input_reports_no_input_and_returns_to_sleep(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.SCRIPT_PATH = str(ROOT)
        calls = []
        original_input = builtins.input
        original_play = trinitty.Play_Audio_File
        original_sleep = trinitty.Go_Back_To_Sleep
        original_randint = trinitty.Non_Crypto_Randint
        builtins.input = lambda _prompt=None: ""
        trinitty.Play_Audio_File = lambda path: calls.append(("play", path)) or 0
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        trinitty.Non_Crypto_Randint = lambda _start, _end: 1
        try:
            self.assertEqual("sleep", trinitty.Prompt())
        finally:
            builtins.input = original_input
            trinitty.Play_Audio_File = original_play
            trinitty.Go_Back_To_Sleep = original_sleep
            trinitty.Non_Crypto_Randint = original_randint

        self.assertIn(("play", str(ROOT / "local_sounds" / "prompt" / "2.wav")), calls)
        self.assertIn(("play", str(ROOT / "local_sounds" / "noinput" / "1.wav")), calls)
        self.assertIn(("sleep", True), calls)
        self.assertFalse(trinitty.No_Input.empty())

    def test_load_csv_routes_common_spoken_show_history_requests(self):
        reset_command_state()
        original_paths = {
            "SCRIPT_PATH": getattr(trinitty, "SCRIPT_PATH", ""),
            "SAVED_ANSWER": getattr(trinitty, "SAVED_ANSWER", ""),
            "CMDFILE": getattr(trinitty, "CMDFILE", ""),
            "ALTFILE": getattr(trinitty, "ALTFILE", ""),
            "TRIFILE": getattr(trinitty, "TRIFILE", ""),
            "ACTFILE": getattr(trinitty, "ACTFILE", ""),
            "PREFILE": getattr(trinitty, "PREFILE", ""),
            "SYNFILE": getattr(trinitty, "SYNFILE", ""),
        }
        original_show_history = trinitty.Show_History
        calls = []

        with tempfile.TemporaryDirectory() as tmp:
            datas = ROOT / "datas"
            trinitty.SCRIPT_PATH = str(ROOT)
            trinitty.SAVED_ANSWER = str(Path(tmp) / "saved_answer")
            trinitty.CMDFILE = str(datas / "cmd.trinity")
            trinitty.ALTFILE = str(datas / "alt_cmd.trinity")
            trinitty.TRIFILE = str(datas / "alt_trigger.trinity")
            trinitty.ACTFILE = str(datas / "action.trinity")
            trinitty.PREFILE = str(datas / "prefix.trinity")
            trinitty.SYNFILE = str(datas / "synonym.trinity")
            trinitty.Show_History = lambda: calls.append("show-history") or True

            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertTrue(trinitty.Load_Csv())
                    self.assertTrue(trinitty.Commandes("est-ce que tu peux afficher l'historique"))
                    self.assertTrue(trinitty.Commandes("tu peux afficher l historique"))
                    self.assertTrue(trinitty.Commandes("montre moi l historique"))
            finally:
                trinitty.Show_History = original_show_history
                for name, value in original_paths.items():
                    setattr(trinitty, name, value)

        self.assertEqual(["show-history", "show-history", "show-history"], calls)

    def test_command_classifier_training_samples_collects_commands_and_negatives(self):
        reset_command_state()
        trinitty.Loaded_Actions_Words_Requests = ["affiche"]
        trinitty.Loaded_Show_History_Requests = ["affiche*historique"]

        samples = trinitty.Command_Classifier_Training_Samples()

        self.assertIn(("affiche", 1), samples)
        self.assertIn(("affiche historique", 1), samples)
        self.assertIn(("bonjour", 0), samples)

    def test_train_command_classifier_uses_tensorflow_when_available(self):
        reset_command_state()
        calls = []

        class FakeVectorizer:
            def __init__(self, **kwargs):
                calls.append(("vectorizer", kwargs))

            def adapt(self, texts):
                calls.append(("adapt", list(texts)))

        class FakeModel:
            def __init__(self, layers):
                calls.append(("model", len(layers)))

            def compile(self, **kwargs):
                calls.append(("compile", kwargs["optimizer"], kwargs["loss"]))

            def fit(self, texts, labels, epochs=1, verbose=0):
                calls.append(("fit", list(texts), list(labels), epochs, verbose))

            def save(self, path):
                calls.append(("save", path))

        fake_layers = SimpleNamespace(
            TextVectorization=FakeVectorizer,
            Embedding=lambda *_args, **_kwargs: "embedding",
            GlobalAveragePooling1D=lambda: "pool",
            Dense=lambda *_args, **_kwargs: "dense",
        )
        fake_tensorflow = SimpleNamespace(
            keras=SimpleNamespace(layers=fake_layers, Sequential=lambda layers: FakeModel(layers))
        )
        original_tensorflow = trinitty.tensorflow
        model_path = temp_path("command.keras")
        try:
            trinitty.tensorflow = fake_tensorflow
            model = trinitty.Train_Command_Classifier(
                command_texts=["affiche historique"],
                negative_texts=["bonjour"],
                model_path=model_path,
                epochs=2,
            )
        finally:
            trinitty.tensorflow = original_tensorflow

        self.assertIs(model, trinitty.COMMAND_CLASSIFIER_MODEL)
        self.assertIn(("adapt", ["affiche historique", "bonjour"]), calls)
        self.assertIn(("fit", ["affiche historique", "bonjour"], [1, 0], 2, 0), calls)
        self.assertIn(("save", model_path), calls)

    def test_command_classifier_allows_command_uses_model_threshold(self):
        reset_command_state()

        class FakeModel:
            def __init__(self, score):
                self.score = score

            def predict(self, texts, verbose=0):
                self.texts = texts
                self.verbose = verbose
                return [[self.score]]

        trinitty.COMMAND_CLASSIFIER_ENABLED = True
        trinitty.COMMAND_CLASSIFIER_THRESHOLD = 0.65
        trinitty.COMMAND_CLASSIFIER_MODEL = FakeModel(0.8)
        self.assertTrue(trinitty.Command_Classifier_Allows_Command("affiche historique"))

        trinitty.COMMAND_CLASSIFIER_MODEL = FakeModel(0.2)
        self.assertFalse(trinitty.Command_Classifier_Allows_Command("bonjour"))

    def test_commandes_rejects_before_ambiguity_when_classifier_says_no(self):
        reset_command_state()
        calls = []
        original_classifier = trinitty.Command_Classifier_Allows_Command
        original_check = trinitty.Check_Ambiguity
        trinitty.Command_Classifier_Allows_Command = lambda text: calls.append(("classifier", text)) or False
        trinitty.Check_Ambiguity = lambda *_args, **_kwargs: calls.append("ambiguity") or False
        try:
            self.assertFalse(trinitty.Commandes("affiche l'historique"))
        finally:
            trinitty.Command_Classifier_Allows_Command = original_classifier
            trinitty.Check_Ambiguity = original_check

        self.assertEqual([("classifier", "affiche l'historique")], calls)

    def test_command_routes_direct_url_without_destroying_punctuation(self):
        reset_command_state()
        calls = []
        original_read_link = trinitty.ReadLink
        trinitty.ReadLink = lambda **kwargs: calls.append(kwargs) or "read-link"
        try:
            self.assertTrue(trinitty.Commandes("lis https://example.invalid/page?q=1."))
        finally:
            trinitty.ReadLink = original_read_link

        self.assertEqual("https://example.invalid/page?q=1", calls[0]["urlinput"])

    def test_command_routes_quit(self):
        reset_command_state()
        calls = []
        trinitty.Loaded_Actions_Words_Requests = ["ferme"]
        trinitty.Loaded_Quit_Words_Requests = ["ferme*programme"]
        original_quit = trinitty.Quit
        trinitty.Quit = lambda from_function=None: calls.append(from_function)
        try:
            self.assertTrue(trinitty.Commandes("ferme ton programme"))
        finally:
            trinitty.Quit = original_quit

        self.assertEqual([None], calls)

    def test_results_hub_command_returns_function_name(self):
        reset_command_state()
        trinitty.Loaded_Actions_Words_Requests = ["lis"]
        trinitty.Loaded_Read_Results = ["lis*resultats"]

        self.assertEqual(
            "F_read_results",
            trinitty.Commandes(
                "lis les resultats",
                allowed_functions=["F_read_results"],
                from_function="Results_Hub",
            ),
        )

    def test_results_hub_allowed_functions_do_not_mutate_command_scope(self):
        reset_command_state()
        trinitty.Loaded_Actions_Words_Requests = ["ferme"]
        trinitty.Loaded_Quit_Words_Requests = ["ferme*programme"]
        allowed = ["F_read_results"]

        self.assertEqual(
            "F_quit",
            trinitty.Commandes(
                "ferme le programme",
                allowed_functions=allowed,
                from_function="Results_Hub",
            ),
        )
        self.assertEqual(["F_read_results"], allowed)

    def test_results_hub_handle_quit_command_exits(self):
        reset_command_state()
        calls = []
        original_quit = trinitty.Quit
        trinitty.Quit = lambda from_function=None: calls.append(from_function) or "quit"
        try:
            self.assertEqual("quit", trinitty.Results_Hub_Handle_Command("F_quit", []))
        finally:
            trinitty.Quit = original_quit

        self.assertEqual(["Results_Hub"], calls)

    def test_results_hub_handle_read_results_command_exits_to_sleep(self):
        reset_command_state()
        calls = []
        original_read_results = trinitty.Read_Results
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Read_Results = lambda results: calls.append(("read", results)) or "text"
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual(
                "sleep",
                trinitty.Results_Hub_Handle_Command("F_read_results", [{"hist_output": "reponse"}]),
            )
        finally:
            trinitty.Read_Results = original_read_results
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual(
            [("read", [{"hist_output": "reponse"}]), ("sleep", True)],
            calls,
        )

    def test_results_hub_selects_second_result_for_reading(self):
        reset_command_state()
        results = [{"hist_output": "un"}, {"hist_output": "deux"}]
        calls = []
        original_read_results = trinitty.Read_Results
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Read_Results = lambda selected: calls.append(("read", selected)) or "text"
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual(
                "sleep",
                trinitty.Results_Hub_Handle_Command(
                    "F_read_results",
                    results,
                    command_text="lis le numero deux",
                ),
            )
        finally:
            trinitty.Read_Results = original_read_results
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual([("read", [{"hist_output": "deux"}]), ("sleep", True)], calls)

    def test_results_hub_selection_uses_human_numbering(self):
        reset_command_state()
        results = [{"id": index} for index in range(1, 6)]
        cases = [
            ("selectionne le resultat numero 1", [1]),
            ("selectionne le resultat numero 2", [2]),
            ("selectionne le resultat numero 3", [3]),
            ("ouvre le resultat 3 et lis le", [3]),
            ("lis le numero trois", [3]),
            ("joue le fichier trois", [3]),
            ("audio trois", [3]),
            ("selectionne 3", [3]),
            ("et 1", [1]),
            ("les trois premiers", [1, 2, 3]),
            ("les cinq", [1, 2, 3, 4, 5]),
            ("les 5", [1, 2, 3, 4, 5]),
        ]

        for command_text, expected_ids in cases:
            with self.subTest(command_text=command_text):
                selected = trinitty.Results_Hub_Select_Results(
                    command_text,
                    results,
                    default_all=False,
                )
                self.assertEqual(expected_ids, [result["id"] for result in selected])

    def test_results_hub_does_not_select_result_from_wait_duration(self):
        reset_command_state()
        results = [{"id": index} for index in range(1, 6)]

        self.assertIsNone(trinitty.Results_Hub_Selection_Range("attends deux secondes", len(results)))
        self.assertEqual(
            [1],
            [
                result["id"]
                for result in trinitty.Results_Hub_Select_Results(
                    "attends deux secondes",
                    results,
                    default_all=False,
                )
            ],
        )
        self.assertEqual(
            [2],
            [
                result["id"]
                for result in trinitty.Results_Hub_Select_Results(
                    "lis le resultat deux",
                    results,
                    default_all=False,
                )
            ],
        )

    def test_results_hub_reads_third_result_when_user_says_number_three(self):
        reset_command_state()
        results = [
            {"hist_output": "un"},
            {"hist_output": "deux"},
            {"hist_output": "trois"},
        ]
        calls = []
        original_read_results = trinitty.Read_Results
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Read_Results = lambda selected: calls.append(("read", selected)) or "text"
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual(
                "sleep",
                trinitty.Results_Hub_Handle_Command(
                    "F_read_results",
                    results,
                    command_text="lis le resultat numero 3",
                ),
            )
        finally:
            trinitty.Read_Results = original_read_results
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual([("read", [{"hist_output": "trois"}]), ("sleep", True)], calls)

    def test_results_hub_opens_selected_google_link(self):
        reset_command_state()
        results = [
            {"google_title": "A", "google_url": "https://a.example"},
            {"google_title": "B", "google_url": "https://b.example"},
        ]
        calls = []
        original_read_link = trinitty.ReadLink
        trinitty.ReadLink = lambda **kwargs: calls.append(kwargs) or "read-link"
        try:
            self.assertEqual(
                "read-link",
                trinitty.Results_Hub_Handle_Command(
                    "F_read_link",
                    results,
                    command_text="ouvre le resultat deux",
                ),
            )
        finally:
            trinitty.ReadLink = original_read_link

        self.assertEqual("https://b.example", calls[0]["urlinput"])

    def test_results_hub_plays_selected_history_audio(self):
        reset_command_state()
        one_wav = temp_path("one.wav")
        two_wav = temp_path("two.wav")
        results = [
            {"hist_output_wav": one_wav},
            {"hist_output_wav": two_wav},
        ]
        calls = []
        original_play = trinitty.Play_Response
        trinitty.Play_Response = lambda *args, **kwargs: calls.append((args, kwargs)) or "played"
        try:
            self.assertEqual(
                "played",
                trinitty.Results_Hub_Handle_Command(
                    "F_play_audio",
                    results,
                    command_text="joue le fichier deux",
                ),
            )
        finally:
            trinitty.Play_Response = original_play

        self.assertEqual((two_wav,), calls[0][0])

    def test_results_hub_random_reads_one_random_result(self):
        reset_command_state()
        results = [{"hist_output": "un"}, {"hist_output": "deux"}]
        calls = []
        original_choice = trinitty.random.choice
        original_read_results = trinitty.Read_Results
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.random.choice = lambda sequence: sequence[1]
        trinitty.Read_Results = lambda selected: calls.append(("read", selected)) or "text"
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual("sleep", trinitty.Results_Hub_Handle_Command("F_rnd", results))
        finally:
            trinitty.random.choice = original_choice
            trinitty.Read_Results = original_read_results
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual([("read", [{"hist_output": "deux"}]), ("sleep", True)], calls)

    def test_play_response_uses_sox_play_for_mp3(self):
        reset_command_state()
        calls = []
        audio_mp3 = temp_path("audio.mp3")
        original_run = trinitty.Run_Playback_Command
        trinitty.Run_Playback_Command = lambda command: calls.append(command) or 0
        try:
            trinitty.Play_Response(audio_mp3, stay_awake=True, save_history=False)
        finally:
            trinitty.Run_Playback_Command = original_run

        self.assertEqual([[trinitty.PLAY_BIN, "-q", audio_mp3]], calls)

    def test_run_playback_command_rejects_raw_string_command(self):
        calls = []
        original_popen = trinitty.subprocess.Popen
        trinitty.subprocess.Popen = lambda *args, **kwargs: calls.append((args, kwargs))
        try:
            self.assertEqual(127, trinitty.Run_Playback_Command("play -q /tmp/audio.wav"))
        finally:
            trinitty.subprocess.Popen = original_popen

        self.assertEqual([], calls)

    def test_run_playback_command_stops_process_when_cancelled(self):
        reset_runtime_queues()
        calls = []

        class FakeProcess:
            def __init__(self):
                self.returncode = 0
                self.poll_count = 0

            def poll(self):
                self.poll_count += 1
                if self.poll_count == 1:
                    calls.append("poll")
                    trinitty.cancel_operation.put(True)
                    return None
                return self.returncode

            def terminate(self):
                calls.append("terminate")
                self.returncode = -15

            def wait(self, timeout=None):
                calls.append(("wait", timeout))
                return self.returncode

        original_popen = trinitty.subprocess.Popen
        original_sleep = trinitty.time.sleep
        audio_mp3 = temp_path("audio.mp3")
        trinitty.subprocess.Popen = lambda command, stdout=None, stderr=None: (
            stdout,
            stderr,
            calls.append(command),
            FakeProcess(),
        )[-1]
        trinitty.time.sleep = lambda _seconds: None
        try:
            self.assertEqual(130, trinitty.Run_Playback_Command(["play", "-q", audio_mp3]))
        finally:
            trinitty.subprocess.Popen = original_popen
            trinitty.time.sleep = original_sleep

        self.assertIn(["play", "-q", audio_mp3], calls)
        self.assertIn("terminate", calls)

    def test_playback_interrupt_listener_cancels_on_voice_stop_command(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.INTERPRETOR = False
        trinitty.PLAYBACK_INTERRUPT_ENABLED = True
        trinitty.Loaded_Actions_Words_Requests = ["arrete"]
        trinitty.Loaded_Wait_Words_Requests = ["arrete"]
        trinitty.audio_datas.put(b"audio")
        calls = []
        original_start = trinitty.Start_Thread_Record
        original_stop = trinitty.Stop_Recording
        original_stt = trinitty.Speech_To_Text
        trinitty.Start_Thread_Record = lambda: calls.append("start")
        trinitty.Stop_Recording = lambda: calls.append("stop")
        trinitty.Speech_To_Text = lambda _audio: ("arrete", 0.95, [], [], "")
        try:
            self.assertTrue(trinitty.Playback_Interrupt_Listener(trinitty.Event(), timeout=0.1))
        finally:
            trinitty.Start_Thread_Record = original_start
            trinitty.Stop_Recording = original_stop
            trinitty.Speech_To_Text = original_stt

        self.assertFalse(trinitty.cancel_operation.empty())
        self.assertEqual(["start", "stop"], calls)

    def test_playback_interrupt_listener_is_disabled_by_default(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.INTERPRETOR = False

        self.assertFalse(trinitty.Playback_Interrupt_Listener(trinitty.Event(), timeout=0.01))
        self.assertIsNone(trinitty.Start_Playback_Interrupt_Listener())

    def test_play_response_starts_interrupt_listener_around_playback(self):
        reset_command_state()
        calls = []
        audio_wav = temp_path("audio.wav")
        original_start = trinitty.Start_Playback_Interrupt_Listener
        original_stop = trinitty.Stop_Playback_Interrupt_Listener
        original_play = trinitty.Play_Audio_File
        trinitty.Start_Playback_Interrupt_Listener = lambda: calls.append("start") or "listener"
        trinitty.Stop_Playback_Interrupt_Listener = lambda listener: calls.append(("stop", listener))
        trinitty.Play_Audio_File = lambda filepath: calls.append(("play", filepath)) or 0
        try:
            trinitty.Play_Response(audio_wav, stay_awake=True, save_history=False)
        finally:
            trinitty.Start_Playback_Interrupt_Listener = original_start
            trinitty.Stop_Playback_Interrupt_Listener = original_stop
            trinitty.Play_Audio_File = original_play

        self.assertEqual(["start", ("play", audio_wav), ("stop", "listener")], calls)

    def test_playback_interrupt_listener_is_disabled_in_push_to_talk(self):
        reset_command_state()
        trinitty.INTERPRETOR = False
        trinitty.PUSH_TO_TALK = True
        self.assertFalse(trinitty.Playback_Interrupt_Listener(trinitty.Event(), timeout=0.01))
        self.assertIsNone(trinitty.Start_Playback_Interrupt_Listener())

    def test_results_hub_voice_quit_exits_loop(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.Loaded_Actions_Words_Requests = ["ferme"]
        trinitty.Loaded_Quit_Words_Requests = ["ferme*programme"]
        result = [{"hist_input_full": "question", "hist_output": "reponse"}]
        calls = []
        original_wait = trinitty.Wait
        original_wait_for = trinitty.Wait_for
        original_start = trinitty.Start_Thread_Record
        original_stt = trinitty.Speech_To_Text
        original_check = trinitty.Check_Transcript
        original_quit = trinitty.Quit
        original_play = trinitty.Play_Audio_File
        trinitty.Wait = lambda *_args, **_kwargs: None
        trinitty.Wait_for = lambda _action, timeout=None: (timeout is None) or (timeout is not None)
        trinitty.Start_Thread_Record = lambda: trinitty.audio_datas.put(b"audio")
        trinitty.Speech_To_Text = lambda _audio: (["ferme le programme"], [1.0], [], [], "")
        trinitty.Check_Transcript = lambda _transcripts, _confidence, _words, _words_confidence, _err: (
            "ferme le programme",
            True,
        )
        trinitty.Quit = lambda from_function=None: calls.append(from_function) or "quit"
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual("quit", trinitty.Results_Hub(result, from_function="Search_History"))
        finally:
            trinitty.Wait = original_wait
            trinitty.Wait_for = original_wait_for
            trinitty.Start_Thread_Record = original_start
            trinitty.Speech_To_Text = original_stt
            trinitty.Check_Transcript = original_check
            trinitty.Quit = original_quit
            trinitty.Play_Audio_File = original_play

        self.assertEqual(["Results_Hub"], calls)

    def test_results_hub_unknown_voice_command_exits_after_max_attempts(self):
        reset_command_state()
        reset_runtime_queues()
        result = [{"hist_input_full": "question", "hist_output": "reponse"}]
        calls = []
        original_wait = trinitty.Wait
        original_wait_for = trinitty.Wait_for
        original_start = trinitty.Start_Thread_Record
        original_stt = trinitty.Speech_To_Text
        original_check = trinitty.Check_Transcript
        original_sleep = trinitty.Go_Back_To_Sleep
        original_play = trinitty.Play_Audio_File
        original_attempts = trinitty.RESULTS_HUB_MAX_ATTEMPTS
        original_time_sleep = trinitty.time.sleep
        trinitty.RESULTS_HUB_MAX_ATTEMPTS = 2
        trinitty.time.sleep = lambda _seconds: None
        trinitty.Wait = lambda *_args, **_kwargs: None
        trinitty.Wait_for = lambda _action, timeout=None: (timeout is None) or (timeout is not None)
        trinitty.Start_Thread_Record = lambda: trinitty.audio_datas.put(b"audio")
        trinitty.Speech_To_Text = lambda _audio: (["commande inconnue"], [1.0], [], [], "")
        trinitty.Check_Transcript = lambda _transcripts, _confidence, _words, _words_confidence, _err: (
            "commande inconnue",
            True,
        )
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            started = time.monotonic()
            self.assertEqual("sleep", trinitty.Results_Hub(result, from_function="Search_History"))
            elapsed = time.monotonic() - started
        finally:
            trinitty.Wait = original_wait
            trinitty.Wait_for = original_wait_for
            trinitty.Start_Thread_Record = original_start
            trinitty.Speech_To_Text = original_stt
            trinitty.Check_Transcript = original_check
            trinitty.Go_Back_To_Sleep = original_sleep
            trinitty.Play_Audio_File = original_play
            trinitty.RESULTS_HUB_MAX_ATTEMPTS = original_attempts
            trinitty.time.sleep = original_time_sleep

        self.assertLess(elapsed, 1)
        self.assertEqual([("sleep", True)], calls)

    def test_search_history_matches_multiword_output(self):
        reset_command_state()
        trinitty.Loaded_History_List = [
            {
                "hist_file": "cat",
                "hist_cats": "cat",
                "hist_input_full": "question source",
                "hist_input_short": "question",
                "hist_input_wav": "",
                "hist_output": "une reponse avec deux mots",
                "hist_output_wav": "answer.wav",
                "hist_urls": "",
                "hist_epok": "1",
                "hist_tstamp": "2026-06-23 12:00:00",
            }
        ]
        calls = []
        original_isolate = trinitty.Isolate_Search
        original_results_hub = trinitty.Results_Hub
        trinitty.Isolate_Search = lambda _text, _function_name: "deux mots"
        trinitty.Results_Hub = lambda sorted_results, top_results, from_function=None: calls.append(
            (sorted_results, top_results, from_function)
        ) or "results"
        try:
            self.assertEqual("results", trinitty.Search_History("cherche deux mots"))
        finally:
            trinitty.Isolate_Search = original_isolate
            trinitty.Results_Hub = original_results_hub

        self.assertEqual("Search_History", calls[0][2])
        self.assertEqual(1, len(calls[0][0]))
        self.assertEqual("cat", calls[0][0][0]["hist_cats"])

    def test_clean_history_search_query_removes_command_noise(self):
        reset_command_state()
        self.assertEqual(
            "vitesse lumiere",
            trinitty.Clean_History_Search_Query("cherche dans l'historique la vitesse de la lumière"),
        )

    def test_search_history_cleans_query_and_matches_accents(self):
        reset_command_state()
        trinitty.Loaded_History_List = [
            {
                "hist_file": "science",
                "hist_cats": "science",
                "hist_input_full": "question source",
                "hist_input_short": "question",
                "hist_input_wav": "",
                "hist_output": "La vitesse de la lumière est proche de 299 792 458 m/s.",
                "hist_output_wav": "answer.wav",
                "hist_urls": "",
                "hist_epok": "1",
                "hist_tstamp": "2026-06-25 12:00:00",
            }
        ]
        calls = []
        original_isolate = trinitty.Isolate_Search
        original_results_hub = trinitty.Results_Hub
        trinitty.Isolate_Search = lambda _text, _function_name: "cherche dans l historique la vitesse de la lumiere"
        trinitty.Results_Hub = lambda sorted_results, top_results, from_function=None: calls.append(
            (sorted_results, top_results, from_function)
        ) or "results"
        try:
            self.assertEqual("results", trinitty.Search_History("cherche la vitesse"))
        finally:
            trinitty.Isolate_Search = original_isolate
            trinitty.Results_Hub = original_results_hub

        self.assertEqual("Search_History", calls[0][2])
        self.assertEqual(1, len(calls[0][0]))
        self.assertEqual("science", calls[0][0][0]["hist_cats"])

    def test_delete_last_history_entry_removes_latest_row(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "history"
            history.mkdir()
            trinitty.SCRIPT_PATH = str(root)
            rows = [
                {
                    "hist_file": "cat",
                    "hist_cats": "cat",
                    "hist_input_full": "ancienne question",
                    "hist_input_short": "ancienne",
                    "hist_input_wav": "",
                    "hist_output": "ancienne reponse",
                    "hist_output_wav": "old.wav",
                    "hist_urls": "",
                    "hist_epok": "1.0",
                    "hist_tstamp": "2026-06-23 12:00:00",
                },
                {
                    "hist_file": "cat",
                    "hist_cats": "cat",
                    "hist_input_full": "derniere question",
                    "hist_input_short": "derniere",
                    "hist_input_wav": "",
                    "hist_output": "derniere reponse",
                    "hist_output_wav": "new.wav",
                    "hist_urls": "",
                    "hist_epok": "2.0",
                    "hist_tstamp": "2026-06-23 12:01:00",
                },
            ]
            trinitty.Loaded_History_List = list(rows)
            trinitty.Write_History_File(str(history / "cat"), rows)

            self.assertTrue(trinitty.Delete_Last_History_Entry())

            self.assertEqual(["1.0"], [row["hist_epok"] for row in trinitty.Loaded_History_List])
            with open(history / "cat", newline="") as csvfile:
                saved_rows = list(trinitty.csv.DictReader(csvfile))
            self.assertEqual(["1.0"], [row["hist_epok"] for row in saved_rows])

    def test_check_history_replays_matching_wav_without_debug_exit(self):
        reset_command_state()
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(root / "saved")
            trinitty.Current_Category = ["cat"]
            trinitty.Loaded_History_List = [
                {
                    "hist_file": "cat",
                    "hist_cats": "cat",
                    "hist_input_full": "question",
                    "hist_input_short": "question",
                    "hist_output": "reponse differente",
                    "hist_output_wav": "known.wav",
                }
            ]
            calls = []
            originals = (
                trinitty.preprocess,
                trinitty.similar,
                trinitty.Play_Audio_File,
                trinitty.Start_Thread_Record,
                trinitty.Wait_for,
            )
            trinitty.preprocess = lambda value: value
            trinitty.similar = lambda left, right: 1.0 if (left, right) == ("question", "question") else 0.0
            trinitty.Play_Audio_File = lambda path: calls.append(path) or 0
            trinitty.Start_Thread_Record = lambda: calls.append("record")
            trinitty.Wait_for = lambda _what, **_kwargs: False
            try:
                self.assertFalse(trinitty.Check_History("question"))
            finally:
                (
                    trinitty.preprocess,
                    trinitty.similar,
                    trinitty.Play_Audio_File,
                    trinitty.Start_Thread_Record,
                    trinitty.Wait_for,
                ) = originals

            self.assertIn("known.wav", calls)

    def test_check_history_falls_back_to_nocat_when_classify_leaves_category_empty(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.Current_Category = []
        trinitty.Loaded_History_List = []
        originals = (trinitty.Classify, trinitty.preprocess)
        trinitty.Classify = lambda _text: None
        trinitty.preprocess = lambda value: value
        try:
            self.assertFalse(trinitty.Check_History("question"))
        finally:
            trinitty.Classify, trinitty.preprocess = originals

        self.assertEqual(["nocat"], trinitty.Current_Category)

    def test_classify_passes_google_language_timeout(self):
        reset_command_state()
        original_language_v1 = trinitty.language_v1
        original_timeout = trinitty.GOOGLE_LANGUAGE_TIMEOUT
        calls = []

        class FakeLanguageClient:
            def classify_text(self, request, timeout=None):
                calls.append((request, timeout))
                return SimpleNamespace(categories=[SimpleNamespace(name="/Science/Physics")])

        trinitty.language_v1 = SimpleNamespace(
            LanguageServiceClient=FakeLanguageClient,
            Document=SimpleNamespace(Type=SimpleNamespace(PLAIN_TEXT="plain_text")),
            ClassificationModelOptions=SimpleNamespace(
                V2Model=SimpleNamespace(ContentCategoriesVersion=SimpleNamespace(V2="v2"))
            ),
        )
        trinitty.GOOGLE_LANGUAGE_TIMEOUT = 2.5
        try:
            self.assertEqual((), trinitty.Classify("vitesse de la lumiere"))
        finally:
            trinitty.language_v1 = original_language_v1
            trinitty.GOOGLE_LANGUAGE_TIMEOUT = original_timeout

        self.assertEqual(2.5, calls[0][1])
        self.assertEqual(["-Science-Physics"], trinitty.Current_Category)

    def test_classify_falls_back_to_nocat_when_google_language_fails(self):
        reset_command_state()
        original_language_v1 = trinitty.language_v1
        trinitty.Runtime_Errors = []

        class FakeLanguageClient:
            def classify_text(self, request, timeout=None):
                raise TimeoutError("language timeout")

        trinitty.language_v1 = SimpleNamespace(
            LanguageServiceClient=FakeLanguageClient,
            Document=SimpleNamespace(Type=SimpleNamespace(PLAIN_TEXT="plain_text")),
            ClassificationModelOptions=SimpleNamespace(
                V2Model=SimpleNamespace(ContentCategoriesVersion=SimpleNamespace(V2="v2"))
            ),
        )
        try:
            self.assertEqual((), trinitty.Classify("question"))
        finally:
            trinitty.language_v1 = original_language_v1

        self.assertEqual(["nocat"], trinitty.Current_Category)
        self.assertEqual("Classify", trinitty.Runtime_Errors[-1]["context"])

    def test_save_history_uses_no_audio_placeholder_when_current_wav_is_missing(self):
        reset_command_state()
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "history").mkdir()
            (root / "tmp").mkdir()
            saved = root / "saved"
            saved.mkdir()
            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(saved) + "/"
            trinitty.Current_Category = ["cat"]
            trinitty.Loaded_History_List = []
            trinitty.last_sentence.put("question")

            trinitty.Save_History("reponse")

            expected_wav = str(root / "local_sounds" / "errors" / "err_no_audio_saved.wav")
            self.assertEqual(expected_wav, trinitty.Loaded_History_List[-1]["hist_output_wav"])

    def test_save_history_falls_back_to_nocat_when_classify_leaves_category_empty(self):
        reset_command_state()
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "history"
            history.mkdir()
            trinitty.SCRIPT_PATH = str(root)
            trinitty.Current_Category = []
            trinitty.Loaded_History_List = []
            trinitty.last_sentence.put("question")
            original_classify = trinitty.Classify
            trinitty.Classify = lambda _text: None
            try:
                trinitty.Save_History("reponse", no_audio=True)
            finally:
                trinitty.Classify = original_classify

            self.assertTrue((history / "nocat").exists())
            self.assertEqual("nocat", trinitty.Loaded_History_List[-1]["hist_file"])

    def test_save_history_sanitizes_category_filename(self):
        reset_command_state()
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "history"
            history.mkdir()
            trinitty.SCRIPT_PATH = str(root)
            trinitty.Current_Category = ["../outside/category"]
            trinitty.Loaded_History_List = []
            trinitty.last_sentence.put("question")

            trinitty.Save_History("reponse", no_audio=True)

            self.assertTrue((history / "outside.category").exists())
            self.assertFalse((root / "outside").exists())
            self.assertEqual("outside.category", trinitty.Loaded_History_List[-1]["hist_file"])

    def test_save_history_creates_history_directory(self):
        reset_command_state()
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trinitty.SCRIPT_PATH = str(root)
            trinitty.Current_Category = ["cat"]
            trinitty.Loaded_History_List = []
            trinitty.last_sentence.put("question")

            trinitty.Save_History("reponse", no_audio=True)

            self.assertTrue((root / "history" / "cat").exists())
            self.assertEqual("cat", trinitty.Loaded_History_List[-1]["hist_file"])

    def test_save_history_accepts_saved_answer_without_trailing_slash(self):
        reset_command_state()
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "history").mkdir()
            tmp_dir = root / "tmp"
            tmp_dir.mkdir()
            saved = root / "saved"
            saved.mkdir()
            (tmp_dir / "current_answer.wav").write_bytes(b"wav")
            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(saved)
            trinitty.Current_Category = ["cat"]
            trinitty.Loaded_History_List = []
            trinitty.last_sentence.put("question")

            trinitty.Save_History("reponse")

            output_wav = Path(trinitty.Loaded_History_List[-1]["hist_output_wav"])
            self.assertEqual(saved, output_wav.parent)
            self.assertTrue(output_wav.exists())

    def test_save_history_copies_audio_without_preserving_metadata(self):
        reset_command_state()
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "history").mkdir()
            tmp_dir = root / "tmp"
            tmp_dir.mkdir()
            saved = root / "saved"
            saved.mkdir()
            current_wav = tmp_dir / "current_answer.wav"
            current_wav.write_bytes(b"wav")
            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(saved)
            trinitty.Current_Category = ["cat"]
            trinitty.Loaded_History_List = []
            trinitty.last_sentence.put("question")
            original_copy2 = trinitty.copy2
            trinitty.copy2 = lambda *_args, **_kwargs: (_ for _ in ()).throw(
                PermissionError("copystat not supported")
            )
            try:
                trinitty.Save_History("reponse")
            finally:
                trinitty.copy2 = original_copy2

            output_wav = Path(trinitty.Loaded_History_List[-1]["hist_output_wav"])
            self.assertEqual(b"wav", output_wav.read_bytes())

    def test_text_to_speech_cleans_temporary_answer_wavs(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tmp_dir = root / "tmp"
            saved = root / "saved"
            (saved / "saved_error").mkdir(parents=True)
            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(saved)
            calls = []

            class FakeClient:
                def synthesize_speech(self, **_kwargs):
                    return SimpleNamespace(audio_content=b"wav")

            class FakeTransformer:
                def set_output_format(self, rate=None):
                    calls.append(("rate", rate))

                def build(self, source, dest):
                    Path(dest).write_bytes(Path(source).read_bytes())

            fake_tts = SimpleNamespace(
                TextToSpeechClient=lambda: FakeClient(),
                AudioConfig=lambda audio_encoding=None: SimpleNamespace(audio_encoding=audio_encoding),
                AudioEncoding=SimpleNamespace(LINEAR16="LINEAR16"),
                SynthesisInput=lambda text=None: SimpleNamespace(text=text),
                VoiceSelectionParams=lambda language_code=None, name=None: SimpleNamespace(
                    language_code=language_code,
                    name=name,
                ),
            )
            fake_sox = SimpleNamespace(
                file_info=SimpleNamespace(sample_rate=lambda _path: 24000),
                Transformer=lambda: FakeTransformer(),
            )

            originals = (
                trinitty.tts,
                trinitty.sox,
                trinitty.time.sleep,
                trinitty.Play_Response,
                getattr(trinitty, "DLANG_KEY", None),
                getattr(trinitty, "GOOGLE_TRANSLATE", None),
            )
            trinitty.tts = fake_tts
            trinitty.sox = fake_sox
            trinitty.time.sleep = lambda _seconds: None
            trinitty.Play_Response = lambda **kwargs: calls.append(("play_response", kwargs)) or "played"
            trinitty.DLANG_KEY = False
            trinitty.GOOGLE_TRANSLATE = False
            try:
                self.assertEqual("played", trinitty.Text_To_Speech("bonjour", savehistory=False))
            finally:
                (
                    trinitty.tts,
                    trinitty.sox,
                    trinitty.time.sleep,
                    trinitty.Play_Response,
                    trinitty.DLANG_KEY,
                    trinitty.GOOGLE_TRANSLATE,
                ) = originals

            self.assertTrue(tmp_dir.exists())
            self.assertFalse((tmp_dir / "answer0000.wav").exists())
            self.assertTrue((tmp_dir / "current_answer.wav").exists())

    def test_google_custom_search_handles_missing_description(self):
        reset_command_state()
        class Response:
            status_code = 200

            def json(self):
                return {"items": [{"title": "Titre", "link": "https://example.invalid"}]}

        calls = []
        original_key = getattr(trinitty, "GOOGLE_KEY", "")
        original_engine = getattr(trinitty, "GOOGLE_ENGINE", "")
        original_isolate = trinitty.Isolate_Search
        original_get = trinitty.requests.get
        original_results_hub = trinitty.Results_Hub
        original_play = trinitty.Play_Audio_File
        trinitty.GOOGLE_KEY = "key"
        trinitty.GOOGLE_ENGINE = "engine"
        trinitty.Isolate_Search = lambda _text, _function_name: "requete test"
        trinitty.requests.get = lambda url, timeout=None: (url, timeout, Response())[-1]
        trinitty.Results_Hub = lambda results, top_results, from_function=None: calls.append(
            (results, top_results, from_function)
        ) or "results"
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual("results", trinitty.Google("cherche test", rnbr=1))
        finally:
            trinitty.GOOGLE_KEY = original_key
            trinitty.GOOGLE_ENGINE = original_engine
            trinitty.Isolate_Search = original_isolate
            trinitty.requests.get = original_get
            trinitty.Results_Hub = original_results_hub
            trinitty.Play_Audio_File = original_play

        self.assertEqual("Google", calls[0][2])
        self.assertEqual("no description", calls[0][0][0]["google_description"])

    def test_google_custom_search_can_sort_by_date(self):
        reset_command_state()
        class Response:
            status_code = 200

            def json(self):
                return {"items": [{"title": "Titre", "link": "https://example.invalid"}]}

        calls = []
        original_key = getattr(trinitty, "GOOGLE_KEY", "")
        original_engine = getattr(trinitty, "GOOGLE_ENGINE", "")
        original_sort = getattr(trinitty, "GOOGLE_SORT_BY_DATE", False)
        original_isolate = trinitty.Isolate_Search
        original_get = trinitty.requests.get
        original_results_hub = trinitty.Results_Hub
        original_play = trinitty.Play_Audio_File
        trinitty.GOOGLE_KEY = "key"
        trinitty.GOOGLE_ENGINE = "engine"
        trinitty.GOOGLE_SORT_BY_DATE = True
        trinitty.Isolate_Search = lambda _text, _function_name: "requete test"
        trinitty.requests.get = lambda url, timeout=None: (timeout, calls.append(url), Response())[-1]
        trinitty.Results_Hub = lambda _results, _top_results, from_function=None: (from_function, "results")[1]
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual("results", trinitty.Google("cherche test", rnbr=1))
        finally:
            trinitty.GOOGLE_KEY = original_key
            trinitty.GOOGLE_ENGINE = original_engine
            trinitty.GOOGLE_SORT_BY_DATE = original_sort
            trinitty.Isolate_Search = original_isolate
            trinitty.requests.get = original_get
            trinitty.Results_Hub = original_results_hub
            trinitty.Play_Audio_File = original_play

        self.assertIn("&sort=date&start=1", calls[0])

    def test_clean_web_search_query_removes_google_command_noise(self):
        reset_command_state()
        self.assertEqual(
            "albert einstein",
            trinitty.Clean_Web_Search_Query("fais une recherche sur google sur albert einstein"),
        )

    def test_google_uses_clean_query_and_fallback_when_custom_search_empty(self):
        reset_command_state()
        class Response:
            status_code = 200

            def json(self):
                return {"items": []}

        class Result:
            title = "Albert Einstein"
            description = "Physicien"
            url = "https://example.invalid/einstein"

        calls = []
        original_key = getattr(trinitty, "GOOGLE_KEY", "")
        original_engine = getattr(trinitty, "GOOGLE_ENGINE", "")
        original_isolate = trinitty.Isolate_Search
        original_get = trinitty.requests.get
        original_search = trinitty.googlesearch.search
        original_results_hub = trinitty.Results_Hub
        original_play = trinitty.Play_Audio_File
        trinitty.GOOGLE_KEY = "key"
        trinitty.GOOGLE_ENGINE = "engine"
        trinitty.Isolate_Search = lambda _text, _function_name: "une recherche sur google sur albert einstein"
        trinitty.requests.get = lambda url, timeout=None: calls.append(("custom", url)) or Response()
        trinitty.googlesearch.search = lambda query, **_kwargs: calls.append(("fallback", query)) or [Result()]
        trinitty.Results_Hub = lambda results, top_results, from_function=None: calls.append(
            ("hub", results, top_results, from_function)
        ) or "results"
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual("results", trinitty.Google("cherche test", rnbr=1))
        finally:
            trinitty.GOOGLE_KEY = original_key
            trinitty.GOOGLE_ENGINE = original_engine
            trinitty.Isolate_Search = original_isolate
            trinitty.requests.get = original_get
            trinitty.googlesearch.search = original_search
            trinitty.Results_Hub = original_results_hub
            trinitty.Play_Audio_File = original_play

        self.assertIn(("fallback", "albert einstein"), calls)
        self.assertIn("q=albert+einstein", calls[0][1])
        self.assertEqual("Google", calls[-1][3])

    def test_google_uses_web_fallback_when_google_sources_are_empty(self):
        reset_command_state()
        class Response:
            def __init__(self, payload=None, text="", status_code=200):
                self.payload = payload or {}
                self.text = text
                self.status_code = status_code

            def json(self):
                return self.payload

        html = """
        <html><body>
          <div class="result">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fduckduckgo.com%2Fy.js%3Fad_domain%3Dexample.invalid">
              Publicite
            </a>
          </div>
          <div class="result">
            <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.invalid%2Feinstein">
              Albert Einstein
            </a>
            <a class="result__snippet">Physicien theoricien</a>
          </div>
        </body></html>
        """

        calls = []
        original_key = getattr(trinitty, "GOOGLE_KEY", "")
        original_engine = getattr(trinitty, "GOOGLE_ENGINE", "")
        original_isolate = trinitty.Isolate_Search
        original_get = trinitty.requests.get
        original_search = trinitty.googlesearch.search
        original_results_hub = trinitty.Results_Hub
        original_play = trinitty.Play_Audio_File

        def fake_get(url, **kwargs):
            calls.append(("get", url, kwargs))
            if "googleapis.com" in url:
                return Response(payload={"items": []})
            return Response(text=html)

        trinitty.GOOGLE_KEY = "key"
        trinitty.GOOGLE_ENGINE = "engine"
        trinitty.Isolate_Search = lambda _text, _function_name: "fais une recherche sur google sur albert einstein"
        trinitty.requests.get = fake_get
        trinitty.googlesearch.search = lambda *_args, **_kwargs: []
        trinitty.Results_Hub = lambda results, top_results, from_function=None: calls.append(
            ("hub", results, top_results, from_function)
        ) or "results"
        trinitty.Play_Audio_File = lambda path, **_kwargs: calls.append(("play", path)) or 0
        try:
            self.assertEqual("results", trinitty.Google("cherche test", rnbr=1))
        finally:
            trinitty.GOOGLE_KEY = original_key
            trinitty.GOOGLE_ENGINE = original_engine
            trinitty.Isolate_Search = original_isolate
            trinitty.requests.get = original_get
            trinitty.googlesearch.search = original_search
            trinitty.Results_Hub = original_results_hub
            trinitty.Play_Audio_File = original_play

        hub_call = calls[-1]
        self.assertEqual("hub", hub_call[0])
        self.assertEqual("Google", hub_call[3])
        self.assertEqual("Albert Einstein", hub_call[1][0]["google_title"])
        self.assertEqual("https://example.invalid/einstein", hub_call[1][0]["google_url"])
        self.assertNotIn("play", [call[0] for call in calls])

    def test_get_title_link_uses_web_fallback_with_site_filter(self):
        reset_command_state()
        class Response:
            status_code = 200
            text = """
            <html><body>
              <div class="result">
                <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.invalid%2Feinstein">
                  Albert Einstein officiel
                </a>
              </div>
              <div class="result">
                <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Ffr.wikipedia.org%2Fwiki%2FAlbert_Einstein">
                  Albert Einstein - Wikipedia
                </a>
              </div>
            </body></html>
            """

        original_key = getattr(trinitty, "GOOGLE_KEY", "")
        original_engine = getattr(trinitty, "GOOGLE_ENGINE", "")
        original_get = trinitty.requests.get
        original_search = trinitty.googlesearch.search
        original_play = trinitty.Play_Audio_File
        trinitty.GOOGLE_KEY = ""
        trinitty.GOOGLE_ENGINE = ""
        trinitty.requests.get = lambda *_args, **_kwargs: Response()
        trinitty.googlesearch.search = lambda *_args, **_kwargs: []
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual("Albert Einstein - Wikipedia", trinitty.GetTitleLink("albert einstein", "wikipedia"))
        finally:
            trinitty.GOOGLE_KEY = original_key
            trinitty.GOOGLE_ENGINE = original_engine
            trinitty.requests.get = original_get
            trinitty.googlesearch.search = original_search
            trinitty.Play_Audio_File = original_play

    def test_clean_wikipedia_search_query_removes_command_noise(self):
        reset_command_state()
        self.assertEqual(
            "albert einstein",
            trinitty.Clean_Wikipedia_Search_Query(
                "une recherche sur Albert Einstein sur Wikipédia s'il te plaît"
            ),
        )

    def test_wikipedia_uses_clean_direct_search_when_google_title_fails(self):
        reset_command_state()
        reset_runtime_queues()
        calls = []

        original_isolate = trinitty.Isolate_Search
        original_get_title = trinitty.GetTitleLink
        original_search = trinitty.wikipedia.search
        original_summary = trinitty.wikipedia.summary
        original_set_lang = trinitty.wikipedia.set_lang
        original_start_record = trinitty.Start_Thread_Record
        original_tts = trinitty.Text_To_Speech
        original_google = trinitty.Google
        original_play = trinitty.Play_Audio_File

        trinitty.Isolate_Search = (
            lambda _text, _function_name: "une recherche sur albert einstein sur wikipedia s'"
        )
        trinitty.GetTitleLink = lambda *_args, **_kwargs: None
        trinitty.wikipedia.set_lang = lambda lang: calls.append(("set_lang", lang))
        trinitty.wikipedia.search = lambda query: calls.append(("search", query)) or (
            ["Albert Einstein"] if query == "albert einstein" else []
        )
        trinitty.wikipedia.summary = lambda title, **_kwargs: calls.append(("summary", title)) or "Resume Einstein"
        trinitty.Start_Thread_Record = lambda: False
        trinitty.Text_To_Speech = lambda text, stayawake=False: calls.append(("tts", text, stayawake)) or "tts"
        trinitty.Google = lambda *_args, **_kwargs: calls.append(("google", _args, _kwargs)) or "google"
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual((), trinitty.Wikipedia("wikipedia albert einstein"))
        finally:
            trinitty.Isolate_Search = original_isolate
            trinitty.GetTitleLink = original_get_title
            trinitty.wikipedia.search = original_search
            trinitty.wikipedia.summary = original_summary
            trinitty.wikipedia.set_lang = original_set_lang
            trinitty.Start_Thread_Record = original_start_record
            trinitty.Text_To_Speech = original_tts
            trinitty.Google = original_google
            trinitty.Play_Audio_File = original_play

        self.assertIn(("search", "albert einstein"), calls)
        self.assertIn(("summary", "Albert Einstein"), calls)
        self.assertIn(("tts", "Resume Einstein", True), calls)
        self.assertNotIn("google", [call[0] for call in calls])

    def test_wikipedia_outer_error_falls_back_to_google(self):
        reset_command_state()
        calls = []
        original_isolate = trinitty.Isolate_Search
        original_get_title = trinitty.GetTitleLink
        original_google = trinitty.Google
        original_play = trinitty.Play_Audio_File
        trinitty.Isolate_Search = lambda _text, _function_name: "requete wiki"
        trinitty.GetTitleLink = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("boom"))
        trinitty.Google = lambda search, wiki_failed=False: calls.append((search, wiki_failed)) or "google"
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual("google", trinitty.Wikipedia("wikipedia test"))
        finally:
            trinitty.Isolate_Search = original_isolate
            trinitty.GetTitleLink = original_get_title
            trinitty.Google = original_google
            trinitty.Play_Audio_File = original_play

        self.assertEqual([("wikipedia test", True)], calls)

    def test_get_title_link_falls_back_when_custom_search_non_200(self):
        reset_command_state()
        class Response:
            status_code = 500

        class Result:
            title = "Titre wiki"
            url = "https://fr.wikipedia.org/wiki/Test"

        original_key = getattr(trinitty, "GOOGLE_KEY", "")
        original_engine = getattr(trinitty, "GOOGLE_ENGINE", "")
        original_get = trinitty.requests.get
        original_search = trinitty.googlesearch.search
        original_play = trinitty.Play_Audio_File
        trinitty.GOOGLE_KEY = "key"
        trinitty.GOOGLE_ENGINE = "engine"
        trinitty.requests.get = lambda url, timeout=None: (url, timeout, Response())[-1]
        trinitty.googlesearch.search = lambda *_args, **_kwargs: [Result()]
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            self.assertEqual("Titre wiki", trinitty.GetTitleLink("test", "wikipedia"))
        finally:
            trinitty.GOOGLE_KEY = original_key
            trinitty.GOOGLE_ENGINE = original_engine
            trinitty.requests.get = original_get
            trinitty.googlesearch.search = original_search
            trinitty.Play_Audio_File = original_play

    def test_to_gpt_without_openai_or_fallback_does_not_exit(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.SCRIPT_PATH = str(ROOT)
        trinitty.GPT4FREE_SERVERS_STATUS = False
        trinitty.Providers_To_Use = None
        calls = []
        original_check_history = trinitty.Check_History
        original_openai = trinitty.Openai_Gpt
        original_wait_audio = trinitty.Play_Wait_Response_Audio
        original_play = trinitty.Play_Audio_File
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Check_History = lambda _text, **_kwargs: False
        trinitty.Openai_Gpt = lambda _text: ""
        trinitty.Play_Wait_Response_Audio = lambda: calls.append(("wait", None)) or 0
        trinitty.Play_Audio_File = lambda path: calls.append(("play", path)) or 0
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual("sleep", trinitty.To_Gpt("question"))
        finally:
            trinitty.Check_History = original_check_history
            trinitty.Openai_Gpt = original_openai
            trinitty.Play_Wait_Response_Audio = original_wait_audio
            trinitty.Play_Audio_File = original_play
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual(
            [
                ("wait", None),
                ("play", str(ROOT / "local_sounds" / "errors" / "err_no_respons_allprovider.wav")),
                ("sleep", False),
            ],
            calls,
        )

    def test_to_gpt_starts_wait_audio_before_history_and_openai(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.GPT4FREE_SERVERS_STATUS = False
        calls = []
        originals = (
            trinitty.Start_Wait_Response_Audio,
            trinitty.Stop_Wait_Response_Audio,
            trinitty.Check_History,
            trinitty.Openai_Gpt,
            trinitty.Text_To_Speech,
        )
        trinitty.Start_Wait_Response_Audio = lambda: calls.append("wait-start") or "wait-handle"
        trinitty.Stop_Wait_Response_Audio = lambda handle: calls.append(("wait-stop", handle))
        trinitty.Check_History = lambda _text, **_kwargs: calls.append("history") or False
        trinitty.Openai_Gpt = lambda _text: calls.append("openai") or "reponse"
        trinitty.Text_To_Speech = lambda text, stayawake=False: calls.append(("tts", text, stayawake)) or "tts"
        try:
            self.assertEqual("tts", trinitty.To_Gpt("question"))
        finally:
            (
                trinitty.Start_Wait_Response_Audio,
                trinitty.Stop_Wait_Response_Audio,
                trinitty.Check_History,
                trinitty.Openai_Gpt,
                trinitty.Text_To_Speech,
            ) = originals

        self.assertEqual(
            ["wait-start", "history", "openai", ("wait-stop", "wait-handle"), ("tts", "reponse", False)],
            calls,
        )

    def test_to_gpt_keeps_history_mandatory_while_classification_runs_in_worker(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.SCRIPT_PATH = str(ROOT)
        trinitty.GPT4FREE_SERVERS_STATUS = False
        trinitty.Current_Category = []
        trinitty.Loaded_History_List = [
            {
                "hist_file": "oldcat",
                "hist_cats": "oldcat",
                "hist_input_full": "ancienne question",
                "hist_input_short": "ancienne question",
                "hist_output": "ancienne reponse",
                "hist_output_wav": "old.wav",
            }
        ]
        calls = []
        originals = (
            trinitty.Start_Wait_Response_Audio,
            trinitty.Stop_Wait_Response_Audio,
            trinitty.Classify,
            trinitty.preprocess,
            trinitty.similar,
            trinitty.Openai_Gpt,
            trinitty.Text_To_Speech,
        )

        def slow_classify(text):
            calls.append(("classify-worker", text))
            time.sleep(5.2)

        trinitty.Start_Wait_Response_Audio = lambda: calls.append("wait-start") or "wait-handle"
        trinitty.Stop_Wait_Response_Audio = lambda handle: calls.append(("wait-stop", handle))
        trinitty.Classify = slow_classify
        trinitty.preprocess = lambda value: value
        trinitty.similar = lambda left, right: calls.append(("history-scan", left, right)) or 0.0
        trinitty.Openai_Gpt = lambda text: calls.append(("openai", text)) or "reponse rapide"
        trinitty.Text_To_Speech = lambda text, stayawake=False: calls.append(("tts", text, stayawake)) or "tts"

        try:
            started = time.monotonic()
            self.assertEqual("tts", trinitty.To_Gpt("question actuelle"))
            elapsed = time.monotonic() - started
        finally:
            (
                trinitty.Start_Wait_Response_Audio,
                trinitty.Stop_Wait_Response_Audio,
                trinitty.Classify,
                trinitty.preprocess,
                trinitty.similar,
                trinitty.Openai_Gpt,
                trinitty.Text_To_Speech,
            ) = originals

        self.assertLess(elapsed, 1.0)
        self.assertIn(("history-scan", "question actuelle", "ancienne question"), calls)
        self.assertIn(("classify-worker", "question actuelle"), calls)
        self.assertIn(("openai", "question actuelle"), calls)

    def test_play_wait_response_audio_uses_packaged_wait_sound(self):
        reset_command_state()
        trinitty.SCRIPT_PATH = str(ROOT)
        calls = []
        original_randint = trinitty.Non_Crypto_Randint
        original_play = trinitty.Play_Audio_File
        trinitty.Non_Crypto_Randint = lambda _start, _end: 4
        trinitty.Play_Audio_File = lambda path: calls.append(path) or 0
        try:
            trinitty.Play_Wait_Response_Audio()
        finally:
            trinitty.Non_Crypto_Randint = original_randint
            trinitty.Play_Audio_File = original_play

        self.assertEqual([str(ROOT / "local_sounds" / "wait" / "4.wav")], calls)

    def test_to_gpt_discovers_g4f_only_after_openai_fails(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.SCRIPT_PATH = str(ROOT)
        trinitty.GPT4FREE_SERVERS_LIST = None
        trinitty.GPT4FREE_SERVERS_STATUS = "Active"
        trinitty.GPT4FREE_RUNTIME_AVAILABLE = True
        trinitty.Providers_To_Use = None
        calls = []
        original_check_history = trinitty.Check_History
        original_openai = trinitty.Openai_Gpt
        original_wait_audio = trinitty.Play_Wait_Response_Audio
        original_refresh = trinitty.Refresh_Gpt4free_Providers_Config
        original_getconf = trinitty.GetConf
        original_check_servers = trinitty.Check_Free_Servers
        original_freegpt = trinitty.FreeGpt
        trinitty.Check_History = lambda _text, **_kwargs: False
        trinitty.Openai_Gpt = lambda _text: ""
        trinitty.Play_Wait_Response_Audio = lambda: calls.append("wait") or 0
        trinitty.Refresh_Gpt4free_Providers_Config = lambda: calls.append("refresh") or False
        trinitty.GetConf = lambda: calls.append("getconf")
        trinitty.Check_Free_Servers = lambda: calls.append("check_servers") or ["g4f.Provider.Qwen"]
        trinitty.FreeGpt = lambda text, **kwargs: calls.append(("freegpt", text, kwargs)) or "freegpt"
        try:
            self.assertEqual("freegpt", trinitty.To_Gpt("question"))
        finally:
            trinitty.Check_History = original_check_history
            trinitty.Openai_Gpt = original_openai
            trinitty.Play_Wait_Response_Audio = original_wait_audio
            trinitty.Refresh_Gpt4free_Providers_Config = original_refresh
            trinitty.GetConf = original_getconf
            trinitty.Check_Free_Servers = original_check_servers
            trinitty.FreeGpt = original_freegpt

        self.assertEqual(["wait", "refresh", "getconf", "check_servers"], calls[:4])
        self.assertEqual("freegpt", calls[4][0])
        self.assertEqual("question", calls[4][1])
        self.assertEqual(
            {"check_history": False, "save_last_sentence": False, "play_wait": False},
            {key: calls[4][2][key] for key in ["check_history", "save_last_sentence", "play_wait"]},
        )
        self.assertIn("wait_audio", calls[4][2])
        self.assertEqual(["g4f.Provider.Qwen"], trinitty.Providers_To_Use)

    def test_load_csv_missing_required_file_returns_false_without_exit(self):
        reset_command_state()
        original_exit = trinitty.sys.exit
        original_paths = {
            "SCRIPT_PATH": getattr(trinitty, "SCRIPT_PATH", ""),
            "SAVED_ANSWER": getattr(trinitty, "SAVED_ANSWER", ""),
            "CMDFILE": getattr(trinitty, "CMDFILE", ""),
            "ALTFILE": getattr(trinitty, "ALTFILE", ""),
            "TRIFILE": getattr(trinitty, "TRIFILE", ""),
            "ACTFILE": getattr(trinitty, "ACTFILE", ""),
            "PREFILE": getattr(trinitty, "PREFILE", ""),
            "SYNFILE": getattr(trinitty, "SYNFILE", ""),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datas = root / "datas"
            datas.mkdir()
            (datas / "synonym.trinity").write_text("")
            (datas / "alt_trigger.trinity").write_text("trigger\n")
            (datas / "action.trinity").write_text("verb,functions\n")
            (datas / "prefix.trinity").write_text("present1,present2,condi1,condi2\n")
            (datas / "alt_cmd.trinity").write_text("function,trigger\n")
            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(root / "saved_answer")
            trinitty.Runtime_Errors = []
            trinitty.CMDFILE = str(datas / "cmd.trinity")
            trinitty.ALTFILE = str(datas / "alt_cmd.trinity")
            trinitty.TRIFILE = str(datas / "alt_trigger.trinity")
            trinitty.ACTFILE = str(datas / "action.trinity")
            trinitty.PREFILE = str(datas / "prefix.trinity")
            trinitty.SYNFILE = str(datas / "synonym.trinity")
            trinitty.sys.exit = lambda code=0: (_ for _ in ()).throw(SystemExit(code))
            try:
                self.assertFalse(trinitty.Load_Csv())
            finally:
                trinitty.sys.exit = original_exit
                for name, value in original_paths.items():
                    setattr(trinitty, name, value)

        self.assertEqual("Load_Csv", trinitty.Runtime_Errors[-1]["context"])
        self.assertIn("cmd.trinity", trinitty.Runtime_Errors[-1]["error"])

    def test_check_update_warns_without_exit(self):
        reset_command_state()
        original_exit = trinitty.sys.exit
        original_g4f = trinitty.g4f
        original_saved_answer = getattr(trinitty, "SAVED_ANSWER", "")
        original_runtime_available = getattr(trinitty, "GPT4FREE_RUNTIME_AVAILABLE", None)
        original_installed_version = trinitty.Installed_Trinitty_Version
        original_pypi_version = trinitty.Pypi_Latest_Version
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trinitty.SAVED_ANSWER = str(root / "saved_answer")
            trinitty.Runtime_Errors = []

            trinitty.Installed_Trinitty_Version = lambda: "0.1.0"
            trinitty.Pypi_Latest_Version = lambda: "0.2.0"
            trinitty.g4f = SimpleNamespace(
                version=SimpleNamespace(
                    utils=SimpleNamespace(
                        current_version="1",
                        latest_version="2",
                        check_version=lambda: None,
                    )
                )
            )
            trinitty.GPT4FREE_RUNTIME_AVAILABLE = True
            trinitty.sys.exit = lambda code=0: (_ for _ in ()).throw(SystemExit(code))
            try:
                self.assertFalse(trinitty.Check_Update())
            finally:
                trinitty.sys.exit = original_exit
                trinitty.g4f = original_g4f
                trinitty.SAVED_ANSWER = original_saved_answer
                trinitty.GPT4FREE_RUNTIME_AVAILABLE = original_runtime_available
                trinitty.Installed_Trinitty_Version = original_installed_version
                trinitty.Pypi_Latest_Version = original_pypi_version

        self.assertEqual("Check_Update", trinitty.Runtime_Errors[-1]["context"])
        self.assertIn("update available", trinitty.Runtime_Errors[-1]["error"])

    def test_version_newer_compares_multi_digit_versions(self):
        self.assertTrue(trinitty.Version_Newer("0.1.10", "0.1.6"))
        self.assertFalse(trinitty.Version_Newer("0.1.6", "0.1.10"))
        self.assertFalse(trinitty.Version_Newer("", "0.1.6"))

    def test_bad_confidence_interpretor_accepts_direct_correction(self):
        reset_command_state()
        trinitty.INTERPRETOR = True
        calls = []
        original_input = getattr(trinitty, "input", None)
        original_to_gpt = trinitty.To_Gpt
        trinitty.input = lambda _prompt="": "phrase corrigee"
        trinitty.To_Gpt = lambda text: calls.append(text) or "sent"
        try:
            self.assertEqual("sent", trinitty.Bad_Confidence("phrase mal comprise"))
        finally:
            if original_input is None:
                delattr(trinitty, "input")
            else:
                trinitty.input = original_input
            trinitty.To_Gpt = original_to_gpt

        self.assertEqual(["phrase corrigee"], calls)

    def test_simulate_conversation_uses_injected_responder_without_command_side_effects(self):
        reset_command_state()
        calls = []
        original_commandes = trinitty.Commandes
        trinitty.Commandes = lambda text: calls.append(text) or True
        try:
            transcript = trinitty.Simulate_Conversation(
                ["bonjour", "suite"],
                responder=lambda text, history: "%s:%s" % (len(history), text),
            )
        finally:
            trinitty.Commandes = original_commandes

        self.assertEqual([], calls)
        self.assertEqual(
            [
                {"user": "bonjour", "assistant": "0:bonjour", "command": None},
                {"user": "suite", "assistant": "1:suite", "command": None},
            ],
            transcript,
        )

    def test_simulate_conversation_can_execute_commands_when_requested(self):
        reset_command_state()
        calls = []
        original_commandes = trinitty.Commandes
        trinitty.Commandes = lambda text: calls.append(text) or "F_quit"
        try:
            transcript = trinitty.Simulate_Conversation(["ferme"], execute_commands=True)
        finally:
            trinitty.Commandes = original_commandes

        self.assertEqual(["ferme"], calls)
        self.assertEqual("F_quit", transcript[0]["command"])

    def test_check_transcript_uses_word_confidence_when_transcript_confidence_missing(self):
        reset_command_state()

        self.assertEqual(
            ("bonjour trinitty", True),
            trinitty.Check_Transcript(
                "bonjour trinitty",
                0.0,
                ["bonjour", "trinitty"],
                [0.9, 0.85],
                "",
            ),
        )

    def test_check_transcript_rejects_low_word_confidence_even_when_transcript_is_high(self):
        reset_command_state()

        self.assertEqual(
            ("bonjour trinitty", False),
            trinitty.Check_Transcript(
                "bonjour trinitty",
                0.95,
                ["bonjour", "trinitty"],
                [0.95, 0.4],
                "",
            ),
        )

    def test_check_transcript_stt_error_returns_without_keyboard_prompt(self):
        reset_command_state()
        trinitty.Runtime_Errors = []
        calls = []
        originals = (
            trinitty.Play_Audio_File,
            trinitty.Text_To_Speech,
            trinitty.Prompt,
        )
        missing = object()
        original_saved = getattr(trinitty, "SAVED_ANSWER", missing)
        with tempfile.TemporaryDirectory() as tmp:
            trinitty.SAVED_ANSWER = str(Path(tmp) / "saved")
            trinitty.Play_Audio_File = lambda path: calls.append(("play", path)) or 0
            trinitty.Text_To_Speech = lambda *_args, **_kwargs: calls.append(("tts", None))
            trinitty.Prompt = lambda: (_ for _ in ()).throw(AssertionError("Prompt should not be called"))
            try:
                self.assertEqual(
                    ("", False),
                    trinitty.Check_Transcript("", 0, [], [], "Speech_To_Text:timeout"),
                )
            finally:
                (
                    trinitty.Play_Audio_File,
                    trinitty.Text_To_Speech,
                    trinitty.Prompt,
                ) = originals
                if original_saved is missing:
                    delattr(trinitty, "SAVED_ANSWER")
                else:
                    trinitty.SAVED_ANSWER = original_saved

        self.assertEqual(1, len(calls))
        self.assertEqual("play", calls[0][0])
        self.assertTrue(calls[0][1].endswith("/local_sounds/errors/err_stt.wav"))
        self.assertEqual("Check_Transcript", trinitty.Runtime_Errors[-1]["context"])

    def test_speech_to_text_returns_error_when_google_speech_import_is_broken(self):
        reset_command_state()
        original_speech = trinitty.speech
        trinitty.Runtime_Errors = []
        trinitty.speech = trinitty.MissingDependency(
            "google.cloud.speech_v1p1beta1",
            "google-cloud-speech",
            ValueError("bad marshal data (invalid reference)"),
        )
        try:
            transcripts, confidence, words, words_confidence, err_msg = trinitty.Speech_To_Text(b"audio")
        finally:
            trinitty.speech = original_speech

        self.assertEqual("", transcripts)
        self.assertEqual(0, confidence)
        self.assertEqual([], words)
        self.assertEqual([], words_confidence)
        self.assertIn("Speech_To_Text:", err_msg)
        self.assertIn("bad marshal data", err_msg)
        self.assertEqual("Speech_To_Text", trinitty.Runtime_Errors[-1]["context"])

    def test_speech_to_text_passes_google_timeout(self):
        reset_command_state()
        original_speech = trinitty.speech
        calls = []

        class FakeRecognitionConfig:
            AudioEncoding = SimpleNamespace(LINEAR16="linear16")

            def __init__(self, **kwargs):
                self.kwargs = kwargs

        class FakeRecognitionAudio:
            def __init__(self, content):
                self.content = content

        class FakeSpeechClient:
            def recognize(self, request, timeout=None):
                calls.append((request, timeout))
                word = SimpleNamespace(word="minecraft", confidence=0.91)
                alternative = SimpleNamespace(
                    transcript="question minecraft",
                    confidence=0.93,
                    words=[word],
                )
                result = SimpleNamespace(alternatives=[alternative])
                return SimpleNamespace(results=[result])

        trinitty.speech = SimpleNamespace(
            SpeechClient=FakeSpeechClient,
            RecognitionAudio=FakeRecognitionAudio,
            RecognitionConfig=FakeRecognitionConfig,
        )
        trinitty.GOOGLE_STT_TIMEOUT = 3.5
        try:
            transcripts, confidence, words, words_confidence, err_msg = trinitty.Speech_To_Text(b"audio")
        finally:
            trinitty.speech = original_speech

        self.assertEqual("question minecraft", transcripts)
        self.assertEqual(0.93, confidence)
        self.assertEqual(["minecraft"], words)
        self.assertEqual([0.91], words_confidence)
        self.assertEqual("", err_msg)
        self.assertEqual(3.5, calls[0][1])
        self.assertEqual(b"audio", calls[0][0]["audio"].content)

    def test_speech_to_text_returns_error_when_google_recognize_times_out(self):
        reset_command_state()
        original_speech = trinitty.speech
        trinitty.Runtime_Errors = []

        class FakeRecognitionConfig:
            AudioEncoding = SimpleNamespace(LINEAR16="linear16")

            def __init__(self, **_kwargs):
                pass

        class FakeRecognitionAudio:
            def __init__(self, content):
                self.content = content

        class FakeSpeechClient:
            def recognize(self, request, timeout=None):
                raise TimeoutError("google speech timeout")

        trinitty.speech = SimpleNamespace(
            SpeechClient=FakeSpeechClient,
            RecognitionAudio=FakeRecognitionAudio,
            RecognitionConfig=FakeRecognitionConfig,
        )
        try:
            transcripts, confidence, words, words_confidence, err_msg = trinitty.Speech_To_Text(b"audio")
        finally:
            trinitty.speech = original_speech

        self.assertEqual("", transcripts)
        self.assertEqual(0, confidence)
        self.assertEqual([], words)
        self.assertEqual([], words_confidence)
        self.assertIn("Speech_To_Text:google speech timeout", err_msg)
        self.assertEqual("Speech_To_Text", trinitty.Runtime_Errors[-1]["context"])

    @unittest.skipUnless(hasattr(trinitty.signal, "SIGALRM"), "SIGALRM is POSIX-only")
    def test_runtime_timeout_raises_on_main_thread(self):
        reset_command_state()

        with self.assertRaises(TimeoutError):
            with trinitty.Runtime_Timeout(0.01, "test"):
                time.sleep(0.1)

    def test_interpretor_mode_skips_pico_key_loading(self):
        reset_command_state()
        trinitty.INTERPRETOR = True
        trinitty.PUSH_TO_TALK = False
        calls = []
        original_pico = trinitty.PicoLoadKeys
        original_google = trinitty.GoogleLoadKeys
        original_detect = trinitty.DetectLanguageLoadKeys
        trinitty.PicoLoadKeys = lambda: calls.append("pico") or "pico-key"
        trinitty.GoogleLoadKeys = lambda: ("", "", "")
        trinitty.DetectLanguageLoadKeys = lambda: None
        try:
            trinitty.Load_Runtime_Keys()
        finally:
            trinitty.PicoLoadKeys = original_pico
            trinitty.GoogleLoadKeys = original_google
            trinitty.DetectLanguageLoadKeys = original_detect

        self.assertEqual([], calls)
        self.assertIsNone(trinitty.PICO_KEY)

    def test_push_to_talk_mode_skips_pico_key_loading(self):
        reset_command_state()
        trinitty.INTERPRETOR = False
        trinitty.PUSH_TO_TALK = True
        calls = []
        original_pico = trinitty.PicoLoadKeys
        original_google = trinitty.GoogleLoadKeys
        original_detect = trinitty.DetectLanguageLoadKeys
        trinitty.PicoLoadKeys = lambda: calls.append("pico") or "pico-key"
        trinitty.GoogleLoadKeys = lambda: ("", "", "")
        trinitty.DetectLanguageLoadKeys = lambda: None
        try:
            trinitty.Load_Runtime_Keys()
        finally:
            trinitty.PicoLoadKeys = original_pico
            trinitty.GoogleLoadKeys = original_google
            trinitty.DetectLanguageLoadKeys = original_detect

        self.assertEqual([], calls)
        self.assertIsNone(trinitty.PICO_KEY)

    def test_missing_pico_key_switches_to_push_to_talk(self):
        reset_command_state()
        trinitty.INTERPRETOR = False
        trinitty.PUSH_TO_TALK = False
        original_script_path = trinitty.SCRIPT_PATH
        original_google = trinitty.GoogleLoadKeys
        original_detect = trinitty.DetectLanguageLoadKeys
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keys").mkdir()
            try:
                trinitty.SCRIPT_PATH = str(root)
                trinitty.GoogleLoadKeys = lambda: ("", "", "")
                trinitty.DetectLanguageLoadKeys = lambda: None
                trinitty.Load_Runtime_Keys()
            finally:
                trinitty.SCRIPT_PATH = original_script_path
                trinitty.GoogleLoadKeys = original_google
                trinitty.DetectLanguageLoadKeys = original_detect

        self.assertIsNone(trinitty.PICO_KEY)
        self.assertTrue(trinitty.PUSH_TO_TALK)

    def test_invalid_key_files_are_not_printed(self):
        reset_command_state()
        secrets = {
            "pico.key": "bad-pico-secret",
            "detectlanguage.key": "bad-detect-secret",
            "google_translate.key": "bad-google-translate",
            "google_search.key": "bad-google-search",
            "google_search_engine.id": "bad-engine",
        }
        original_script_path = trinitty.SCRIPT_PATH
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            keys = root / "keys"
            keys.mkdir()
            for name, value in secrets.items():
                (keys / name).write_text(value)

            stdout = io.StringIO()
            try:
                trinitty.SCRIPT_PATH = str(root)
                with contextlib.redirect_stdout(stdout):
                    self.assertIsNone(trinitty.PicoLoadKeys())
                    self.assertIsNone(trinitty.DetectLanguageLoadKeys())
                    self.assertEqual(("", "", ""), trinitty.GoogleLoadKeys())
            finally:
                trinitty.SCRIPT_PATH = original_script_path

        output = stdout.getvalue()
        for secret in secrets.values():
            self.assertNotIn(secret, output)

    def test_xcb_fix_does_not_create_empty_display(self):
        original_env_display = os.environ.get("DISPLAY")
        original_global_display = getattr(trinitty, "DISPLAY", "")
        try:
            os.environ.pop("DISPLAY", None)
            trinitty.DISPLAY = ""
            trinitty.Xcb_Fix("set")
            self.assertNotIn("DISPLAY", os.environ)

            os.environ["DISPLAY"] = ":99"
            trinitty.Xcb_Fix("unset")
            self.assertNotIn("DISPLAY", os.environ)
            self.assertEqual(":99", trinitty.DISPLAY)

            trinitty.Xcb_Fix("set")
            self.assertEqual(":99", os.environ.get("DISPLAY"))
        finally:
            trinitty.DISPLAY = original_global_display
            if original_env_display is None:
                os.environ.pop("DISPLAY", None)
            else:
                os.environ["DISPLAY"] = original_env_display

    def test_quit_uses_expected_time_of_day_sound(self):
        reset_command_state()
        cases = [
            (23, "quit_night.wav"),
            (10, "quit_day.wav"),
            (15, "quit_afternoon.wav"),
            (19, "quit_evening.wav"),
        ]
        original_datetime = trinitty.datetime
        original_play = trinitty.Play_Audio_File
        original_exit = trinitty.sys.exit
        try:
            for hour, expected_sound in cases:
                calls = []

                trinitty.datetime = SimpleNamespace(now=lambda current_hour=hour: SimpleNamespace(hour=current_hour))
                trinitty.Play_Audio_File = lambda path, current_calls=calls: current_calls.append(path) or 0
                trinitty.sys.exit = lambda code=0: (_ for _ in ()).throw(SystemExit(code))

                with self.subTest(hour=hour):
                    with self.assertRaises(SystemExit) as exc:
                        trinitty.Quit()

                    self.assertEqual(0, exc.exception.code)
                    self.assertTrue(calls[0].endswith("/local_sounds/quit/" + expected_sound), calls)
                    self.assertTrue(calls[1].endswith("/local_sounds/boot/xspx.wav"), calls)
        finally:
            trinitty.datetime = original_datetime
            trinitty.Play_Audio_File = original_play
            trinitty.sys.exit = original_exit

    def test_getconf_loads_local_override_after_base_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datas = root / "datas"
            default_saved = root / "local_sounds" / "saved_answer"
            local_saved = root / "private_saved"
            datas.mkdir(parents=True)
            default_saved.mkdir(parents=True)
            local_saved.mkdir()
            (datas / "conf.trinity").write_text(
                "\n".join(
                    [
                        "SAVED_ANSWER = default",
                        "OPENAI_ENABLED = True",
                        "OPENAI_MODEL = gpt-5.5",
                        "OPENAI_API_KEY_FILE = keys/openai.key",
                        "  # OPENAI_TIMEOUT = 999",
                        "OPENAI_TIMEOUT = 12",
                        'OPENAI_INSTRUCTIONS = "Keep # as plain text" # inline comment',
                        "SPACY_MODEL = fr_core_news_md",
                        "GOOGLE_LANGUAGE_TIMEOUT = 13",
                        "HISTORY_CLASSIFICATION_ENABLED = True",
                        "GPT4FREE_SERVERS_LIST = None",
                        "GPT4FREE_SERVERS_STATUS = None",
                    ]
                )
            )
            (datas / "conf.local.trinity").write_text(
                "SAVED_ANSWER = %s\nOPENAI_TIMEOUT = 7\nGOOGLE_STT_TIMEOUT = 11\nGOOGLE_LANGUAGE_TIMEOUT = 5\nHISTORY_CLASSIFICATION_ENABLED = False\n"
                % local_saved
            )

            trinitty.SCRIPT_PATH = str(root)
            trinitty.DEBUG = False
            trinitty.GPT4FREE_SERVERS_LIST = None
            trinitty.GPT4FREE_SERVERS_STATUS = "Active"
            trinitty.GetConf()

            self.assertEqual(str(local_saved), trinitty.SAVED_ANSWER)
            self.assertEqual(7.0, trinitty.OPENAI_TIMEOUT)
            self.assertEqual(11.0, trinitty.GOOGLE_STT_TIMEOUT)
            self.assertEqual(5.0, trinitty.GOOGLE_LANGUAGE_TIMEOUT)
            self.assertFalse(trinitty.HISTORY_CLASSIFICATION_ENABLED)
            self.assertEqual("Keep # as plain text", trinitty.OPENAI_INSTRUCTIONS)
            self.assertTrue((local_saved / "saved_error").exists())

    def test_getconf_loads_user_data_override_after_packaged_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "home"
            datas = root / "package" / "datas"
            user_datas = home / ".local" / "share" / "Trinitty" / "datas"
            datas.mkdir(parents=True)
            user_datas.mkdir(parents=True)
            (datas / "conf.trinity").write_text(
                "\n".join(
                    [
                        "SAVED_ANSWER = default",
                        "OPENAI_MODEL = package-model",
                        "OPENAI_TIMEOUT = 30",
                        "GOOGLE_STT_TIMEOUT = 20",
                        "GOOGLE_LANGUAGE_TIMEOUT = 13",
                        "HISTORY_CLASSIFICATION_ENABLED = True",
                        "GPT4FREE_SERVERS_STATUS = Active",
                    ]
                )
            )
            (user_datas / "conf.trinity").write_text(
                "OPENAI_MODEL = user-model\nOPENAI_TIMEOUT = 4\nGOOGLE_STT_TIMEOUT = 8\nGOOGLE_LANGUAGE_TIMEOUT = 6\nHISTORY_CLASSIFICATION_ENABLED = False\nGPT4FREE_SERVERS_STATUS = None\n"
            )
            original_home = os.environ.get("HOME")
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            try:
                os.environ["HOME"] = str(home)
                trinitty.SCRIPT_PATH = str(root / "package")
                trinitty.GPT4FREE_SERVERS_LIST = None
                trinitty.GPT4FREE_SERVERS_STATUS = "Active"
                trinitty.GetConf()
            finally:
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home
                if original_script_path is missing:
                    delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path

            self.assertEqual("user-model", trinitty.OPENAI_MODEL)
            self.assertEqual(4.0, trinitty.OPENAI_TIMEOUT)
            self.assertEqual(8.0, trinitty.GOOGLE_STT_TIMEOUT)
            self.assertEqual(6.0, trinitty.GOOGLE_LANGUAGE_TIMEOUT)
            self.assertFalse(trinitty.HISTORY_CLASSIFICATION_ENABLED)
            self.assertIsNone(trinitty.GPT4FREE_SERVERS_STATUS)

    def test_getconf_accepts_quoted_gpt4free_provider_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datas = root / "datas"
            saved = root / "local_sounds" / "saved_answer"
            datas.mkdir(parents=True)
            saved.mkdir(parents=True)
            (datas / "conf.trinity").write_text(
                "\n".join(
                    [
                        "SAVED_ANSWER = default",
                        'GPT4FREE_SERVERS_LIST = ["g4f.Provider.Qwen", g4f.Provider.OpenaiChat]',
                        "GPT4FREE_SERVERS_STATUS = None",
                    ]
                )
            )
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            try:
                trinitty.SCRIPT_PATH = str(root)
                trinitty.GPT4FREE_SERVERS_LIST = None
                trinitty.GPT4FREE_SERVERS_STATUS = "Active"
                trinitty.GetConf()
            finally:
                if original_script_path is missing:
                    delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path

            self.assertEqual(["g4f.Provider.Qwen", "g4f.Provider.OpenaiChat"], trinitty.GPT4FREE_SERVERS_LIST)
            self.assertEqual("Active", trinitty.GPT4FREE_SERVERS_STATUS)

    def test_gpt4free_refresh_honors_local_status_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datas = root / "datas"
            datas.mkdir(parents=True)
            base_config = "\n".join(
                [
                    "GPT4FREE_SERVERS_LIST = None",
                    "GPT4FREE_SERVERS_STATUS = Active",
                    "GPT4FREE_SERVERS_AUTH = False",
                ]
            )
            (datas / "conf.trinity").write_text(base_config)
            (datas / "conf.local.trinity").write_text("GPT4FREE_SERVERS_STATUS = None\n")
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            original_discover = trinitty.Discover_Gpt4free_Text_Providers
            calls = []
            try:
                trinitty.SCRIPT_PATH = str(root)
                trinitty.Discover_Gpt4free_Text_Providers = lambda auth_mode=False: calls.append(auth_mode) or [
                    "g4f.Provider.Qwen"
                ]
                self.assertFalse(trinitty.Refresh_Gpt4free_Providers_Config())
            finally:
                if original_script_path is missing:
                    delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path
                trinitty.Discover_Gpt4free_Text_Providers = original_discover

            self.assertEqual([], calls)
            self.assertEqual(base_config, (datas / "conf.trinity").read_text())

    def test_gpt4free_refresh_write_failure_is_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            datas = root / "datas"
            datas.mkdir(parents=True)
            base_config = "\n".join(
                [
                    "GPT4FREE_SERVERS_LIST = None",
                    "GPT4FREE_SERVERS_STATUS = Active",
                    "GPT4FREE_SERVERS_AUTH = False",
                ]
            )
            conf_file = datas / "conf.trinity"
            conf_file.write_text(base_config)
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            original_discover = trinitty.Discover_Gpt4free_Text_Providers
            original_replace = trinitty.os.replace
            try:
                trinitty.SCRIPT_PATH = str(root)
                trinitty.Discover_Gpt4free_Text_Providers = lambda _auth_mode=False: ["g4f.Provider.Qwen"]

                def fail_replace(_source, _dest):
                    raise OSError("read-only config")

                trinitty.os.replace = fail_replace
                self.assertFalse(trinitty.Refresh_Gpt4free_Providers_Config())
            finally:
                if original_script_path is missing:
                    delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path
                trinitty.Discover_Gpt4free_Text_Providers = original_discover
                trinitty.os.replace = original_replace

            self.assertEqual(base_config, conf_file.read_text())
            self.assertFalse((datas / "conf.trinity.tmp").exists())

    def test_gpt4free_auto_reject_notworking_is_configurable(self):
        class Provider:
            working = False
            default_model = "gpt-test"

        Provider.__module__ = "g4f.Provider.free"
        original_auto_reject = getattr(trinitty, "GPT4FREE_AUTO_REJECT_NOTWORKING", True)
        try:
            trinitty.GPT4FREE_AUTO_REJECT_NOTWORKING = True
            self.assertFalse(trinitty.Gpt4free_Provider_Is_Text_Chat(Provider))

            trinitty.GPT4FREE_AUTO_REJECT_NOTWORKING = False
            self.assertTrue(trinitty.Gpt4free_Provider_Is_Text_Chat(Provider))
        finally:
            trinitty.GPT4FREE_AUTO_REJECT_NOTWORKING = original_auto_reject

    def test_sync_gpt4free_cookie_captures_copies_har_and_json(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            dest = root / "dest"
            source.mkdir()
            (source / "chatgpt.com_Archive.har").write_text("har")
            (source / "gemini.json").write_text("{}")
            (source / "ignore.txt").write_text("no")

            copied = trinitty.Sync_Gpt4free_Cookie_Captures(str(source), str(dest))

            self.assertEqual(
                [str(dest / "chatgpt.com_Archive.har"), str(dest / "gemini.json")],
                sorted(copied),
            )
            self.assertTrue((dest / "chatgpt.com_Archive.har").exists())
            self.assertTrue((dest / "gemini.json").exists())
            self.assertFalse((dest / "ignore.txt").exists())

    def test_gpt4free_cookies_dir_falls_back_to_user_data_when_script_path_is_not_directory(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_script_path = root / "installed-file"
            fake_script_path.write_text("")
            home = root / "home"
            home.mkdir()
            missing = object()
            original_script_path = getattr(trinitty, "SCRIPT_PATH", missing)
            original_home = os.environ.get("HOME")
            try:
                trinitty.SCRIPT_PATH = str(fake_script_path)
                os.environ["HOME"] = str(home)
                self.assertEqual(
                    str(home / ".local" / "share" / "Trinitty" / "g4f_cookies"),
                    trinitty.Gpt4free_Cookies_Dir(),
                )
            finally:
                if original_script_path is missing:
                    delattr(trinitty, "SCRIPT_PATH")
                else:
                    trinitty.SCRIPT_PATH = original_script_path
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

    def test_gpt4free_auth_provider_requires_cookie_or_key(self):
        reset_command_state()

        class Gemini:
            __name__ = "Gemini"
            needs_auth = True
            working = True
            default_model = "gemini-2.5-pro"
            models = ("gemini-2.5-pro",)
            text_models = None
            url = "https://gemini.google.com"
            parent = None

        Gemini.__module__ = "g4f.Provider.needs_auth.Gemini"

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cookies = root / "datas" / "har_and_cookies"
            cookies.mkdir(parents=True)
            keys = root / "keys"
            keys.mkdir()
            trinitty.SCRIPT_PATH = str(root)

            self.assertFalse(trinitty.Gpt4free_Provider_Is_Text_Chat(Gemini, auth_mode="auth_only"))

            (cookies / "gemini.json").write_text("{}")
            self.assertTrue(trinitty.Gpt4free_Provider_Is_Text_Chat(Gemini, auth_mode="auth_only"))

            (cookies / "gemini.json").unlink()
            (keys / "g4f_gemini.key").write_text("token")
            self.assertTrue(trinitty.Gpt4free_Provider_Is_Text_Chat(Gemini, auth_mode="auth_only"))

    def test_load_gpt4free_cookies_syncs_then_loads_cookie_files(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "tools" / "har_and_cookies"
            dest = root / "datas" / "har_and_cookies"
            source.mkdir(parents=True)
            dest.mkdir(parents=True)
            (source / "chatgpt.com_Archive.har").write_text("har")
            trinitty.SCRIPT_PATH = str(root)
            calls = []
            original_set = trinitty.set_cookies_dir
            original_read = trinitty.read_cookie_files
            trinitty.set_cookies_dir = lambda path: calls.append(("set", path))
            trinitty.read_cookie_files = lambda path: calls.append(("read", path)) or {"loaded": True}
            try:
                self.assertEqual({"loaded": True}, trinitty.Load_Gpt4free_Cookies())
            finally:
                trinitty.set_cookies_dir = original_set
                trinitty.read_cookie_files = original_read

            self.assertTrue((dest / "chatgpt.com_Archive.har").exists())
            self.assertEqual([("set", str(dest)), ("read", str(dest))], calls)

    def test_gpt4free_runtime_probe_disables_fallback_after_segfault(self):
        reset_command_state()
        original_run = trinitty.subprocess.run
        trinitty.subprocess.run = lambda *_args, **_kwargs: SimpleNamespace(
            returncode=-11,
            stdout="",
            stderr="",
        )
        try:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertFalse(trinitty.Ensure_Gpt4free_Runtime_Available())
        finally:
            trinitty.subprocess.run = original_run

        self.assertFalse(trinitty.GPT4FREE_RUNTIME_AVAILABLE)
        self.assertIn("SIGSEGV 11", output.getvalue())

    def test_ensure_gpt4free_cookies_loads_only_once(self):
        reset_command_state()
        calls = []
        original_load = trinitty.Load_Gpt4free_Cookies
        trinitty.Load_Gpt4free_Cookies = lambda: calls.append("load") or {"loaded": True}
        try:
            self.assertTrue(trinitty.Ensure_Gpt4free_Cookies_Loaded())
            self.assertTrue(trinitty.Ensure_Gpt4free_Cookies_Loaded())
        finally:
            trinitty.Load_Gpt4free_Cookies = original_load

        self.assertEqual(["load"], calls)
        self.assertTrue(trinitty.GPT4FREE_COOKIES_LOADED)

    def test_log_error_records_list_and_file(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            saved = Path(tmp) / "saved"
            saved.mkdir()
            trinitty.SAVED_ANSWER = str(saved)
            trinitty.Runtime_Errors = []

            trinitty.Log_Error("test_context", "boom")

            self.assertEqual("test_context", trinitty.Runtime_Errors[-1]["context"])
            log_file = saved / "saved_error" / "trinitty.errors"
            self.assertIn("test_context: boom", log_file.read_text())

    def test_debug_log_writes_to_user_log_file_when_debug_is_enabled(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            saved = Path(tmp) / "saved"
            saved.mkdir()
            original_home = os.environ.get("HOME")
            original_debug = trinitty.DEBUG
            missing = object()
            original_saved = getattr(trinitty, "SAVED_ANSWER", missing)
            try:
                os.environ["HOME"] = str(home)
                trinitty.DEBUG = True
                trinitty.SAVED_ANSWER = str(saved)
                trinitty.Runtime_Errors = []

                trinitty.Log_Error("debug_context", ValueError("debug boom"))

                debug_file = Path(trinitty.Debug_Log_File())
                debug_text = debug_file.read_text()
            finally:
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home
                trinitty.DEBUG = original_debug
                if original_saved is missing:
                    delattr(trinitty, "SAVED_ANSWER")
                else:
                    trinitty.SAVED_ANSWER = original_saved

        self.assertIn("ERROR[debug_context]", debug_text)
        self.assertIn("ValueError: debug boom", debug_text)
        self.assertTrue(str(debug_file).endswith(".log"))

    def test_wait_for_times_out_and_stops_recording(self):
        reset_runtime_queues()
        trinitty.record_on.put(True)
        original_poll = trinitty.WAIT_FOR_POLL_INTERVAL
        trinitty.WAIT_FOR_POLL_INTERVAL = 0.001
        try:
            started = time.monotonic()
            self.assertFalse(trinitty.Wait_for("audio", timeout=0.01))
            elapsed = time.monotonic() - started
        finally:
            trinitty.WAIT_FOR_POLL_INTERVAL = original_poll

        self.assertLess(elapsed, 1)
        self.assertTrue(trinitty.record_on.empty())
        self.assertFalse(trinitty.cancel_operation.empty())

    def test_wait_uses_prompt_directly_in_interpretor_mode(self):
        reset_command_state()
        trinitty.INTERPRETOR = True
        calls = []
        original_prompt = trinitty.Prompt
        trinitty.Prompt = lambda allowed_functions=None, from_function=None: calls.append(
            (allowed_functions, from_function)
        ) or "prompt"
        try:
            self.assertEqual("prompt", trinitty.Wait(allowed_functions=["F_quit"], from_function="Results_Hub"))
        finally:
            trinitty.Prompt = original_prompt

        self.assertEqual([(["F_quit"], "Results_Hub")], calls)

    def test_wait_uses_push_to_talk_when_enabled(self):
        reset_command_state()
        trinitty.INTERPRETOR = False
        trinitty.PUSH_TO_TALK = True
        original_push_to_talk = trinitty.Push_To_Talk
        trinitty.Push_To_Talk = lambda: "push"
        try:
            self.assertEqual("push", trinitty.Wait(allowed_functions=["F_quit"], from_function="Results_Hub"))
        finally:
            trinitty.Push_To_Talk = original_push_to_talk

    def test_wait_times_out_without_blocking_forever(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.INTERPRETOR = False
        trinitty.PICO_KEY = "pico"
        calls = []

        class FakePorcupine:
            sample_rate = 16000
            frame_length = 2

            def process(self, _pcm):
                return -1

            def delete(self):
                calls.append("delete")

        class FakeStream:
            def read(self, frame_length, exception_on_overflow=False):
                calls.append(("read", frame_length, exception_on_overflow))
                return b"\x00\x00" * frame_length

            def close(self):
                calls.append("close")

        class FakePyAudio:
            def open(self, **_kwargs):
                return FakeStream()

            def terminate(self):
                calls.append("terminate")

        original_create = trinitty.pvporcupine.create
        original_pyaudio = trinitty.pyaudio.PyAudio
        original_poll = trinitty.WAIT_FOR_POLL_INTERVAL
        original_play = trinitty.Play_Audio_File
        trinitty.pvporcupine.create = lambda **_kwargs: FakePorcupine()
        trinitty.pyaudio.PyAudio = lambda: FakePyAudio()
        trinitty.WAIT_FOR_POLL_INTERVAL = 0.001
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        try:
            started = time.monotonic()
            self.assertIsNone(trinitty.Wait(timeout=0.01))
            elapsed = time.monotonic() - started
        finally:
            trinitty.pvporcupine.create = original_create
            trinitty.pyaudio.PyAudio = original_pyaudio
            trinitty.WAIT_FOR_POLL_INTERVAL = original_poll
            trinitty.Play_Audio_File = original_play

        self.assertLess(elapsed, 1)
        self.assertFalse(trinitty.cancel_operation.empty())
        self.assertIn("delete", calls)
        self.assertIn("close", calls)
        self.assertIn("terminate", calls)

    def test_push_to_talk_waits_for_enter_then_records(self):
        reset_command_state()
        calls = []
        original_input = getattr(trinitty, "input", None)
        original_trinitty = trinitty.Trinitty
        original_pyaudio = trinitty.pyaudio
        original_webrtcvad = trinitty.webrtcvad
        trinitty.input = lambda _prompt="": calls.append("input") or ""
        trinitty.Trinitty = lambda fname="WakeMe": calls.append(fname) or "speech"
        trinitty.pyaudio = SimpleNamespace()
        trinitty.webrtcvad = SimpleNamespace()
        try:
            self.assertEqual("speech", trinitty.Push_To_Talk())
        finally:
            if original_input is None:
                delattr(trinitty, "input")
            else:
                trinitty.input = original_input
            trinitty.Trinitty = original_trinitty
            trinitty.pyaudio = original_pyaudio
            trinitty.webrtcvad = original_webrtcvad

        self.assertEqual(["input", "Speech_To_Text"], calls)

    def test_push_to_talk_missing_audio_dependency_does_not_prompt_loop(self):
        reset_command_state()
        reset_runtime_queues()
        calls = []
        original_pyaudio = trinitty.pyaudio
        original_webrtcvad = trinitty.webrtcvad
        original_input = getattr(trinitty, "input", None)
        original_trinitty = trinitty.Trinitty
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.pyaudio = trinitty.MissingDependency("pyaudio")
        trinitty.webrtcvad = SimpleNamespace()
        trinitty.input = lambda _prompt="": (_ for _ in ()).throw(AssertionError("input should not be called"))
        trinitty.Trinitty = lambda _fname="WakeMe": (_ for _ in ()).throw(AssertionError("Trinitty should not recurse"))
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual("sleep", trinitty.Push_To_Talk())
        finally:
            trinitty.pyaudio = original_pyaudio
            trinitty.webrtcvad = original_webrtcvad
            if original_input is None:
                delattr(trinitty, "input")
            else:
                trinitty.input = original_input
            trinitty.Trinitty = original_trinitty
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual([("sleep", False)], calls)

    def test_start_thread_record_missing_audio_dependency_does_not_start_threads(self):
        reset_command_state()
        reset_runtime_queues()
        original_pyaudio = trinitty.pyaudio
        original_webrtcvad = trinitty.webrtcvad
        original_thread = trinitty.Thread
        trinitty.pyaudio = trinitty.MissingDependency("pyaudio")
        trinitty.webrtcvad = SimpleNamespace()
        trinitty.Thread = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("thread should not start"))
        try:
            self.assertFalse(trinitty.Start_Thread_Record())
        finally:
            trinitty.pyaudio = original_pyaudio
            trinitty.webrtcvad = original_webrtcvad
            trinitty.Thread = original_thread

        self.assertTrue(trinitty.record_on.empty())
        self.assertFalse(trinitty.cancel_operation.empty())
        self.assertFalse(trinitty.No_Input.empty())

    def test_trinitty_speech_to_text_does_not_reenter_wakeme_when_recording_cannot_start(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.INTERPRETOR = False
        calls = []
        original_start = trinitty.Start_Thread_Record
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Start_Thread_Record = lambda: False
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual("sleep", trinitty.Trinitty("Speech_To_Text"))
        finally:
            trinitty.Start_Thread_Record = original_start
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual([("sleep", False)], calls)

    def test_trinitty_routes_wakeme_to_push_to_talk_when_enabled(self):
        reset_command_state()
        trinitty.INTERPRETOR = False
        trinitty.PUSH_TO_TALK = True
        calls = []
        original_push_to_talk = trinitty.Push_To_Talk
        trinitty.Push_To_Talk = lambda: calls.append("push") or "push"
        try:
            self.assertEqual("push", trinitty.Trinitty("WakeMe"))
        finally:
            trinitty.Push_To_Talk = original_push_to_talk

        self.assertEqual(["push"], calls)

    def test_push_to_talk_wakeme_records_and_sends_transcript(self):
        reset_command_state()
        reset_runtime_queues()
        trinitty.INTERPRETOR = False
        trinitty.PUSH_TO_TALK = True
        calls = []
        original_input = getattr(trinitty, "input", None)
        original_pyaudio = trinitty.pyaudio
        original_webrtcvad = trinitty.webrtcvad
        original_start = trinitty.Start_Thread_Record
        original_speech = trinitty.Speech_To_Text
        original_check = trinitty.Check_Transcript
        original_commandes = trinitty.Commandes
        original_to_gpt = trinitty.To_Gpt
        trinitty.input = lambda _prompt="": calls.append("input") or ""
        trinitty.pyaudio = SimpleNamespace()
        trinitty.webrtcvad = SimpleNamespace()
        trinitty.Start_Thread_Record = lambda: calls.append("start_record") or True
        trinitty.Speech_To_Text = lambda audio: calls.append(("speech", audio)) or ("t", "c", "w", "wc", "")
        trinitty.Check_Transcript = lambda *_args: calls.append("check") or ("bonjour", True)
        trinitty.Commandes = lambda text: calls.append(("cmd", text)) or False
        trinitty.To_Gpt = lambda text: calls.append(("gpt", text)) or "sent"
        trinitty.audio_datas.put("audio-bytes")
        try:
            self.assertIsNone(trinitty.Trinitty("WakeMe"))
        finally:
            if original_input is None:
                delattr(trinitty, "input")
            else:
                trinitty.input = original_input
            trinitty.pyaudio = original_pyaudio
            trinitty.webrtcvad = original_webrtcvad
            trinitty.Start_Thread_Record = original_start
            trinitty.Speech_To_Text = original_speech
            trinitty.Check_Transcript = original_check
            trinitty.Commandes = original_commandes
            trinitty.To_Gpt = original_to_gpt

        self.assertEqual(
            [
                "input",
                "start_record",
                ("speech", "audio-bytes"),
                "check",
                ("cmd", "bonjour"),
                ("gpt", "bonjour"),
            ],
            calls,
        )

    def test_wake_up_failure_switches_to_push_to_talk(self):
        reset_command_state()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_script_path = trinitty.SCRIPT_PATH
            original_saved_answer = getattr(trinitty, "SAVED_ANSWER", "")
            original_pvporcupine = trinitty.pvporcupine
            original_push_to_talk = trinitty.Push_To_Talk
            try:
                trinitty.SCRIPT_PATH = str(root)
                trinitty.SAVED_ANSWER = str(root / "local_sounds" / "saved_answer")
                trinitty.PUSH_TO_TALK = False
                trinitty.PICO_KEY = "pico"
                trinitty.Runtime_Errors = []
                trinitty.pvporcupine = SimpleNamespace(
                    create=lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("porcupine down"))
                )
                trinitty.Push_To_Talk = lambda: "push"

                self.assertEqual("push", trinitty.wake_up())
            finally:
                trinitty.SCRIPT_PATH = original_script_path
                trinitty.SAVED_ANSWER = original_saved_answer
                trinitty.pvporcupine = original_pvporcupine
                trinitty.Push_To_Talk = original_push_to_talk

        self.assertTrue(trinitty.PUSH_TO_TALK)
        self.assertEqual("wake_up", trinitty.Runtime_Errors[-1]["context"])

    def test_freegpt_does_not_loop_forever_when_all_providers_blacklisted(self):
        reset_runtime_queues()
        trinitty.SCRIPT_PATH = str(ROOT)
        trinitty.SAVED_ANSWER = str(ROOT / "local_sounds" / "saved_answer")
        trinitty.Providers_To_Use = ["g4f.Provider.Bad"]
        trinitty.Blacklisted = ["g4f.Provider.Bad"]
        trinitty.Current_Provider_Id = 0
        trinitty.GPT4FREE_RUNTIME_AVAILABLE = True
        trinitty.GPT4FREE_COOKIES_LOADED = True
        calls = []
        original_quit = trinitty.Quit
        original_play = trinitty.Play_Audio_File
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Quit = lambda _from_function=None: (_ for _ in ()).throw(AssertionError("Quit should not be called"))
        trinitty.Play_Audio_File = lambda *_args, **_kwargs: 0
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            started = time.monotonic()
            self.assertEqual(
                "sleep",
                trinitty.FreeGpt("question", check_history=False, save_last_sentence=False),
            )
            elapsed = time.monotonic() - started
        finally:
            trinitty.Quit = original_quit
            trinitty.Play_Audio_File = original_play
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertLess(elapsed, 1)
        self.assertEqual([("sleep", False)], calls)

    def test_freegpt_without_providers_does_not_exit(self):
        reset_runtime_queues()
        trinitty.SCRIPT_PATH = str(ROOT)
        trinitty.SAVED_ANSWER = str(ROOT / "local_sounds" / "saved_answer")
        trinitty.Providers_To_Use = []
        trinitty.Blacklisted = []
        trinitty.Current_Provider_Id = 0
        calls = []
        original_quit = trinitty.Quit
        original_play = trinitty.Play_Audio_File
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Quit = lambda _from_function=None: (_ for _ in ()).throw(AssertionError("Quit should not be called"))
        trinitty.Play_Audio_File = lambda path: calls.append(("play", path)) or 0
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual(
                "sleep",
                trinitty.FreeGpt("question", check_history=False, save_last_sentence=False),
            )
        finally:
            trinitty.Quit = original_quit
            trinitty.Play_Audio_File = original_play
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual(
            [
                ("play", str(ROOT / "local_sounds" / "errors" / "err_no_respons_allprovider.wav")),
                ("sleep", False),
            ],
            calls,
        )

    def test_freegpt_rotates_to_next_provider_after_failure(self):
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "local_sounds" / "providers").mkdir(parents=True)
            (root / "local_sounds" / "providers" / "Qwen.wav").write_bytes(b"")
            (root / "local_sounds" / "errors").mkdir(parents=True)
            (root / "saved_answer" / "saved_error").mkdir(parents=True)

            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(root / "saved_answer")
            trinitty.Providers_To_Use = ["g4f.Provider.Qwen", "g4f.Provider.PollinationsAI"]
            trinitty.Blacklisted = []
            trinitty.Current_Provider_Id = 0
            trinitty.GPT4FREE_RUNTIME_AVAILABLE = True
            trinitty.GPT4FREE_COOKIES_LOADED = True
            calls = []
            original_g4f = trinitty.g4f
            original_resolve = trinitty.Resolve_Gpt4free_Provider
            original_play = trinitty.Play_Audio_File
            original_tts = trinitty.Text_To_Speech

            def fake_create(model=None, provider=None, timeout=None, messages=None):
                calls.append(("create", model, provider, timeout, messages[0]["content"]))
                if provider == "Qwen":
                    raise RuntimeError("down")
                return "bonjour"

            trinitty.g4f = SimpleNamespace(
                models=SimpleNamespace(default="default-model"),
                ChatCompletion=SimpleNamespace(create=fake_create),
            )
            trinitty.Resolve_Gpt4free_Provider = lambda name: name.replace("g4f.Provider.", "")
            trinitty.Play_Audio_File = lambda path: calls.append(("play", path)) or 0
            trinitty.Text_To_Speech = lambda text, stayawake=False: calls.append(("tts", text, stayawake)) or "tts"
            try:
                self.assertEqual(
                    "tts",
                    trinitty.FreeGpt("question", check_history=False, save_last_sentence=False),
                )
            finally:
                trinitty.g4f = original_g4f
                trinitty.Resolve_Gpt4free_Provider = original_resolve
                trinitty.Play_Audio_File = original_play
                trinitty.Text_To_Speech = original_tts

        self.assertEqual(
            [
                ("play", calls[0][1]),
                ("create", "default-model", "Qwen", 10, "question"),
                ("play", str(root / "local_sounds" / "providers" / "Qwen.wav")),
                ("create", "default-model", "PollinationsAI", 10, "question"),
                ("tts", "bonjour", False),
            ],
            calls,
        )
        self.assertTrue(calls[0][1].startswith(str(root / "local_sounds" / "wait")))
        self.assertEqual(["g4f.Provider.Qwen"], trinitty.Blacklisted)
        self.assertEqual(0, trinitty.Current_Provider_Id)

    def test_freegpt_generates_missing_provider_audio_in_runtime_tmp(self):
        reset_runtime_queues()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "saved_answer" / "saved_error").mkdir(parents=True)
            trinitty.SCRIPT_PATH = str(root)
            trinitty.SAVED_ANSWER = str(root / "saved_answer")
            trinitty.Providers_To_Use = ["g4f.Provider.NewProvider", "g4f.Provider.PollinationsAI"]
            trinitty.Blacklisted = []
            trinitty.Current_Provider_Id = 0
            trinitty.GPT4FREE_RUNTIME_AVAILABLE = True
            trinitty.GPT4FREE_COOKIES_LOADED = True
            calls = []

            class FakeClient:
                def synthesize_speech(self, **_kwargs):
                    return SimpleNamespace(audio_content=b"wav")

            fake_tts = SimpleNamespace(
                TextToSpeechClient=lambda: FakeClient(),
                AudioConfig=lambda audio_encoding=None: SimpleNamespace(audio_encoding=audio_encoding),
                AudioEncoding=SimpleNamespace(LINEAR16="LINEAR16"),
                SynthesisInput=lambda text=None: SimpleNamespace(text=text),
                VoiceSelectionParams=lambda language_code=None, name=None: SimpleNamespace(
                    language_code=language_code,
                    name=name,
                ),
            )

            original_g4f = trinitty.g4f
            original_resolve = trinitty.Resolve_Gpt4free_Provider
            original_play = trinitty.Play_Audio_File
            original_tts_module = trinitty.tts
            original_text_to_speech = trinitty.Text_To_Speech

            def fake_create(provider=None, **_kwargs):
                calls.append(("create", provider))
                if provider == "NewProvider":
                    raise RuntimeError("down")
                return "bonjour"

            trinitty.g4f = SimpleNamespace(
                models=SimpleNamespace(default="default-model"),
                ChatCompletion=SimpleNamespace(create=fake_create),
            )
            trinitty.Resolve_Gpt4free_Provider = lambda name: name.replace("g4f.Provider.", "")
            trinitty.Play_Audio_File = lambda path: calls.append(("play", path)) or 0
            trinitty.tts = fake_tts
            trinitty.Text_To_Speech = lambda text, stayawake=False: calls.append(("tts", text, stayawake)) or "tts"
            try:
                self.assertEqual(
                    "tts",
                    trinitty.FreeGpt("question", check_history=False, save_last_sentence=False),
                )
            finally:
                trinitty.g4f = original_g4f
                trinitty.Resolve_Gpt4free_Provider = original_resolve
                trinitty.Play_Audio_File = original_play
                trinitty.tts = original_tts_module
                trinitty.Text_To_Speech = original_text_to_speech

            generated = root / "tmp" / "providers" / "NewProvider.wav"
            self.assertTrue(generated.exists())
            self.assertFalse((root / "local_sounds" / "providers" / "NewProvider.wav").exists())
            self.assertIn(("play", str(generated)), calls)
            self.assertEqual(["g4f.Provider.NewProvider"], trinitty.Blacklisted)


if __name__ == "__main__":
    unittest.main()
