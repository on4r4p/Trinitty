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
    trinitty.PLAYBACK_INTERRUPT_ENABLED = True
    trinitty.PLAYBACK_INTERRUPT_TIMEOUT = 30.0
    trinitty.COMMAND_CLASSIFIER_ENABLED = False
    trinitty.COMMAND_CLASSIFIER_THRESHOLD = 0.65
    trinitty.COMMAND_CLASSIFIER_MODEL_PATH = "datas/command_classifier.keras"
    trinitty.COMMAND_CLASSIFIER_MODEL = None
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
                self.assertTrue((user_root / "history").is_dir())
                self.assertTrue((user_root / "saved_answer" / "saved_error").is_dir())
                self.assertIn(
                    "OPENAI_API_KEY_FILE = keys/openai.key",
                    (user_root / "datas" / "conf.trinity").read_text(),
                )
                self.assertIn("Dossier utilisateur: %s" % user_root, output.getvalue())
                self.assertIn(
                    "Configuration modifiable: %s" % (user_root / "datas" / "conf.trinity"),
                    output.getvalue(),
                )

                openai_key = user_root / "keys" / "openai.key"
                user_conf = user_root / "datas" / "conf.trinity"
                openai_key.write_text("sk-existing\n")
                user_conf.write_text("OPENAI_MODEL = custom-user-model\n")
                with contextlib.redirect_stdout(io.StringIO()):
                    trinitty.Initialize_User_Data()
                self.assertEqual("sk-existing\n", openai_key.read_text())
                self.assertEqual("OPENAI_MODEL = custom-user-model\n", user_conf.read_text())
            finally:
                if original_home is None:
                    os.environ.pop("HOME", None)
                else:
                    os.environ["HOME"] = original_home

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

            self.assertEqual("OPENAI_MODEL = old-user-model\n", (user_root / "datas" / "conf.trinity").read_text())
            self.assertEqual("OPENAI_MODEL = old-user-model\n", legacy_conf.read_text())

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
        original_play = trinitty.Play_Audio_File
        original_sleep = trinitty.Go_Back_To_Sleep
        trinitty.Check_History = lambda _text: False
        trinitty.Openai_Gpt = lambda _text: ""
        trinitty.Play_Audio_File = lambda path: calls.append(("play", path)) or 0
        trinitty.Go_Back_To_Sleep = lambda go_trinitty=True: calls.append(("sleep", go_trinitty)) or "sleep"
        try:
            self.assertEqual("sleep", trinitty.To_Gpt("question"))
        finally:
            trinitty.Check_History = original_check_history
            trinitty.Openai_Gpt = original_openai
            trinitty.Play_Audio_File = original_play
            trinitty.Go_Back_To_Sleep = original_sleep

        self.assertEqual(
            [
                ("play", str(ROOT / "local_sounds" / "errors" / "err_no_respons_allprovider.wav")),
                ("sleep", False),
            ],
            calls,
        )

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
        original_refresh = trinitty.Refresh_Gpt4free_Providers_Config
        original_getconf = trinitty.GetConf
        original_check_servers = trinitty.Check_Free_Servers
        original_freegpt = trinitty.FreeGpt
        trinitty.Check_History = lambda _text: False
        trinitty.Openai_Gpt = lambda _text: ""
        trinitty.Refresh_Gpt4free_Providers_Config = lambda: calls.append("refresh") or False
        trinitty.GetConf = lambda: calls.append("getconf")
        trinitty.Check_Free_Servers = lambda: calls.append("check_servers") or ["g4f.Provider.Qwen"]
        trinitty.FreeGpt = lambda text, **_kwargs: calls.append(("freegpt", text)) or "freegpt"
        try:
            self.assertEqual("freegpt", trinitty.To_Gpt("question"))
        finally:
            trinitty.Check_History = original_check_history
            trinitty.Openai_Gpt = original_openai
            trinitty.Refresh_Gpt4free_Providers_Config = original_refresh
            trinitty.GetConf = original_getconf
            trinitty.Check_Free_Servers = original_check_servers
            trinitty.FreeGpt = original_freegpt

        self.assertEqual(["refresh", "getconf", "check_servers", ("freegpt", "question")], calls)
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
        original_github = trinitty.Github
        original_g4f = trinitty.g4f
        original_last_sha = getattr(trinitty, "LAST_SHA", "")
        original_saved_answer = getattr(trinitty, "SAVED_ANSWER", "")
        original_runtime_available = getattr(trinitty, "GPT4FREE_RUNTIME_AVAILABLE", None)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trinitty.SAVED_ANSWER = str(root / "saved_answer")
            trinitty.Runtime_Errors = []
            trinitty.LAST_SHA = "local-old-sha"

            class FakeRepo:
                def get_commits(self):
                    return [
                        SimpleNamespace(sha="remote-new-sha"),
                        SimpleNamespace(sha="remote-old-sha"),
                    ]

            class FakeGithub:
                def get_repo(self, _repo):
                    return FakeRepo()

            trinitty.Github = FakeGithub
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
                trinitty.Github = original_github
                trinitty.g4f = original_g4f
                trinitty.LAST_SHA = original_last_sha
                trinitty.SAVED_ANSWER = original_saved_answer
                trinitty.GPT4FREE_RUNTIME_AVAILABLE = original_runtime_available

        self.assertEqual("Check_Update", trinitty.Runtime_Errors[-1]["context"])
        self.assertIn("update available", trinitty.Runtime_Errors[-1]["error"])

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
                        "GPT4FREE_SERVERS_LIST = None",
                        "GPT4FREE_SERVERS_STATUS = None",
                    ]
                )
            )
            (datas / "conf.local.trinity").write_text(
                "SAVED_ANSWER = %s\nOPENAI_TIMEOUT = 7\n" % local_saved
            )

            trinitty.SCRIPT_PATH = str(root)
            trinitty.DEBUG = False
            trinitty.GPT4FREE_SERVERS_LIST = None
            trinitty.GPT4FREE_SERVERS_STATUS = "Active"
            trinitty.GetConf()

            self.assertEqual(str(local_saved), trinitty.SAVED_ANSWER)
            self.assertEqual(7.0, trinitty.OPENAI_TIMEOUT)
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
                        "GPT4FREE_SERVERS_STATUS = Active",
                    ]
                )
            )
            (user_datas / "conf.trinity").write_text(
                "OPENAI_MODEL = user-model\nOPENAI_TIMEOUT = 4\nGPT4FREE_SERVERS_STATUS = None\n"
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
        trinitty.input = lambda _prompt="": calls.append("input") or ""
        trinitty.Trinitty = lambda fname="WakeMe": calls.append(fname) or "speech"
        try:
            self.assertEqual("speech", trinitty.Push_To_Talk())
        finally:
            if original_input is None:
                delattr(trinitty, "input")
            else:
                trinitty.input = original_input
            trinitty.Trinitty = original_trinitty

        self.assertEqual(["input", "Speech_To_Text"], calls)

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
                ("create", "default-model", "Qwen", 10, "question"),
                ("play", str(root / "local_sounds" / "providers" / "Qwen.wav")),
                ("create", "default-model", "PollinationsAI", 10, "question"),
                ("tts", "bonjour", False),
            ],
            calls,
        )
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
