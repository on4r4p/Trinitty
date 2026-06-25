#!/usr/bin/python3

import csv
import base64
import html
import importlib
from importlib import metadata as importlib_metadata
import inspect
import json
import os
import random
import re
import runpy
import shlex
import signal
import site
import string
import struct
import subprocess
import sys
import time
import traceback
import unicodedata
from urllib.parse import parse_qs, quote_plus, unquote, urlparse
from urllib.request import urlopen

from difflib import SequenceMatcher

from datetime import datetime

from shutil import copy2, copyfile, move, which

from queue import Empty, Queue
from threading import Event, Thread, current_thread, main_thread
from contextlib import contextmanager

from itertools import product


OPTIONAL_DEPENDENCY_ERRORS = {}


NOMBRES = [
    "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
    "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf",
    "vingt", "vingt et un", "vingt-deux", "vingt-trois", "vingt-quatre", "vingt-cinq", "vingt-six",
    "vingt-sept", "vingt-huit", "vingt-neuf",
    "trente", "trente et un", "trente-deux", "trente-trois", "trente-quatre", "trente-cinq",
    "trente-six", "trente-sept", "trente-huit", "trente-neuf",
    "quarante", "quarante et un", "quarante-deux", "quarante-trois", "quarante-quatre",
    "quarante-cinq", "quarante-six", "quarante-sept", "quarante-huit", "quarante-neuf",
    "cinquante", "cinquante et un", "cinquante-deux", "cinquante-trois", "cinquante-quatre",
    "cinquante-cinq", "cinquante-six", "cinquante-sept", "cinquante-huit", "cinquante-neuf",
    "soixante", "soixante et un", "soixante-deux", "soixante-trois", "soixante-quatre",
    "soixante-cinq", "soixante-six", "soixante-sept", "soixante-huit", "soixante-neuf",
    "soixante-dix", "soixante et onze", "soixante-douze", "soixante-treize", "soixante-quatorze",
    "soixante-quinze", "soixante-seize", "soixante-dix-sept", "soixante-dix-huit",
    "soixante-dix-neuf",
    "quatre-vingts", "quatre-vingt-un", "quatre-vingt-deux", "quatre-vingt-trois",
    "quatre-vingt-quatre", "quatre-vingt-cinq", "quatre-vingt-six", "quatre-vingt-sept",
    "quatre-vingt-huit", "quatre-vingt-neuf",
    "quatre-vingt-dix", "quatre-vingt-onze", "quatre-vingt-douze", "quatre-vingt-treize",
    "quatre-vingt-quatorze", "quatre-vingt-quinze", "quatre-vingt-seize", "quatre-vingt-dix-sept",
    "quatre-vingt-dix-huit", "quatre-vingt-dix-neuf",
]

CENTAINES = [
    "cent", "deux cents", "trois cents", "quatre cents", "cinq cents",
    "six cents", "sept cents", "huit cents", "neuf cents",
]

MILLIERS = [
    "mille", "deux mille", "trois mille", "quatre mille", "cinq mille",
    "six mille", "sept mille", "huit mille", "neuf mille", "dix mille",
    "onze mille", "douze mille", "treize mille", "quatorze mille", "quinze mille",
    "seize mille", "dix-sept mille", "dix-huit mille", "dix-neuf mille",
    "vingt mille", "vingt-et-un mille", "vingt-deux mille", "vingt-trois mille",
]

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

APLAY_BIN = which("aplay") or "aplay"
PLAY_BIN = which("play") or "play"
USER_DATA_DIR_NAME = "Trinitty"
LEGACY_USER_DATA_DIR_NAME = "trinitty"
PYPI_PACKAGE_NAME = "trinitty"
PYPROJECT_VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)


def User_Data_Base_Path():
    return os.path.join(os.path.expanduser("~"), ".local", "share")


def User_Data_Root():
    base_path = User_Data_Base_Path()
    canonical_path = os.path.join(base_path, USER_DATA_DIR_NAME)
    legacy_path = os.path.join(base_path, LEGACY_USER_DATA_DIR_NAME)
    if os.path.exists(legacy_path) and not os.path.exists(canonical_path):
        return legacy_path
    return canonical_path


def Legacy_User_Data_Root():
    return os.path.join(User_Data_Base_Path(), LEGACY_USER_DATA_DIR_NAME)


def Default_Script_Path():
    module_path = os.path.dirname(__file__)
    if os.path.exists(os.path.join(module_path, "datas", "conf.trinity")):
        return module_path
    for base_path in (sys.prefix, site.getuserbase()):
        packaged_path = os.path.join(base_path, "trinitty")
        if os.path.exists(os.path.join(packaged_path, "datas", "conf.trinity")):
            return packaged_path
    return module_path


def User_Data_Path(*parts):
    return os.path.join(User_Data_Root(), *parts)


def User_Data_Path_Candidates(*parts):
    candidates = [
        os.path.join(User_Data_Root(), *parts),
        os.path.join(Legacy_User_Data_Root(), *parts),
    ]
    return list(dict.fromkeys(candidates))


def Config_File_Candidates(relative_path):
    relative_path = str(relative_path or "").strip()
    if not relative_path:
        return []
    relative_path = os.path.expandvars(os.path.expanduser(relative_path))
    if os.path.isabs(relative_path):
        return [relative_path]
    script_path = globals().get("SCRIPT_PATH", Default_Script_Path())
    return [os.path.join(script_path, relative_path), *User_Data_Path_Candidates(relative_path)]


def Existing_Config_File(relative_path):
    for candidate in Config_File_Candidates(relative_path):
        if os.path.exists(candidate):
            return candidate
    return ""


def Packaged_Config_File():
    return os.path.join(globals().get("SCRIPT_PATH", Default_Script_Path()), "datas", "conf.trinity")


def Packaged_Config_Text():
    try:
        with open(Packaged_Config_File()) as f:
            return f.read()
    except OSError as e:
        Log_Error("Packaged_Config_Text", e)
        return ""


def Default_User_Launcher_Path():
    return os.path.join(os.path.expanduser("~"), ".local", "bin", "trinitty")


def Install_User_Launcher(launcher_path=None, python_bin=None):
    launcher_path = launcher_path or Default_User_Launcher_Path()
    python_bin = python_bin or sys.executable
    os.makedirs(os.path.dirname(launcher_path), exist_ok=True)
    launcher = """#!/usr/bin/env bash
set -Eeuo pipefail

export PYTHONNOUSERSITE=1
unset PYTHONPATH

exec %s -m trinitty "$@"
""" % shlex.quote(os.path.abspath(python_bin))
    with open(launcher_path, "w") as f:
        f.write(launcher)
    os.chmod(launcher_path, 0o700)
    print("\n-Trinitty:Lanceur installé: %s" % launcher_path)
    print("-Trinitty:Commande cible: %s -m trinitty" % os.path.abspath(python_bin))
    if os.path.dirname(launcher_path) not in os.environ.get("PATH", "").split(os.pathsep):
        print("-Trinitty:Ajoutez ce dossier au PATH si la commande trinitty n'est pas trouvée.")
    return launcher_path


def Trinitty_Help_Text():
    user_root = User_Data_Root()
    user_conf = os.path.join(user_root, "datas", "conf.trinity")
    keys_dir = os.path.join(user_root, "keys")
    installer = Install_Dependencies_User_Path(user_root)
    package_conf = Packaged_Config_File()

    return """Trinitty - aide

Usage terminal:
  trinitty                       Lance l'assistant vocal.
  trinitty -h, trinitty --help   Affiche cette aide.
  trinitty --check-install       Vérifie/installe les dépendances locales.
  trinitty --dependency-help     Affiche les commandes de réparation des dépendances.
  trinitty --install-launcher    Crée le lanceur propre dans ~/.local/bin/trinitty.

Commandes vocales utiles:
  "affiche ton aide"                         Affiche cette aide et joue l'aide audio.
  "fais une recherche internet sur ..."      Recherche sur le web.
  "fais une recherche wikipedia sur ..."     Recherche sur Wikipedia.
  "affiche l'historique"                     Affiche les échanges enregistrés.
  "cherche dans l'historique ..."            Recherche dans les anciens échanges.
  "répète"                                   Relit la dernière réponse.
  "invite de commande"                       Passe en saisie clavier.
  "quitte ton programme"                     Arrête Trinitty.

Avec les résultats web, Wikipedia ou historique:
  "lis le résultat numéro 3"      Lit le résultat sélectionné.
  "ouvre le résultat numéro 3"    Ouvre le lien du résultat sélectionné.
  "lis les trois premiers"        Lit plusieurs résultats.
  "choisis au hasard"             Sélectionne un résultat au hasard.
  "attends"                       Laisse les résultats affichés.
  "quitte"                        Quitte l'écran de résultats.

Configuration:
  Dossier utilisateur: %s
  Configuration modifiable: %s
  Configuration fournie avec le package: %s
  Dossier des clés: %s
  Installateur de dépendances: %s

Les fichiers existants dans le dossier utilisateur ne sont pas écrasés.
""" % (user_root, user_conf, package_conf, keys_dir, installer)


def Trinitty_Help(play_audio=True):
    print(Trinitty_Help_Text())
    if play_audio:
        help_wav = os.path.join(globals().get("SCRIPT_PATH", Default_Script_Path()), "local_sounds", "saved_answer", "help.wav")
        if os.path.exists(help_wav):
            Play_Audio_File(help_wav)
    return True


def Handle_Utility_Args():
    if len(sys.argv) < 2:
        return False
    command = sys.argv[1]
    if command in ("-h", "--help", "help"):
        print(Trinitty_Help_Text())
        return True
    if command == "--check-install":
        root = Initialize_User_Data()
        Auto_Run_Dependency_Installer(root, force=True)
        return True
    if command == "--install-launcher":
        Install_User_Launcher()
        return True
    if command == "--dependency-help":
        print(Dependency_Install_Help())
        return True
    return False


def Write_File_If_Missing(filepath, content, mode=None):
    if os.path.exists(filepath):
        return False
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w") as f:
        f.write(content)
    if mode is not None:
        try:
            os.chmod(filepath, mode)
        except OSError:
            pass
    return True


def Install_Dependencies_Source_Candidates(filename="install_dependencies.sh"):
    return [
        os.path.join(os.getcwd(), filename),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),
        os.path.join(Default_Script_Path(), filename),
    ]


def Install_Dependencies_User_Path(root=None):
    root = root or User_Data_Root()
    return os.path.join(root, "install_dependencies.sh")


def Install_Dependencies_Requirements_User_Path(root=None):
    root = root or User_Data_Root()
    return os.path.join(root, "requirements.txt")


def Install_Dependencies_Script_Path():
    candidates = [
        Install_Dependencies_User_Path(),
        *Install_Dependencies_Source_Candidates(),
    ]
    for candidate in dict.fromkeys(candidates):
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return ""


def Initialize_User_Installer(root=None):
    root = root or User_Data_Root()
    copied = []
    files = [
        ("install_dependencies.sh", Install_Dependencies_User_Path(root), 0o700),
        ("requirements.txt", Install_Dependencies_Requirements_User_Path(root), 0o600),
    ]

    for filename, destination, mode in files:
        if os.path.exists(destination):
            continue

        for source in dict.fromkeys(Install_Dependencies_Source_Candidates(filename)):
            if os.path.isfile(source) and os.path.abspath(source) != os.path.abspath(destination):
                os.makedirs(os.path.dirname(destination), exist_ok=True)
                copy2(source, destination)
                try:
                    os.chmod(destination, mode)
                except OSError:
                    pass
                copied.append(destination)
                break

    return copied


def Dependency_Installer_Is_User_Copy(script_path=None, root=None):
    script_path = script_path or Install_Dependencies_Script_Path()
    root = root or User_Data_Root()
    try:
        return os.path.abspath(script_path) == os.path.abspath(Install_Dependencies_User_Path(root))
    except Exception:
        return False


def Dependency_Installer_Command(script_path=None, root=None):
    script_path = script_path or Install_Dependencies_Script_Path()
    if not script_path:
        return []
    if Dependency_Installer_Is_User_Copy(script_path, root):
        return [script_path, "--system", "--no-venv", "--no-dev-tools", "--no-launcher"]
    return [script_path, "--system", "--venv"]


def Dependency_Installer_Stamp_Path(root=None):
    root = root or User_Data_Root()
    return os.path.join(root, ".install_dependencies.version")


def Auto_Dependency_Installer_Enabled():
    if os.environ.get("TRINITTY_SKIP_AUTO_INSTALL"):
        return False
    value = os.environ.get("TRINITTY_AUTO_INSTALL_DEPENDENCIES", "0").strip().lower()
    return value in ["1", "true", "yes", "on"]


def Current_Trinitty_Version_For_Installer():
    try:
        version = Installed_Trinitty_Version()
    except Exception:
        version = ""
    return str(version or "unknown").strip()


def Last_Dependency_Installer_Version(root=None):
    stamp_path = Dependency_Installer_Stamp_Path(root)
    try:
        with open(stamp_path) as f:
            return f.read().strip()
    except OSError:
        return ""


def Mark_Dependency_Installer_Version(root=None, version=None):
    root = root or User_Data_Root()
    version = version or Current_Trinitty_Version_For_Installer()
    stamp_path = Dependency_Installer_Stamp_Path(root)
    os.makedirs(os.path.dirname(stamp_path), exist_ok=True)
    with open(stamp_path, "w") as f:
        f.write(str(version).strip() + "\n")


def Auto_Run_Dependency_Installer(root=None, force=False):
    root = root or User_Data_Root()
    if not force and not Auto_Dependency_Installer_Enabled():
        PRINT("\n-Trinitty:Installation automatique des dépendances désactivée.")
        return False

    Initialize_User_Installer(root)
    version = Current_Trinitty_Version_For_Installer()
    if Last_Dependency_Installer_Version(root) == version:
        PRINT("\n-Trinitty:Dépendances déjà vérifiées pour Trinitty %s." % version)
        return False

    script_path = Install_Dependencies_User_Path(root)
    if not os.path.isfile(script_path):
        script_path = Install_Dependencies_Script_Path()
    command = Dependency_Installer_Command(script_path, root)
    if not command:
        print("\n-Trinitty:Warning:install_dependencies.sh introuvable; dépendances non vérifiées.")
        return False

    if force:
        print("\n-Trinitty:Vérification/installation des dépendances pour Trinitty %s." % version)
    else:
        print("\n-Trinitty:Vérification/installation automatique des dépendances pour Trinitty %s." % version)
    print("-Trinitty:Commande: %s" % " ".join(shlex.quote(part) for part in command))

    env = os.environ.copy()
    env["PYTHON"] = sys.executable
    env["PYTHONNOUSERSITE"] = "1"
    try:
        result = subprocess.run(command, cwd=root, env=env, check=False)
    except Exception as e:
        print("\n-Trinitty:Warning:install_dependencies.sh n'a pas pu démarrer:%s" % str(e))
        Log_Error("Auto_Run_Dependency_Installer", e)
        return False

    if result.returncode == 0:
        Mark_Dependency_Installer_Version(root, version)
        print("\n-Trinitty:Dépendances vérifiées pour Trinitty %s." % version)
        return True

    print("\n-Trinitty:Warning:install_dependencies.sh a échoué avec le code %s." % result.returncode)
    if force:
        print("-Trinitty:Relancez trinitty --check-install après correction.")
    else:
        print("-Trinitty:Le prochain lancement réessaiera. Pour désactiver: TRINITTY_SKIP_AUTO_INSTALL=1")
    Log_Error("Auto_Run_Dependency_Installer", "exit code %s" % result.returncode)
    return False


def Dependency_Install_Help(package_name=None):
    script_path = Install_Dependencies_Script_Path()
    package_label = package_name or "la dépendance manquante"
    if script_path:
        command = " ".join(shlex.quote(part) for part in Dependency_Installer_Command(script_path))
        return (
            "Pour installer %s, utilisez ce chemin exact:\n"
            "  %s\n"
        ) % (package_label, command)

    return (
        "Aucun install_dependencies.sh n'a été trouvé dans cette installation PyPI.\n"
        "Depuis un virtualenv Raspberry Pi existant, utilisez plutôt:\n"
        "  source ~/venvs/trinitty/bin/activate\n"
        "  export PYTHONNOUSERSITE=1\n"
        "  sudo apt-get install -y python3-pyaudio alsa-utils sox libsox-fmt-all\n"
        "  python -m pip install -U --no-cache-dir trinitty google-cloud-speech grpcio grpcio-status google-api-core protobuf\n"
        "\n"
        "Si vous utilisez le dépôt Git, lancez le script depuis son chemin absolu, par exemple:\n"
        "  /chemin/vers/Trinitty/install_dependencies.sh --system --venv\n"
    )


def Dependency_Install_Help_Summary(package_name=None):
    script_path = Install_Dependencies_Script_Path()
    if script_path:
        command = " ".join(shlex.quote(part) for part in Dependency_Installer_Command(script_path))
        return "Run: %s" % command
    return "Run: trinitty --dependency-help"


def Config_Keys_From_Text(text):
    keys = []
    for line in str(text or "").splitlines():
        key, _value = Config_Option_Value(line)
        if key and key not in keys:
            keys.append(key)
    return keys


def Append_Missing_User_Config_Options(user_conf):
    if not os.path.exists(user_conf):
        return False

    packaged_text = Packaged_Config_Text()
    if not packaged_text:
        return False

    with open(user_conf) as f:
        user_text = f.read()

    existing_keys = set(Config_Keys_From_Text(user_text))
    missing_lines = []
    for line in packaged_text.splitlines():
        key, _value = Config_Option_Value(line)
        if key and key not in existing_keys:
            missing_lines.append(line)
            existing_keys.add(key)

    if not missing_lines:
        return False

    with open(user_conf, "a") as f:
        if user_text and not user_text.endswith("\n"):
            f.write("\n")
        f.write("\n# Variables ajoutees depuis la configuration package sans remplacer les valeurs existantes.\n")
        for line in missing_lines:
            f.write(line + "\n")
    return True


def Migrate_User_Config_Defaults(user_conf):
    if not os.path.exists(user_conf):
        return False

    old_playback_interrupt_defaults = {
        "PLAYBACK_INTERRUPT_ENABLED = True #True or False - listen for stop command while speaking",
        "PLAYBACK_INTERRUPT_ENABLED = True # True or False - listen for stop command while speaking",
    }
    new_playback_interrupt_default = (
        "PLAYBACK_INTERRUPT_ENABLED = False "
        "#True records during playback to listen for stop commands"
    )

    with open(user_conf) as f:
        lines = f.readlines()

    changed = False
    migrated_lines = []
    for line in lines:
        newline = "\n" if line.endswith("\n") else ""
        stripped = line.strip()
        if stripped in old_playback_interrupt_defaults:
            migrated_lines.append(new_playback_interrupt_default + newline)
            changed = True
        else:
            migrated_lines.append(line)

    if not changed:
        return False

    with open(user_conf, "w") as f:
        f.writelines(migrated_lines)
    return True


def Initialize_User_Data():
    root = User_Data_Root()
    created = []
    for dirname in [
        "datas",
        "keys",
        "history",
        "tmp",
        "g4f_cookies",
        os.path.join("saved_answer", "saved_error"),
    ]:
        path = os.path.join(root, dirname)
        if not os.path.isdir(path):
            os.makedirs(path, exist_ok=True)
            created.append(path)

    user_conf = os.path.join(root, "datas", "conf.trinity")
    legacy_user_conf = os.path.join(root, "datas", "conf.local.trinity")
    if not os.path.exists(user_conf) and os.path.exists(legacy_user_conf):
        os.makedirs(os.path.dirname(user_conf), exist_ok=True)
        copy2(legacy_user_conf, user_conf)
        created.append(user_conf)
    elif Write_File_If_Missing(user_conf, User_Config_Template()):
        created.append(user_conf)
    if Append_Missing_User_Config_Options(user_conf):
        created.append(user_conf)
    if Migrate_User_Config_Defaults(user_conf):
        created.append(user_conf)

    openai_key = os.path.join(root, "keys", "openai.key")
    if Write_File_If_Missing(openai_key, "# Collez la cle OpenAI ici, sans guillemets.\n", mode=0o600):
        created.append(openai_key)

    keys_readme = os.path.join(root, "keys", "README.txt")
    if Write_File_If_Missing(keys_readme, User_Keys_Readme_Template()):
        created.append(keys_readme)

    created.extend(Initialize_User_Installer(root))

    if created:
        print("\n-Trinitty:Configuration utilisateur initialisée dans %s" % root)
    print("\n-Trinitty:Dossier utilisateur: %s" % root)
    print("-Trinitty:Configuration package: %s" % Packaged_Config_File())
    print("-Trinitty:Configuration modifiable: %s" % user_conf)
    return root


def User_Config_Template():
    packaged_config = Packaged_Config_Text().rstrip()
    if not packaged_config:
        packaged_config = "SAVED_ANSWER = default\nOPENAI_ENABLED = True\nOPENAI_API_KEY_FILE = keys/openai.key"
    return """# Overrides locaux de Trinitty.
# Ce fichier est lu apres la configuration fournie avec le package.
# Configuration fournie avec le package:
# %s
# Les valeurs ci-dessous remplacent celles du fichier ci-dessus.
# Les fichiers existants ne sont pas ecrases par Trinitty.

%s
""" % (Packaged_Config_File(), packaged_config)


def User_Keys_Readme_Template():
    return """Fichiers de cles reconnus par Trinitty:

openai.key                 cle API OpenAI, une seule ligne, sans guillemets
pico.key                   cle Picovoice/Porcupine pour le wake word
detectlanguage.key          cle detectlanguage.com
google_translate.key        cle Google Translate API
google_search.key           cle Google Custom Search API
google_search_engine.id     identifiant du moteur Google Custom Search
google_adc.json             credentials Google Cloud ADC

Ne versionnez pas ce dossier.
"""


def Writable_Dir_From_Candidates(candidates):
    for candidate in candidates:
        test_file = os.path.join(candidate, ".trinitty-write-test")
        try:
            os.makedirs(candidate, exist_ok=True)
            with open(test_file, "w") as f:
                f.write("")
            os.remove(test_file)
            return candidate
        except Exception:
            try:
                if os.path.exists(test_file):
                    os.remove(test_file)
            except OSError:
                continue
            continue

    return candidates[0]


def Writable_Runtime_Dir(dirname):
    script_path = globals().get("SCRIPT_PATH", Default_Script_Path())
    return Writable_Dir_From_Candidates([
        os.path.join(script_path, dirname),
        User_Data_Path(dirname),
    ])


def Runtime_Tmp_Path(*parts):
    return os.path.join(Writable_Runtime_Dir("tmp"), *parts)


def Local_Sound_Path(*parts):
    script_path = globals().get("SCRIPT_PATH", Default_Script_Path())
    return os.path.join(script_path, "local_sounds", *parts)


def Non_Crypto_Randint(start, end):
    return random.randint(start, end)  # noqa: S311 - used only for UI/audio variation, not security.


def Non_Crypto_Choice(values):
    return random.choice(values)  # noqa: S311 - used only for UI/audio variation, not security.


def Non_Crypto_Token(length, alphabet=None):
    alphabet = alphabet or (string.ascii_letters + string.digits)
    return "".join(random.choice(alphabet) for _ in range(length))  # noqa: S311 - used for temporary filenames only.


class MissingDependency:
    def __init__(self, import_name, package_name=None, error=None):
        self.import_name = import_name
        self.package_name = package_name or import_name
        self.error = error

    def _raise(self):
        message = "Optional dependency '%s' is unavailable." % self.package_name
        if self.error:
            message += " Import error: %s" % self.error
        message += " %s." % Dependency_Install_Help_Summary(self.package_name)
        raise ModuleNotFoundError(message) from self.error

    def __getattr__(self, name):
        self._raise()

    def __call__(self, *_args, **_kwargs):
        self._raise()

    def __bool__(self):
        return False


class LazyOptionalModule:
    def __init__(self, import_name, package_name=None):
        self.import_name = import_name
        self.package_name = package_name or import_name
        self._module = None
        self._missing = None

    def _load(self):
        if self._module is not None:
            return self._module
        if self._missing is not None:
            self._missing._raise()

        try:
            self._module = importlib.import_module(self.import_name)
        except Exception as e:
            OPTIONAL_DEPENDENCY_ERRORS[self.import_name] = e
            self._missing = MissingDependency(self.import_name, self.package_name, e)
            self._missing._raise()
        return self._module

    def is_available(self):
        if self._module is not None:
            return True
        if self._missing is not None:
            return False
        try:
            self._load()
        except ModuleNotFoundError:
            return False
        return True

    def __getattr__(self, name):
        return getattr(self._load(), name)

    def __bool__(self):
        return self.is_available()


class LazyOptionalAttribute:
    def __init__(self, module, attr_name, package_name=None):
        self.module = module
        self.attr_name = attr_name
        self.package_name = package_name or attr_name
        self._attribute = None
        self._missing = None

    def _load(self):
        if self._attribute is not None:
            return self._attribute
        if self._missing is not None:
            self._missing._raise()

        try:
            self._attribute = getattr(self.module, self.attr_name)
        except Exception as e:
            OPTIONAL_DEPENDENCY_ERRORS[self.attr_name] = e
            self._missing = MissingDependency(self.attr_name, self.package_name, e)
            self._missing._raise()
        return self._attribute

    def is_available(self):
        if self._attribute is not None:
            return True
        if self._missing is not None:
            return False
        try:
            self._load()
        except ModuleNotFoundError:
            return False
        return True

    def __call__(self, *args, **kwargs):
        return self._load()(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._load(), name)

    def __bool__(self):
        return self.is_available()


def Optional_Import(import_name, package_name=None):
    return LazyOptionalModule(import_name, package_name)


def Optional_Attribute(module, attr_name, package_name=None):
    if isinstance(module, MissingDependency):
        return MissingDependency(module.import_name, package_name or module.package_name, module.error)
    if isinstance(module, LazyOptionalModule):
        return LazyOptionalAttribute(module, attr_name, package_name)
    return LazyOptionalAttribute(module, attr_name, package_name)


def Dependency_Available(module):
    if isinstance(module, MissingDependency):
        return False
    if isinstance(module, (LazyOptionalModule, LazyOptionalAttribute)):
        return module.is_available()
    return True


def Subprocess_Returncode_Label(returncode):
    if returncode is None:
        return "no return code"
    if returncode < 0:
        signal_number = -returncode
        try:
            signal_name = signal.Signals(signal_number).name
        except ValueError:
            signal_name = "signal"
        return "%s %s" % (signal_name, signal_number)
    return "exit code %s" % returncode


def Ensure_Gpt4free_Runtime_Available():
    global GPT4FREE_RUNTIME_AVAILABLE

    cached = globals().get("GPT4FREE_RUNTIME_AVAILABLE", None)
    if cached is not None:
        return cached

    try:
        probe = subprocess.run(
            [sys.executable, "-c", "import g4f\nimport g4f.cookies\n"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
            check=False,
        )
    except Exception as e:
        GPT4FREE_RUNTIME_AVAILABLE = False
        print("\n-Trinitty:Warning:gpt4free indisponible, fallback désactivé:%s" % str(e))
        return False

    if probe.returncode != 0:
        details = (probe.stderr or probe.stdout or "").strip().splitlines()
        message = Subprocess_Returncode_Label(probe.returncode)
        if details:
            message = "%s: %s" % (message, details[-1])
        GPT4FREE_RUNTIME_AVAILABLE = False
        print("\n-Trinitty:Warning:gpt4free indisponible, fallback désactivé:%s" % message)
        return False

    GPT4FREE_RUNTIME_AVAILABLE = True
    return True


g4f = Optional_Import("g4f")
pyaudio = Optional_Import("pyaudio")
pvporcupine = Optional_Import("pvporcupine")
webrtcvad = Optional_Import("webrtcvad", "webrtcvad-wheels")
googlesearch = Optional_Import("googlesearch", "googlesearch-python")
requests = Optional_Import("requests")
sox = Optional_Import("sox")
spacy = Optional_Import("spacy")
detectlanguage = Optional_Import("detectlanguage")
wikipedia = Optional_Import("wikipedia")
tts = Optional_Import("google.cloud.texttospeech", "google-cloud-texttospeech")
speech = Optional_Import("google.cloud.speech_v1p1beta1", "google-cloud-speech")
language_v1 = Optional_Import("google.cloud.language_v1", "google-cloud-language")
translate_v2 = Optional_Import("google.cloud.translate_v2", "google-cloud-translate")
deep_translator = Optional_Import("deep_translator", "deep-translator")
GoogleTranslator = Optional_Attribute(deep_translator, "GoogleTranslator", "deep-translator")
g4f_cookies = Optional_Import("g4f.cookies", "g4f")
set_cookies_dir = Optional_Attribute(g4f_cookies, "set_cookies_dir", "g4f")
read_cookie_files = Optional_Attribute(g4f_cookies, "read_cookie_files", "g4f")
openai_module = Optional_Import("openai")
OpenAI = Optional_Attribute(openai_module, "OpenAI", "openai")
tensorflow = Optional_Import("tensorflow")
nltk_module = Optional_Import("nltk")
nltk_corpus = Optional_Import("nltk.corpus", "nltk")
nltk_tokenize = Optional_Import("nltk.tokenize", "nltk")
nltk_stem = Optional_Import("nltk.stem", "nltk")
stopwords = Optional_Attribute(nltk_corpus, "stopwords", "nltk")
wordnet = Optional_Attribute(nltk_corpus, "wordnet", "nltk")
word_tokenize = Optional_Attribute(nltk_tokenize, "word_tokenize", "nltk")
WordNetLemmatizer = Optional_Attribute(nltk_stem, "WordNetLemmatizer", "nltk")
pos_tag = Optional_Attribute(nltk_module, "pos_tag", "nltk")
urlextract_module = Optional_Import("urlextract")
URLExtract = Optional_Attribute(urlextract_module, "URLExtract", "urlextract")
bs4_module = Optional_Import("bs4", "beautifulsoup4")
BeautifulSoup = Optional_Attribute(bs4_module, "BeautifulSoup", "beautifulsoup4")
github_module = Optional_Import("github", "PyGithub")
Github = Optional_Attribute(github_module, "Github", "PyGithub")
unidecode_module = Optional_Import("unidecode", "Unidecode")
unidecode = Optional_Attribute(unidecode_module, "unidecode", "Unidecode")

g4f_debug = Optional_Import("g4f.debug", "g4f")


@contextmanager
def ignoreStderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


def Configure_Default_Google_Credentials():
    env_name = "GOOGLE_APPLICATION_CREDENTIALS"
    credential_candidates = [
        os.path.join(Default_Script_Path(), "keys", "google_adc.json"),
        *User_Data_Path_Candidates("keys", "google_adc.json"),
    ]
    for credentials_path in credential_candidates:
        if not os.environ.get(env_name) and os.path.exists(credentials_path):
            os.environ[env_name] = credentials_path
            break


Configure_Default_Google_Credentials()


def signal_handler(_sig, _frame):
    Xcb_Fix("set")
    sys.exit(0)

def signal_ctrlc(_sig, _frame):
    Xcb_Fix("set")
    return Quit()


def Debug_Log_File():
    log_dir = User_Data_Path("logs")
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError:
        log_dir = os.path.join(globals().get("SCRIPT_PATH", Default_Script_Path()), "tmp")
        os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "trinitty-debug-%s.log" % datetime.now().strftime("%Y%m%d"))


def Debug_Log(message, other=None):
    if not globals().get("DEBUG", False):
        return False
    if other is not None:
        message = "%s %s" % (message, other)
    try:
        with open(Debug_Log_File(), "a+", encoding="utf-8") as f:
            f.write(
                "[%s] pid=%s thread=%s %s\n"
                % (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                    os.getpid(),
                    current_thread().name,
                    str(message),
                )
            )
        return True
    except Exception as e:
        print("\n-Trinitty:Erreur dans la fonction Debug_Log:", str(e), file=sys.stderr)
        return False


def PRINT(txt, other=None):
    tmp_txt = txt
    #   print("\n-Trinitty:Dans la fonction PRINT().")
    #   print("\n-Trinitty:other:",other)
    try:
        if globals().get("DEBUG", False):
            if other is not None:
                tmp_txt = str(txt) + " " + str(other)
                print(tmp_txt)
            else:
                print(tmp_txt)
            Debug_Log(tmp_txt)
    except Exception as e:
        print("\n-Trinitty:Erreur dans la fonction PRINT:", str(e))


QUEUE_MISSING = object()
WAIT_FOR_TIMEOUT = 30.0
WAIT_FOR_POLL_INTERVAL = 0.05
PLAYBACK_POLL_INTERVAL = 0.05
PLAYBACK_INTERRUPT_TIMEOUT = 30.0
PLAYBACK_INTERRUPT_ENABLED = False
COMMAND_CLASSIFIER_ENABLED = False
COMMAND_CLASSIFIER_THRESHOLD = 0.65
COMMAND_CLASSIFIER_MODEL_PATH = "datas/command_classifier.keras"
COMMAND_CLASSIFIER_MODEL = None
STT_TRANSCRIPT_CONFIDENCE_MIN = 0.7
STT_WORD_CONFIDENCE_MIN = 0.6
STT_AVG_WORD_CONFIDENCE_MIN = 0.65
GOOGLE_STT_TIMEOUT = 20.0
GOOGLE_LANGUAGE_TIMEOUT = 8.0
HISTORY_CLASSIFICATION_ENABLED = True
RESULTS_HUB_MAX_ATTEMPTS = 2
RESULTS_HUB_CONTINUE = object()
WAIT_TIMEOUT = object()
GPT4FREE_COOKIES_LOADED = False
GPT4FREE_RUNTIME_AVAILABLE = None


def Queue_Get_Optional(queue_obj, timeout=0.2, default=QUEUE_MISSING):
    try:
        return queue_obj.get(timeout=timeout)
    except Empty:
        return default


def Queue_Drain(queue_obj):
    drained = 0
    while True:
        try:
            queue_obj.get_nowait()
            drained += 1
        except Empty:
            break
    return drained


def Audio_Input_Available():
    missing = []
    if not Dependency_Available(pyaudio):
        missing.append("pyaudio")
    if not Dependency_Available(webrtcvad):
        missing.append("webrtcvad-wheels")

    if not missing:
        return True

    message = "Entrée audio indisponible. Dépendances manquantes: %s" % ", ".join(missing)
    print("\n-Trinitty:Error:%s" % message)
    print(
        "-Trinitty:Sur Raspberry, installer python3-pyaudio puis recréer le venv avec "
        "`python3 -m venv --system-site-packages ~/venvs/trinitty`."
    )
    Log_Error("Audio_Input_Available", message)
    return False


def Stop_Recording():
    try:
        Queue_Drain(record_on)
    except NameError:
        return


def PicoLoadKeys():
    PRINT("\n-Trinitty:Dans fonction PicoLoadKeys")
    key_path = Existing_Config_File("keys/pico.key")
    if key_path:
        with open(key_path) as k:
            PICO_KEY = k.read()
            PICO_KEY = PICO_KEY.strip()
        if not PICO_KEY.endswith("=="):
            print("\n-Trinitty:-Wrong Pico Api key.")
            return None
        else:
            return PICO_KEY
    else:
        print("\n-Trinitty:-keys/pico.key doesn't exist.")
        return None

def DetectLanguageLoadKeys():
    PRINT("\n-Trinitty:Dans fonction DetectLanguageLoadKeys")
    key_path = Existing_Config_File("keys/detectlanguage.key")
    if key_path:
        with open(key_path) as k:
            DLANG_KEY = k.read()
            DLANG_KEY = DLANG_KEY.strip()
        if len(DLANG_KEY) != 32:
            print("\n-Trinitty:-Wrong DetectLanguage Api key.")
            return None
        else:
            return DLANG_KEY
    else:
        print("\n-Trinitty:-keys/detectlanguage.key doesn't exist.")
        #sys.exit()
        return None

def GoogleLoadKeys():
    PRINT("\n-Trinitty:Dans fonction GoogleLoadKeys")

    GOOGLE_KEY = ""
    GOOGLE_ENGINE = ""
    GOOGLE_TRANSLATE = ""

    google_translate_path = Existing_Config_File("keys/google_translate.key")
    if google_translate_path:
        with open(google_translate_path) as k:
            GOOGLE_TRANSLATE = k.read()
            GOOGLE_TRANSLATE = GOOGLE_TRANSLATE.strip()
        if len(GOOGLE_TRANSLATE) != 39:
            print("\n-Trinitty:-Wrong Google Translate Api key (len).")
            GOOGLE_TRANSLATE = ""
    else:
        print("\n-Trinitty:-keys/google_translate.key doesn't exist.")


    google_search_path = Existing_Config_File("keys/google_search.key")
    if google_search_path:
        with open(google_search_path) as k:
            GOOGLE_KEY = k.read()
            GOOGLE_KEY = GOOGLE_KEY.strip()
        if len(GOOGLE_KEY) != 39:
            print("\n-Trinitty:-Wrong Google Api key (len).")
            GOOGLE_KEY = ""
    else:
        print("\n-Trinitty:-keys/google_search.key doesn't exist.")

    google_engine_path = Existing_Config_File("keys/google_search_engine.id")
    if google_engine_path:
        with open(google_engine_path) as k:
            GOOGLE_ENGINE = k.read()
            GOOGLE_ENGINE = GOOGLE_ENGINE.strip()
        if len(GOOGLE_ENGINE) != 17:
            print("\n-Trinitty:-Wrong Google engine id (len).")
            GOOGLE_ENGINE = ""
    else:
        print("\n-Trinitty:-keys/google_search_engine.id doesn't exist.")

    return (GOOGLE_KEY, GOOGLE_ENGINE,GOOGLE_TRANSLATE)


def parse_response(data):

    PRINT("\n-Trinitty:Original Data before parse:\n", data)

    input_lang = None

    data = html.unescape(data)
    data = re.sub(r"\s*>\s*", " ", data)
    dlang_key = globals().get("DLANG_KEY", "")
    google_translate = globals().get("GOOGLE_TRANSLATE", False)


    if dlang_key and google_translate:
         try:
             input_lang = detectlanguage.simple_detect(data)
             PRINT("\n-Trinitty:detectlanguage:input_lang set to :",input_lang)
         except Exception as e:
            PRINT("\n-Trinitty:Error:detectlanguage.simple_detect:")
            PRINT(e)

    if google_translate:
        if not input_lang:
             try:
                  client = translate_v2.Client()
                  input_lang = client.detect_language(data)
                  input_lang = input_lang['language']
                  PRINT("\n-Trinitty:google.detect_language:input_lang set to :",input_lang)
             except Exception as e:
                  PRINT("\n-Trinitty:Error:client.detect_language:")
                  PRINT(e)
                  input_lang = "fr"

        if input_lang != "fr":
            try:
               data_translated = GoogleTranslator(source=input_lang, target='fr').translate(text=data)
               Play_Audio_File(SCRIPT_PATH+"/local_sounds/trad/traduction.wav")
               PRINT("\n-Trinitty:GoogleTranslator:Translation successful.")
               data = data_translated
            except Exception as e:
                  PRINT("\n-Trinitty:Error:GoogleTranslator:")
                  PRINT(e)
                  if "No support for the provided language" in str(e):
                      PRINT("\n-Trinitty:GoogleTranslator:Trying auto detect input language..")
                      try:
                         data_translated = GoogleTranslator(source="auto", target='fr').translate(text=data)
                         Play_Audio_File(SCRIPT_PATH+"/local_sounds/trad/traduction.wav")
                         PRINT("\n-Trinitty:GoogleTranslator:Translation successful.")
                         data = data_translated
                      except Exception as e:
                            PRINT("\n-Trinitty:Error:GoogleTranslator:")
                            PRINT(e)



    emoj = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002500-\U00002BEF"  # chinese char
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "\u2640-\u2642"
        "\u2600-\u2B55"
        "\u200d"
        "\u23cf"
        "\u23e9"
        "\u231a"
        "\ufe0f"  # dingbats
        "\u3030"
        "]+",
        re.UNICODE,
    )


    if "Generated by BLACKBOX.AI, try unlimited chat" in data:
        index = data.find("Generated by BLACKBOX.AI, try unlimited chat")
        data = data[index + 45 :]

    if "Bonjour, c'est Bing." in data:
        index = data.find("Bonjour, c'est Bing.")
        data = data[index + 21 :]

    if "Bonjour, je suis Copilot" in data:
        to_find = "Bonjour, je suis Copilot"
        index = data.find(to_find)
        after_to_find = index + len(to_find)
        next_point = None
        for n, c in enumerate(data[after_to_find:]):
            if c == ".":
                next_point = n + 1
                break
        if next_point:
            data = data[index + len(to_find) + next_point :]
        else:
            data = data[index + len(to_find) :]

    data = data.replace("**", "")
    data = data.replace("* ","")
    data = data.replace(" *","")
    no_link = re.sub(r'\[\d+\]:\s*https?://[^\s]+ "[^"]*"\n?', "", data)
    no_emoj = re.sub(emoj, "", no_link)
    no_brak = re.sub(r"\[[^\]]+\]", "", no_emoj)
    no_brak2 = re.sub(r"\[\^?\d+\^?\]:", "", no_brak)

    final = ""
    for raw_line in no_brak2.splitlines():
#        if line.startswith("* "):
#            data = data.replace("* ", "")
        line = raw_line
        if "http" in line:
            httpos = line.find("http")
            to_replace = line[httpos : line.find(" ")]
            if len(to_replace) == 0:
                to_replace = line[httpos:]
            line = line.replace(to_replace, " ")
            if len(line.replace(" ", "")) <= 1:
                continue
            final += "\n" + line
        else:
            final += line

    return final.replace("####", "").replace("###","")


def Play_Wait_Response_Audio(cancel_event=None):
    rnd = str(Non_Crypto_Randint(1, 10))
    wait = SCRIPT_PATH + "/local_sounds/wait/" + rnd + ".wav"
    PRINT("\n-Trinitty:wait response audio:%s" % wait)
    if cancel_event is None:
        return Play_Audio_File(wait)
    return Play_Audio_File(wait, cancel_event=cancel_event)


def Start_Wait_Response_Audio():
    stop_event = Event()

    def play_wait_response_audio():
        try:
            Play_Wait_Response_Audio(cancel_event=stop_event)
        except TypeError:
            Play_Wait_Response_Audio()

    listener = Thread(target=play_wait_response_audio, daemon=True)
    listener.start()
    return (stop_event, listener)


def Stop_Wait_Response_Audio(listener_info):
    if not listener_info:
        return
    stop_event, listener = listener_info
    stop_event.set()
    listener.join(timeout=0.2)


def To_Gpt(input, wait_audio=None):

    if wait_audio is None:
        wait_audio = Start_Wait_Response_Audio()

    def stop_wait_audio():
        nonlocal wait_audio
        Stop_Wait_Response_Audio(wait_audio)
        wait_audio = None

    Answer_Known = Check_History(input, before_replay=stop_wait_audio)

    if Answer_Known or not No_Input.empty():
        stop_wait_audio()
        return Trinitty()

    last_sentence.put(input)

    openai_response = Openai_Gpt(input)
    if openai_response:
        stop_wait_audio()
        return Text_To_Speech(str(openai_response), stayawake=False)

    if GPT4FREE_SERVERS_STATUS and Ensure_Gpt4free_Providers():
        return FreeGpt(
            input,
            check_history=False,
            save_last_sentence=False,
            play_wait=False,
            wait_audio=wait_audio,
        )

    stop_wait_audio()
    print("\n-Trinitty:Error no OpenAI response and no gpt4free fallback provider available.")
    Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_respons_allprovider.wav")
    return Go_Back_To_Sleep(False)


def Ensure_Gpt4free_Providers():
    global Providers_To_Use

    if not Ensure_Gpt4free_Runtime_Available():
        Providers_To_Use = []
        return Providers_To_Use

    if Providers_To_Use:
        return Providers_To_Use
    if GPT4FREE_SERVERS_LIST:
        Providers_To_Use = GPT4FREE_SERVERS_LIST
    elif GPT4FREE_SERVERS_STATUS:
        Refresh_Gpt4free_Providers_Config()
        GetConf()
        if GPT4FREE_SERVERS_LIST:
            Providers_To_Use = GPT4FREE_SERVERS_LIST
        elif GPT4FREE_SERVERS_STATUS:
            Providers_To_Use = Check_Free_Servers()
        else:
            Providers_To_Use = []
    else:
        Providers_To_Use = []
    return Providers_To_Use


def Openai_Config_Bool(value, default=False):
    if value is None:
        return default
    value = str(value).strip().lower()
    if value in ["true", "1", "yes", "y", "on", "active"]:
        return True
    if value in ["false", "0", "no", "n", "off", "none"]:
        return False
    return default


def Openai_Config_Path(path):
    path = str(path).strip()
    if not path:
        return ""
    path = os.path.expandvars(os.path.expanduser(path))
    if os.path.isabs(path):
        return path
    script_path = globals().get("SCRIPT_PATH", Default_Script_Path())
    return os.path.join(script_path, path)


def Openai_Config_Path_Candidates(path):
    path = str(path).strip()
    if not path:
        return []
    path = os.path.expandvars(os.path.expanduser(path))
    if os.path.isabs(path):
        return [path]
    return Config_File_Candidates(path)


def Openai_Existing_Config_Path(path):
    for candidate in Openai_Config_Path_Candidates(path):
        if os.path.exists(candidate):
            return candidate
    return ""


def Openai_Read_Key_File(filepath):
    for candidate in Openai_Config_Path_Candidates(filepath):
        if not candidate or not os.path.exists(candidate):
            continue
        try:
            with open(candidate) as key_file:
                for line in key_file:
                    key = Strip_Config_Inline_Comment(line).strip()
                    if key:
                        return key
        except Exception as e:
            PRINT("\n-Trinitty:OpenAI key file read error:%s" % str(e))
    return ""


def Openai_Read_Key_Source(source):
    source = str(source).strip()
    if not source or source.lower() in ["none", "false"]:
        return ""

    if source.lower().startswith("env:"):
        env_name = source.split(":", 1)[1].strip() or "OPENAI_API_KEY"
        return os.getenv(env_name, "").strip()

    if source.lower().startswith("file:"):
        return Openai_Read_Key_File(source.split(":", 1)[1].strip())

    if Openai_Existing_Config_Path(source):
        return Openai_Read_Key_File(source)

    return source


def Openai_Load_Key():
    configured_source = str(globals().get("OPENAI_API_KEY", "")).strip()
    configured_file = str(globals().get("OPENAI_API_KEY_FILE", "keys/openai.key")).strip()
    sources = []

    if configured_source:
        sources.append(configured_source)
    if configured_file:
        sources.append("file:%s" % configured_file)
    sources.append("env:OPENAI_API_KEY")

    checked_sources = []
    for source in sources:
        if source in checked_sources:
            continue
        checked_sources.append(source)
        api_key = Openai_Read_Key_Source(source)
        if api_key:
            return api_key

    return ""


def Openai_Key_Source_For_Log():
    source = str(globals().get("OPENAI_API_KEY", "")).strip()
    configured_file = str(globals().get("OPENAI_API_KEY_FILE", "keys/openai.key")).strip()
    if source.lower().startswith("env:") or source.lower().startswith("file:"):
        return source
    if source.lower() in ["none", "false"]:
        return source
    if Openai_Existing_Config_Path(source):
        return source
    if source:
        return "direct-token-configured"
    if configured_file:
        return "file:%s" % configured_file
    return "env:OPENAI_API_KEY"


def Openai_Response_Text(response):
    output_text = getattr(response, "output_text", "")
    if output_text:
        return str(output_text).strip()

    texts = []
    output = getattr(response, "output", []) or []
    for item in output:
        content = getattr(item, "content", None)
        if content is None and isinstance(item, dict):
            content = item.get("content")
        for part in content or []:
            text = getattr(part, "text", None)
            if text is None and isinstance(part, dict):
                text = part.get("text")
            if text:
                texts.append(str(text))

    return "\n".join(texts).strip()


def Openai_Gpt(input):
    if not Openai_Config_Bool(globals().get("OPENAI_ENABLED", True), default=True):
        PRINT("\n-Trinitty:OpenAI disabled by OPENAI_ENABLED.")
        return ""

    api_key = Openai_Load_Key()
    if not api_key:
        PRINT("\n-Trinitty:OpenAI token missing, using gpt4free fallback.")
        return ""

    model = str(globals().get("OPENAI_MODEL", "gpt-5.5")).strip() or "gpt-5.5"
    instructions = str(
        globals().get("OPENAI_INSTRUCTIONS", "Reponds en francais de facon concise et naturelle.")
    ).strip()
    try:
        timeout = float(globals().get("OPENAI_TIMEOUT", 30))
    except Exception:
        timeout = 30

    try:
        client = OpenAI(api_key=api_key, timeout=timeout)
        request = {
            "model": model,
            "input": str(input),
        }
        if instructions and instructions.lower() not in ["none", "false"]:
            request["instructions"] = instructions

        response = client.responses.create(**request)
        response_text = Openai_Response_Text(response)
        if not response_text:
            print("\n-Trinitty:OpenAI API error, using gpt4free fallback:empty OpenAI response")
            return ""
        PRINT("\n-Trinitty:OpenAI response received.")
        return response_text
    except Exception as e:
        print("\n-Trinitty:OpenAI API error, using gpt4free fallback:%s" % str(e))
        return ""


def Extract_First_Url(text):
    urls = re.findall(r"""https?://[^\s,'"()\[\]<>]+""", str(text or ""))
    if not urls:
        return ""
    return urls[0].rstrip(".,;:!?")


def Check_Free_Servers():
    PRINT("\n-Trinitty:Dans la fonction Check_Free_Servers")
    if not Ensure_Gpt4free_Runtime_Available():
        return []
    return Discover_Gpt4free_Text_Providers(GPT4FREE_SERVERS_AUTH)


def Filter_Gpt4free_Providers_For_Runtime(providers):
    if not providers:
        return []

    filtered = list(providers)
    if GPT4FREE_SERVERS_STATUS == "All":
        for provider in filtered:
            PRINT("\t", provider)
        return filtered

    for provider in list(filtered):
        if Gpt4free_Provider_Working(provider):
            PRINT("\t%s is working." % provider)
        else:
            filtered.remove(provider)
            PRINT("-Trinitty:%s has been removed from servers to use" % provider)
    return filtered


def Strip_Config_Inline_Comment(value):
    quote = None
    escaped = False
    for index, char in enumerate(value):
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char in ("'", '"'):
            if quote == char:
                quote = None
            elif quote is None:
                quote = char
            continue
        if char == "#" and quote is None:
            return value[:index]
    return value


def Config_Option_Value(line):
    if "=" not in line:
        return None, None
    key, value = line.split("=", 1)
    key = key.strip()
    value = Strip_Config_Inline_Comment(value).strip().strip("'\"")
    return key, value


def Parse_Gpt4free_Server_List(value):
    value = str(value or "").strip()
    if value.lower() in ["", "none", "false"]:
        return None
    providers = re.findall(r"g4f\.Provider\.[A-Za-z][A-Za-z0-9_]*", value)
    return list(dict.fromkeys(providers))


def Read_Raw_Config(filepath):
    config = {}
    if not os.path.exists(filepath):
        return config
    with open(filepath) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            key, value = Config_Option_Value(line)
            if key:
                config[key] = value
    return config


def Read_Raw_Runtime_Config():
    config = {}
    script_path = globals().get("SCRIPT_PATH", Default_Script_Path())
    for conf_file in (
        os.path.join(script_path, "datas", "conf.trinity"),
        os.path.join(script_path, "datas", "conf.local.trinity"),
        *User_Data_Path_Candidates("datas", "conf.local.trinity"),
        *User_Data_Path_Candidates("datas", "conf.trinity"),
    ):
        config.update(Read_Raw_Config(conf_file))
    return config


def Gpt4free_Auth_Mode(value):
    value = str(value).strip().lower()
    if value == "true":
        return "auth_only"
    if value == "all":
        return "all"
    return "no_auth"


def Gpt4free_Cookies_Dir():
    script_path = globals().get("SCRIPT_PATH", ".")
    return Writable_Dir_From_Candidates([
        os.path.join(script_path, "datas", "har_and_cookies"),
        User_Data_Path("g4f_cookies"),
    ])


def Gpt4free_Cookie_Capture_Source_Dir():
    configured = str(globals().get("GPT4FREE_COOKIES_SYNC_DIR", "") or "").strip()
    if configured:
        if os.path.isabs(configured):
            return configured
        return os.path.join(globals().get("SCRIPT_PATH", "."), configured)
    return os.path.join(globals().get("SCRIPT_PATH", "."), "tools", "har_and_cookies")


def Sync_Gpt4free_Cookie_Captures(source_dir=None, dest_dir=None):
    if not globals().get("GPT4FREE_COOKIES_AUTO_SYNC", True):
        return []
    if source_dir is None:
        source_dir = Gpt4free_Cookie_Capture_Source_Dir()
    if dest_dir is None:
        dest_dir = Gpt4free_Cookies_Dir()
    if not os.path.isdir(source_dir):
        return []

    os.makedirs(dest_dir, exist_ok=True)
    copied = []
    for filename in os.listdir(source_dir):
        if not filename.lower().endswith((".json", ".har")):
            continue
        source = os.path.join(source_dir, filename)
        dest = os.path.join(dest_dir, filename)
        if not os.path.isfile(source):
            continue
        try:
            copy2(source, dest)
            copied.append(dest)
        except Exception as e:
            Log_Error("Sync_Gpt4free_Cookie_Captures", e)
    return copied


def Gpt4free_Provider_Auth_Tokens(provider):
    name = getattr(provider, "__name__", "")
    parent = getattr(provider, "parent", "") or ""
    url = getattr(provider, "url", "") or ""
    tokens = [name, parent]
    if url:
        domain = re.sub(r"^https?://", "", str(url).lower()).split("/", 1)[0]
        tokens.append(domain)
        generic_domain_parts = {"www", "com", "net", "org", "ai", "app", "chat", "cloud", "console", "platform"}
        tokens.extend(part for part in domain.split(".") if part not in generic_domain_parts)
    clean_tokens = []
    for raw_token in tokens:
        token = re.sub(r"[^a-zA-Z0-9]+", "", str(raw_token or "")).lower()
        if token and token not in clean_tokens:
            clean_tokens.append(token)
    return clean_tokens


def Gpt4free_Provider_Cookies_Available(provider, cookies_dir=None):
    if cookies_dir is None:
        cookies_dir = Gpt4free_Cookies_Dir()
    if not os.path.isdir(cookies_dir):
        return False
    provider_tokens = Gpt4free_Provider_Auth_Tokens(provider)
    if not provider_tokens:
        return False
    for filename in os.listdir(cookies_dir):
        if not filename.lower().endswith((".json", ".har")):
            continue
        normalized = re.sub(r"[^a-zA-Z0-9]+", "", filename).lower()
        if any(token in normalized for token in provider_tokens):
            return True
    return False


def Gpt4free_Provider_Key_Available(provider):
    tokens = Gpt4free_Provider_Auth_Tokens(provider)
    for token in tokens:
        env_names = [
            "GPT4FREE_%s_API_KEY" % token.upper(),
            "GPT4FREE_%s_TOKEN" % token.upper(),
        ]
        if any(os.environ.get(env_name) for env_name in env_names):
            return True
        key_file = Existing_Config_File("keys/g4f_%s.key" % token)
        if os.path.exists(key_file) and os.path.getsize(key_file) > 0:
            return True
    return False


def Gpt4free_Provider_Has_Auth(provider):
    return Gpt4free_Provider_Cookies_Available(provider) or Gpt4free_Provider_Key_Available(provider)


def Resolve_Gpt4free_Provider(provider_name):
    provider_name = str(provider_name or "").strip()
    prefix = "g4f.Provider."
    if not provider_name.startswith(prefix):
        raise ValueError("Invalid g4f provider name: %s" % provider_name)

    provider_attr = provider_name[len(prefix):]
    if provider_attr.startswith("_") or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", provider_attr):
        raise ValueError("Invalid g4f provider attribute: %s" % provider_attr)

    return getattr(g4f.Provider, provider_attr)


def Gpt4free_Provider_Working(provider_name):
    try:
        return getattr(Resolve_Gpt4free_Provider(provider_name), "working", False) is True
    except Exception as e:
        PRINT("-Trinitty:Gpt4free_Provider_Working:%s" % e)
        return False


def Load_Gpt4free_Cookies():
    cookies_dir = Gpt4free_Cookies_Dir()
    Sync_Gpt4free_Cookie_Captures(dest_dir=cookies_dir)
    set_cookies_dir(cookies_dir)
    return read_cookie_files(cookies_dir)


def Ensure_Gpt4free_Cookies_Loaded():
    global GPT4FREE_COOKIES_LOADED

    if GPT4FREE_COOKIES_LOADED:
        return True

    try:
        Load_Gpt4free_Cookies()
        GPT4FREE_COOKIES_LOADED = True
        return True
    except Exception as e:
        PRINT("\n-Trinitty:Warning:g4f cookies non chargés:%s" % str(e))
        return False


def Gpt4free_Model_List(value):
    if not value:
        return []
    if isinstance(value, dict):
        return list(value.keys())
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, (list, tuple)):
        return list(value)
    return [str(value)]


def Gpt4free_Model_Is_Text(model):
    model = str(model).lower()
    media_words = [
        "audio", "tts", "voice", "speech", "image", "img", "flux", "dall-e",
        "stable-diffusion", "stability", "sd-", "sdxl", "video", "vision", "whisper"
    ]
    return not any(word in model for word in media_words)


def Config_Bool(value, default=False):
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    if value in ["true", "1", "yes", "y", "on", "active"]:
        return True
    if value in ["false", "0", "no", "n", "off", "none"]:
        return False
    return default


def Config_Positive_Float(value, default):
    try:
        parsed = float(value)
    except Exception:
        return default
    return parsed if parsed > 0 else default


@contextmanager
def Runtime_Timeout(seconds, label):
    timeout = Config_Positive_Float(seconds, 0)
    can_use_alarm = (
        timeout > 0
        and hasattr(signal, "SIGALRM")
        and hasattr(signal, "setitimer")
        and current_thread() is main_thread()
    )
    if not can_use_alarm:
        yield
        return

    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def timeout_handler(_signum, _frame):
        raise TimeoutError("%s timeout after %.1f seconds" % (label, timeout))

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0] > 0:
            signal.setitimer(signal.ITIMER_REAL, previous_timer[0], previous_timer[1])


def Saved_Answer_Path(*parts):
    base_folder = str(globals().get("SAVED_ANSWER", "") or "").strip()
    return os.path.join(base_folder, *parts)


def Default_Saved_Answer_Path():
    script_path = globals().get("SCRIPT_PATH", Default_Script_Path())
    return os.path.join(script_path, "local_sounds", "saved_answer")


def User_Saved_Answer_Path():
    return User_Data_Path("saved_answer")


def Configure_Saved_Answer_Path(configured):
    global SAVED_ANSWER

    configured = str(configured or "").strip()
    if not configured or configured.lower() == "default":
        candidates = [Default_Saved_Answer_Path(), User_Saved_Answer_Path()]
    else:
        configured = os.path.expandvars(os.path.expanduser(configured))
        if not os.path.isabs(configured):
            configured = os.path.join(globals().get("SCRIPT_PATH", Default_Script_Path()), configured)
        candidates = [configured, User_Saved_Answer_Path()]

    last_error = None
    for candidate in candidates:
        saved_error = os.path.join(candidate, "saved_error")
        try:
            os.makedirs(saved_error, exist_ok=True)
        except Exception as e:
            last_error = e
            print("\n-Trinitty:Error:Impossible de créer le dossier:%s :%s" % (saved_error, str(e)))
            continue
        SAVED_ANSWER = candidate
        return SAVED_ANSWER

    raise RuntimeError("No writable SAVED_ANSWER directory: %s" % str(last_error))


def Error_Log_File():
    base_folder = str(globals().get("SAVED_ANSWER", "") or "").strip()
    if base_folder:
        folder = Saved_Answer_Path("saved_error")
    else:
        folder = os.path.join(globals().get("SCRIPT_PATH", "."), "tmp")
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, "trinitty.errors")


def Log_Error(context, err=None):
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "context": str(context),
        "error": str(err or ""),
    }
    globals().setdefault("Runtime_Errors", []).append(entry)
    try:
        with open(Error_Log_File(), "a+", newline="") as f:
            f.write("[%s] %s: %s\n" % (entry["time"], entry["context"], entry["error"]))
    except Exception as log_error:
        print("\n-Trinitty:Error:Log_Error:%s" % str(log_error), file=sys.stderr)
    if globals().get("DEBUG", False):
        if isinstance(err, BaseException):
            debug_error = "".join(traceback.format_exception(type(err), err, err.__traceback__))
        else:
            debug_error = str(err or "")
        Debug_Log("ERROR[%s] %s" % (context, debug_error))
    return entry


def Missing_Runtime_File(filepath, context="Load_Csv"):
    err = FileNotFoundError(filepath)
    print("\n-Trinitty:Error:%s not found." % filepath)
    Log_Error(context, err)
    return False


def Gpt4free_Auto_Reject_Notworking():
    return Config_Bool(globals().get("GPT4FREE_AUTO_REJECT_NOTWORKING", True), default=True)


def Gpt4free_Provider_Is_Text_Chat(provider, auth_mode="no_auth"):
    helper_names = [
        "AnyProvider",
        "AsyncGeneratorProvider",
        "AsyncProvider",
        "BackendApi",
        "BaseProvider",
        "CreateImagesProvider",
        "Custom",
        "Feature",
        "IterListProvider",
        "OpenaiTemplate",
        "ProviderModelMixin",
        "RetryProvider",
        "RotatedProvider",
    ]
    excluded_module_parts = [".audio.", ".search.", ".local.", ".deprecated."]
    allowed_no_auth_from_auth_modules = ["OpenaiChat"]
    excluded_name_words = ["Image", "Images", "TTS", "Search", "Designer", "Flux", "StabilityAI"]

    name = getattr(provider, "__name__", "")
    module = getattr(provider, "__module__", "")
    if not name or name in helper_names:
        return False
    if any(part in module for part in excluded_module_parts):
        return False
    if auth_mode == "no_auth" and ".needs_auth." in module and name not in allowed_no_auth_from_auth_modules:
        return False
    if any(word in name for word in excluded_name_words):
        return False
    if Gpt4free_Auto_Reject_Notworking() and getattr(provider, "working", False) is not True:
        return False

    needs_auth = getattr(provider, "needs_auth", False)
    if auth_mode == "no_auth" and needs_auth:
        return False
    if auth_mode == "auth_only" and not needs_auth:
        return False
    if auth_mode in ["auth_only", "all"] and needs_auth and not Gpt4free_Provider_Has_Auth(provider):
        return False

    text_models = Gpt4free_Model_List(getattr(provider, "text_models", None))
    if text_models:
        return True

    default_model = getattr(provider, "default_model", None)
    image_models = set(Gpt4free_Model_List(getattr(provider, "image_models", None)))
    audio_models = set(Gpt4free_Model_List(getattr(provider, "audio_models", None)))
    if default_model and (default_model in image_models or default_model in audio_models):
        return False

    models = Gpt4free_Model_List(getattr(provider, "models", None))
    if models:
        return any(Gpt4free_Model_Is_Text(model) for model in models)

    if getattr(provider, "supports_message_history", False):
        return True
    if getattr(provider, "supports_system_message", False):
        return True

    return bool(default_model)


def Discover_Gpt4free_Text_Providers(auth_mode="no_auth"):
    if not Ensure_Gpt4free_Runtime_Available():
        return []

    preferred_order = [
        "Qwen",
        "PollinationsAI",
        "OpenaiChat",
        "Yqcloud",
        "Chatai",
        "DeepInfra",
        "LambdaChat",
        "OperaAria",
        "WeWordle",
        "GLM",
        "TeachAnything",
        "ApiAirforce",
        "GradientNetwork",
        "ItalyGPT",
        "Mintlify",
        "OIVSCodeSer0501",
        "OIVSCodeSer2",
        "Perplexity",
        "Yupp",
    ]
    providers_to_return = []
    auth_mode = Gpt4free_Auth_Mode(auth_mode)

    try:
        g4f_provider_module = g4f.Provider
        provider_classes = getattr(g4f_provider_module, "__providers__", [])
    except Exception as e:
        print("\n-Trinitty:Error:Discover_Gpt4free_Text_Providers:%s" % str(e))
        provider_classes = []

    for provider in provider_classes:
        name = getattr(provider, "__name__", "")
        if name and Gpt4free_Provider_Is_Text_Chat(provider, auth_mode):
            provider_name = "g4f.Provider.%s" % name
            if provider_name not in providers_to_return:
                providers_to_return.append(provider_name)

    def sort_key(provider_name):
        name = provider_name.replace("g4f.Provider.", "")
        if name in preferred_order:
            return (0, preferred_order.index(name))
        return (1, name.lower())

    providers_to_return = sorted(providers_to_return, key=sort_key)

    if len(providers_to_return) == 0:
        print("\n-Trinitty:Error retrieving gpt4free text providers.Using saved fallback list.")
        providers_to_return = [
            "g4f.Provider.Qwen",
            "g4f.Provider.PollinationsAI",
            "g4f.Provider.Yqcloud",
            "g4f.Provider.Chatai",
            "g4f.Provider.DeepInfra",
            "g4f.Provider.LambdaChat",
            "g4f.Provider.OperaAria",
            "g4f.Provider.WeWordle",
            "g4f.Provider.GLM",
        ]

    return providers_to_return


def Refresh_Gpt4free_Providers_Config():
    global GPT4FREE_AUTO_REJECT_NOTWORKING

    conf_file = SCRIPT_PATH + "/datas/conf.trinity"
    marker = "# Auto-updated by Trinitty from gpt4free provider metadata."

    if not os.path.exists(conf_file):
        return False

    raw_config = Read_Raw_Runtime_Config()
    if str(raw_config.get("GPT4FREE_SERVERS_STATUS", "")).lower() == "none":
        PRINT("\n-Trinitty:Gpt4free disabled by GPT4FREE_SERVERS_STATUS=None.")
        return False

    auth_mode = raw_config.get("GPT4FREE_SERVERS_AUTH", "False")
    GPT4FREE_AUTO_REJECT_NOTWORKING = Config_Bool(
        raw_config.get(
            "GPT4FREE_AUTO_REJECT_NOTWORKING",
            globals().get("GPT4FREE_AUTO_REJECT_NOTWORKING", True),
        ),
        default=True,
    )
    providers = Discover_Gpt4free_Text_Providers(auth_mode)
    if not providers:
        return False

    new_line = "GPT4FREE_SERVERS_LIST = [%s]\n" % ",".join(providers)

    with open(conf_file) as f:
        lines = f.readlines()

    out_lines = []
    replaced = False
    for line in lines:
        if line.strip() == marker:
            continue
        key, _value = Config_Option_Value(line)
        if key == "GPT4FREE_SERVERS_LIST":
            if not out_lines or out_lines[-1].strip() != marker:
                out_lines.append(marker + "\n")
            out_lines.append(new_line)
            replaced = True
        else:
            out_lines.append(line)

    if not replaced:
        if out_lines and out_lines[-1].strip():
            out_lines.append("\n")
        out_lines.append(marker + "\n")
        out_lines.append(new_line)

    current = "".join(lines)
    updated = "".join(out_lines)
    if current != updated:
        tmp_file = conf_file + ".tmp"
        try:
            with open(tmp_file, "w") as f:
                f.write(updated)
            os.replace(tmp_file, conf_file)
        except OSError as e:
            try:
                if os.path.exists(tmp_file):
                    os.remove(tmp_file)
            except OSError:
                print("\n-Trinitty:Warning:impossible de supprimer le fichier temporaire:%s" % tmp_file)
            print("\n-Trinitty:Warning:impossible de mettre à jour datas/conf.trinity:%s" % str(e))
            return False
        print("\n-Trinitty:Gpt4free providers texte mis à jour dans datas/conf.trinity:%s" % len(providers))
    else:
        PRINT("\n-Trinitty:Gpt4free providers texte déjà à jour:%s" % len(providers))

    return True


def FreeGpt(input, check_history=True, save_last_sentence=True, play_wait=True, wait_audio=None):
    PRINT("\n-Trinitty:Dans la fonction FreeGpt")

    global LAST_DIALOG
    global Current_Provider_Id
    global Blacklisted

    def minitts(tx, fname):

            try:

                client = tts.TextToSpeechClient()
                audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)

                text_input = tts.SynthesisInput(text=tx)
                voice_params = tts.VoiceSelectionParams(language_code="fr-FR", name="fr-FR-Neural2-A")

                response = client.synthesize_speech(input=text_input, voice=voice_params, audio_config=audio_config)
                audio_response = response.audio_content
                try:
                    with open(fname, "wb") as out:
                        out.write(audio_response)
                except Exception as e:
                    PRINT("\n-Trinitty:Error:%s" % str(e))
            except Exception as e:
                PRINT("\n-Trinitty:Error:%s" % str(e))


    def save_blacklist(server, err):
        err_file = Saved_Answer_Path("saved_error", "g4f_providers.errors")
        try:
            with open(err_file, "a+", newline="") as f:
                now = "===== " + str(datetime.now().strftime("%Y-%m-%d-%H:%M:%S")) + " =====\n"
                serverr = "g4f provider:%s error:%s\n" % (str(server), err)
                f.write(now)
                f.write(serverr)
        except Exception as e:
            print("\n-Trinitty:Error:save_blacklist():%s" % str(e))

    def provider_error_audio(provider_ref):
        provider_name = provider_ref.replace("g4f.Provider.", "")
        packaged_wav = Local_Sound_Path("providers", str(provider_name) + ".wav")
        if os.path.exists(packaged_wav):
            return provider_name, packaged_wav

        generated_wav = Runtime_Tmp_Path("providers", History_Category_File_Name(provider_name) + ".wav")
        if not os.path.exists(generated_wav):
            os.makedirs(os.path.dirname(generated_wav), exist_ok=True)
            err_txt = "Le serveur %s n'a pas répondu , je vais essayer le suivant" % provider_name
            minitts(err_txt, generated_wav)
        return provider_name, generated_wav

    def stop_wait_audio():
        nonlocal wait_audio
        Stop_Wait_Response_Audio(wait_audio)
        wait_audio = None

    Answer_Known = False
    if check_history:
        Answer_Known = Check_History(input)

    if Answer_Known or not No_Input.empty():
        stop_wait_audio()
        return Trinitty()

    if save_last_sentence:
        last_sentence.put(input)

    response = ""
    response_text = ""
    successful_provider = None

    if Blacklisted is None:
        Blacklisted = []

    providers_to_use = list(Providers_To_Use or [])
    if len(providers_to_use) == 0:
        stop_wait_audio()
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_respons_allprovider.wav")
        return Go_Back_To_Sleep(False)

    if Current_Provider_Id >= len(providers_to_use) or Current_Provider_Id < 0:
        Current_Provider_Id = 0

    if not Ensure_Gpt4free_Runtime_Available():
        stop_wait_audio()
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_respons_allprovider.wav")
        return Go_Back_To_Sleep(False)

    if play_wait and wait_audio is None:
        wait_audio = Start_Wait_Response_Audio()

    Ensure_Gpt4free_Cookies_Loaded()

    def advance_provider():
        global Current_Provider_Id
        if len(providers_to_use) == 0:
            Current_Provider_Id = 0
            return
        Current_Provider_Id = (Current_Provider_Id + 1) % len(providers_to_use)

    p_cnt = 0
    max_provider_attempts = len(providers_to_use)
    while p_cnt < max_provider_attempts:
        if Current_Provider_Id >= len(providers_to_use):
            Current_Provider_Id = 0
        provider_ref = providers_to_use[Current_Provider_Id]
        if provider_ref in Blacklisted:
            PRINT("\n-Trinitty:skipping :", provider_ref)
            advance_provider()
            p_cnt += 1
            continue

        PRINT("\n-Trinitty:Asking :", provider_ref)
        request_input = str(input)
        if provider_ref in ["g4f.Provider.PerplexityLabs","g4f.Provider.ChatgptFree"]: ##tmpfix
             PRINT("\n-Trinitty:Adding '. Réponds en français.':")
             request_input = request_input + " . Réponds en français."

        try:
            response = g4f.ChatCompletion.create(
                model=g4f.models.default,
                provider=Resolve_Gpt4free_Provider(provider_ref),
                timeout=10,
                messages=[{"role": "user", "content": request_input}],
            )
            response_text = str(response or "")

            if len(response_text) < 1:
                PRINT(
                    "\n-Trinitty:len(response) < 1:No answer from :",
                    provider_ref,
                )
                stop_wait_audio()
                _provider_name, wait = provider_error_audio(provider_ref)
                Play_Audio_File(wait)
                advance_provider()

            elif "Request ended with status code 404" in response_text:

                 print("\n-Trinitty:Error:Request ended with status code 404")
                 print("\n-Trinitty:No answer from :", provider_ref)
                 stop_wait_audio()
                 _provider_name, wait = provider_error_audio(provider_ref)
                 Play_Audio_File(wait)
                 save_blacklist(provider_ref,"Request ended with status code 404")
                 if provider_ref not in Blacklisted:
                     Blacklisted.append(provider_ref)
                 advance_provider()

            else:
                successful_provider = provider_ref
                break

        except Exception as e:
            print("\n-Trinitty:Error:", str(e))
            print("\n-Trinitty:No answer from :", provider_ref)
            stop_wait_audio()
            _provider_name, wait = provider_error_audio(provider_ref)
            Play_Audio_File(wait)
            save_blacklist(provider_ref, str(e))
            if provider_ref not in Blacklisted:
                Blacklisted.append(provider_ref)
            advance_provider()
        p_cnt += 1

    if len(response_text) < 1:
        stop_wait_audio()
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_respons_allprovider.wav")
        return Go_Back_To_Sleep(False)
    PRINT("\n-Trinitty:Le server %s à répondu." % successful_provider)
    advance_provider()
    ##checktime
    stop_wait_audio()
    return Text_To_Speech(response_text, stayawake=False)

def wake_up():
    global PUSH_TO_TALK

    PRINT("\n-Trinitty:Dans la fonction Wakeup")

    word_key = SCRIPT_PATH + "/models/trinity_fr_raspberry-pi_v3_0_0.ppn"
    word_key2 = SCRIPT_PATH + "/models/interpreteur_fr_raspberry-pi_v3_0_0.ppn"
    word_key3 = SCRIPT_PATH + "/models/repete_fr_raspberry-pi_v3_0_0.ppn"
    word_key4 = SCRIPT_PATH + "/models/merci_fr_raspberry-pi_v3_0_0.ppn"
    pvfr = SCRIPT_PATH + "/models/porcupine_params_fr.pv"
    porcupine = None
    keyword_index = None
    audio_stream = None
    pa = None
    wake_error = None

    try:
        porcupine = pvporcupine.create(
            access_key=PICO_KEY,
            model_path=pvfr,
            keyword_paths=[word_key, word_key2, word_key3, word_key4],
            sensitivities=[1, 1, 1, 1],
        )
#        print("hey")
        with ignoreStderr():
            pa = pyaudio.PyAudio()
#        pa = pyaudio.PyAudio()
#        print("hey2")
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
        )

        print("\n-Trinitty: En attente ...")

        while True:
            pcm = audio_stream.read(porcupine.frame_length)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm)
            if keyword_index == 0:
                PRINT("\n-Trinitty:keyword_index:", keyword_index)

                rnd = str(Non_Crypto_Randint(1, 15))
                wake_sound = SCRIPT_PATH + "/local_sounds/wakesounds/" + rnd + ".wav"
                Play_Audio_File(wake_sound)
                break
            if keyword_index == 1:
                PRINT("\n-Trinitty:keyword_index:", keyword_index)
                break
            if keyword_index == 2:
                PRINT("\n-Trinitty:keyword_index:", keyword_index)
                break
            if keyword_index == 3:
                PRINT("\n-Trinitty:keyword_index:", keyword_index)
                rnd = str(Non_Crypto_Randint(1, 15))
                thk_sound = SCRIPT_PATH + "/local_sounds/merci/" + rnd + ".wav"
                Play_Audio_File(thk_sound)

    except Exception as e:
        wake_error = e
    finally:
        if porcupine is not None:
            porcupine.delete()
        if audio_stream is not None:
            audio_stream.close()
        if pa is not None:
            pa.terminate()

    if wake_error is not None:
        Log_Error("wake_up", wake_error)
        PUSH_TO_TALK = True
        print("\n-Trinitty:Wake word unavailable; switching to PUSH_TO_TALK mode.")
        return Push_To_Talk()

    if keyword_index is None:
        print("\n-Trinitty:Error keyword_index = None")
        Log_Error("wake_up", "keyword_index=None")
        PUSH_TO_TALK = True
        return Push_To_Talk()
    if keyword_index == 0:
        return Trinitty("Speech_To_Text")
    if keyword_index == 1:
        return Prompt()
    if keyword_index == 2:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/repeat/isaid.wav")
        Play_Audio_File(Runtime_Tmp_Path("current_answer.wav"))
        return wake_up()
    return None


def Record_Query():
    PRINT("\n-Trinitty:Dans la fonction Record_Query")

    p = None
    stream = None
    try:
        with ignoreStderr():
            p = pyaudio.PyAudio()

        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=FRAME_RATE,
            input=True,
            frames_per_buffer=FRAME_DURATION,
        )

        wake_sound = SCRIPT_PATH + "/local_sounds/wakesounds/record.wav"
        Play_Audio_File(wake_sound)

        while not record_on.empty():
            try:
                frames = stream.read(FRAME_DURATION, exception_on_overflow=False)
            except TypeError:
                frames = stream.read(FRAME_DURATION)
            chunks.put(frames)

        PRINT("\n-Trinitty:Enregistrement terminé.")
        wake_sound = SCRIPT_PATH + "/local_sounds/wakesounds/record_end.wav"
        Play_Audio_File(wake_sound)
    except Exception as e:
        print("\n-Trinitty:Record_Query():Error:%s" % str(e))
        Stop_Recording()
        cancel_operation.put(True)
        No_Input.put(True)
    finally:
        if stream is not None:
            try:
                stream.stop_stream()
                stream.close()
            except Exception as e:
                PRINT("\n-Trinitty:Record_Query():stream close error:%s" % str(e))
        if p is not None:
            p.terminate()
    return ()


def Check_Silence():

    PRINT("\n-Trinitty:Dans la fonction Check_Silence")
    buffer = b""
    lock = True
    threshold = 1.5
    silence = 0
    no_input = 0
    time_cnt = 0
    VAD = webrtcvad.Vad(3)

    while not record_on.empty():
        frames = Queue_Get_Optional(chunks, timeout=0.1, default=None)
        if frames is not None:
            if not webrtcvad.valid_rate_and_frame_length(FRAME_RATE, FRAME_DURATION):
                raise ValueError("Invalid VAD frame settings: rate=%s duration=%s" % (FRAME_RATE, FRAME_DURATION))
            on_air = VAD.is_speech(frames, sample_rate=FRAME_RATE)

            if on_air:

                if lock:
                    lock = False
                buffer += frames
                silence = 0

            elif not on_air and not lock:

                if silence < threshold * (FRAME_RATE / FRAME_DURATION):
                    silence += 1

                else:
                    lock = True
                    silence = 0
                    Stop_Recording()
                    to_speech = buffer
                    buffer = b""
                    PRINT("\n-Trinitty:Silence détecté-\n")
                    audio_datas.put(to_speech)
                    break
            elif not on_air and lock:
                no_input += 1
                if no_input > 1000:
                    lock = True
                    silence = 0
                    buffer = b""

                    Stop_Recording()

                    rnd = str(Non_Crypto_Randint(1, 11))
                    no_input_sound = SCRIPT_PATH + "/local_sounds/noinput/" + rnd + ".wav"
                    Play_Audio_File(no_input_sound)
                    cancel_operation.put(True)
                    No_Input.put(True)
                    break

            time_cnt += 1
            if time_cnt > 3600:
                lock = True
                silence = 0
                Stop_Recording()
                to_speech = buffer
                buffer = b""
                audio_datas.put(to_speech)
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_too_long.wav")
                break
        else:
            time_cnt += 1
            if time_cnt > 3600:
                Stop_Recording()
                cancel_operation.put(True)
                No_Input.put(True)
                PRINT("\n-Trinitty:Check_Silence():timeout waiting for audio chunks.")
                break


def Write_csv(function_name, trigger_word, filename):

    # CMDFILE,
    with open(filename, "a+", newline="") as csvfile:
        fieldnames = ["function", "trigger"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if csvfile.tell() == 0:
            writer.writeheader()

        writer.writerow({"function": function_name, "trigger": trigger_word})

    return Load_Csv()


def Special_Syntax_Has_Nested_Brackets(txt):
    depth = 0
    for char in str(txt or ""):
        if char == "[":
            depth += 1
            if depth > 1:
                return True
        elif char == "]":
            depth = max(0, depth - 1)
    return False


def Special_Syntax_Collapse_Spaces(value):
    value = str(value)
    while "  " in value:
        value = value.replace("  ", " ")
    return value


def Special_Syntax_Recursive(txt):
    txt = str(txt)

    def concat(prefixes, suffixes):
        output = []
        for prefix in prefixes:
            for suffix in suffixes:
                output.append(prefix + suffix)
        return output

    def parse_sequence(index, stop_chars):
        values = [""]
        while index < len(txt):
            char = txt[index]
            if char in stop_chars:
                break
            if char == "[":
                group_values, index = parse_group(index + 1, "]")
                values = concat(values, group_values)
            elif char == "{":
                group_values, index = parse_group(index + 1, "}")
                values = concat(values, group_values)
            else:
                values = [value + char for value in values]
                index += 1
        return values, index

    def parse_group(index, end_char):
        values = []
        while True:
            sequence_values, index = parse_sequence(index, set(["/", end_char]))
            values.extend(sequence_values)
            if index >= len(txt):
                raise ValueError("missing closing %s" % end_char)
            if txt[index] == "/":
                index += 1
                continue
            if txt[index] == end_char:
                index += 1
                return values, index

    values, index = parse_sequence(0, set())
    if index != len(txt):
        raise ValueError("unexpected parser stop at %s" % index)
    return [Special_Syntax_Collapse_Spaces(value) for value in values]


def Special_Syntax(txt, filepath=None, line=None):

    if Special_Syntax_Has_Nested_Brackets(txt):
        try:
            final_list = Special_Syntax_Recursive(txt)
            if globals().get("SYNTAX_DBG", False):
                PRINT("\n-Trinitty:Output Special Syntax for:\n%s\n\n%s" % (txt, final_list))
            return final_list
        except Exception as e:
            print("-Trinitty Error:", str(e))
            PRINT("\n-Trinitty:Special_Syntax():~PARSE~ERR~:txt:\n%s\n" % txt)
            return None


    def parse_cmd(cmd_txt):

        #         def unnest(lst, append=False):
        #             chunk = []
        #             for x in lst:
        #                 if isinstance(x, list):
        #                     if chunk:
        #                         yield chunk
        #                     yield from unnest(x, True)
        #                     chunk = []
        #                 else:
        #                     if append:
        #                         chunk.append(x)
        #                     else:
        #                         yield [x]
        #             if chunk:
        #                 yield chunk

        def to_list(str_lst):

            def check_split(index):
                coma = False
                obracket = False
                cbracket = False
                quote = False

                for c in str_lst[index:]:
                    #            print("c:",c)
                    if c == " ":
                        pass
                    elif c == ",":
                        coma = True
                    elif c == "[":
                        obracket = True
                    elif c == "]":
                        cbracket = True
                    elif c in ["'", '"']:
                        quote = True
                    else:
                        return (coma and obracket) or (coma and quote) or cbracket
                #        print("Rien")
                return True

            bucket = ""
            to_split = False
            #    listing = []
            for e, char in enumerate(str_lst):
                #        print("bucket:",bucket)
                if to_split:
                    if char in ["'", '"']:
                        #                     print("bucket:",bucket)
                        if check_split(e + 1):
                            yield (None, bucket)
                            # listing.append((None,bucket))
                            bucket = ""
                            to_split = False
                        else:
                            bucket += char
                    else:
                        bucket += char
                else:
                    if char == "[":
                        #                 listing.append(("[", None))
                        yield ("[", None)
                    elif char == "]":
                        #                 listing.append(("]", None))
                        yield ("]", None)
                    elif char in ["'", '"']:
                        to_split = True
                    else:
                        pass

        #    print("listing\:",listing)
        #    return listing

        def make_list(listing):
            lst = []
            for id, data in listing:
                if id == "[":
                    lst.append(make_list(listing))
                elif id == "]":
                    return lst
                else:
                    lst.append(data)
            return lst[0]

        def add_braks(cmd_txt, _lbraks, _rbraks):
            def check_around(idx):
                while True:
                    if idx <= 0:
                        return False
                    if cmd_txt[idx] == " ":
                        pass
                    elif cmd_txt[idx] == "[":
                        return False
                    else:
                        return cmd_txt[idx] == "]"
                    idx -= 1
                # return True

            outside_lvl = []
            bad_pos = []
            skip = 0
            start = None
            end = None
            for e, char in enumerate(cmd_txt):

                if char == "[" and start is None:
                    start = e
                elif char == "[":
                    skip += 1
                elif char == "]":
                    if skip > 0:
                        skip -= 1
                    else:
                        end = e + 1
                        outside_lvl.append((start, end))
                        start = None
                        end = None

            for st, ed in outside_lvl:
                for i in range(st, ed):
                    bad_pos.append(i)

            braks_txt = ""
            opened = False
            for e, char in enumerate(cmd_txt):
                if e not in bad_pos:
                    if opened:
                        braks_txt += str(char)
                    else:
                        if check_around(e - 1):
                            # print("cmd_txt[%s-1]:%s char:,[%s"%(e,cmd_txt[e-1],char))
                            braks_txt += ",[" + str(char)
                        else:
                            # print("cmd_txt[%s-1]:%s char:[%s"%(e,cmd_txt[e-1],char))
                            braks_txt += "[" + str(char)
                        opened = True

                else:
                    if opened:
                        braks_txt += "]," + str(char)
                        opened = False
                    else:
                        braks_txt += str(char)

            if opened:
                braks_txt += "]"

            return "[" + braks_txt + "]"

        def add_quotes(fullbraks):

            def check_around(idx, coma=False):
                if coma:
                    pos = idx - 1
                    before = False
                    after = False
                    while True:
                        #                     print("char before:",fullbraks[pos])
                        if pos == 0:
                            break
                        if fullbraks[pos] == " ":
                            pass
                        elif fullbraks[pos] == "[":
                            before = True
                            break
                        elif fullbraks[pos] == "]":
                            before = False
                            break
                        else:
                            before = True
                            break
                        pos -= 1

                    for c in fullbraks[idx + 1 :]:
                        #                     print("char after:",c)
                        if c == " ":
                            pass
                        if c == "[":
                            after = False
                            break
                        if c == "]":
                            after = True
                            break
                        after = True
                        break

                    if before and not after:
                        #                         print("before and not after")
                        return '",'
                    if after and not before:
                        #                         print("after and not before")
                        return ',"'
                    if not before and not after:
                        #                         print("not before and not after")
                        return ","
                    #                         print(" before and after")
                    return '","'

                for c in fullbraks[idx:]:
                    return c not in ["[", "]"]
                return False

            fullquotes = ""
            for e, char in enumerate(fullbraks):
                #             print("char:",char)
                if char == "[":
                    if check_around(e + 1):
                        fullquotes += '["'
                    else:
                        fullquotes += "["
                elif char == "]":
                    if check_around(e - 1):
                        fullquotes += '"]'
                    else:
                        fullquotes += "]"
                elif char == ",":

                    fullquotes += check_around(e, True)
                else:
                    fullquotes += char
            return fullquotes

        def valid_lists(cmd_txt):
            lbraks = [pos for pos, char in enumerate(cmd_txt) if char == "["]
            rbraks = [pos for pos, char in enumerate(cmd_txt) if char == "]"]
            lbrak_nbr = len(lbraks)
            rbrak_nbr = len(rbraks)

            lcurlys = [pos for pos, char in enumerate(cmd_txt) if char == "{"]
            rcurlys = [pos for pos, char in enumerate(cmd_txt) if char == "}"]
            lcurly_nbr = len(lcurlys)
            rcurly_nbr = len(rcurlys)

            if lbrak_nbr == 0 and rbrak_nbr == 0 and lcurly_nbr > 0 and rcurly_nbr > 0:
                print(
                    "\n-Fichier:%s ligne:%s Les symboles '{' et '}' s'utilisent conjointement avec les symboles '[' et ']' mais pas seuls."
                    % (filepath, line)
                )
                return ("~PARSE~ERR~", None, None)
            if lbrak_nbr == 0 and rbrak_nbr == 0:
                return (False, None, None)
            if lbrak_nbr != rbrak_nbr:
                if lbrak_nbr > rbrak_nbr:
                    print(
                        "\n-Fichier:%s ligne:%s Il ya %s '[' et %s ']' seulement."
                        % (filepath, line, lbrak_nbr, rbrak_nbr)
                    )
                else:
                    print(
                        "\n-Fichier:%s ligne:%s Il ya seulement %s '[' et %s ']'."
                        % (filepath, line, lbrak_nbr, rbrak_nbr)
                    )
                return ("~PARSE~ERR~", None, None)

            if lcurly_nbr != rcurly_nbr:
                if lcurly_nbr > rcurly_nbr:
                    print(
                        "\n-Fichier:%s ligne:%s Il ya %s '{' et %s '}' seulement."
                        % (filepath, line, lcurly_nbr, rcurly_nbr)
                    )
                else:
                    print(
                        "\n-Fichier:%s ligne:%s Il ya seulement %s '{' et %s '}'."
                        % (filepath, line, lcurly_nbr, rcurly_nbr)
                    )
                return ("~PARSE~ERR~", None, None)

            for o, c in zip(lbraks, rbraks, strict=False):
                #             print("o:%s c:%s"%(o,c))
                if o > c:
                    print("\n-Fichier:%s ligne:%s Mauvaise syntax." % (filepath, line))
                    return ("~PARSE~ERR~", None, None)
            for o, c in zip(lcurlys, rcurlys, strict=False):
                #             print("o:%s c:%s"%(o,c))
                if o > c:
                    print("\n-Fichier:%s ligne:%s Mauvaise syntax." % (filepath, line))
                    return ("~PARSE~ERR~", None, None)

            return (True, lbraks, rbraks)

        cmd_txt = cmd_txt.replace("/", ",")

        list_inside, lbraks, rbraks = valid_lists(cmd_txt)
        if list_inside:
            if list_inside == "~PARSE~ERR~":
                return (list_inside, None)
            try:
                curlys = None
                fullbraks = add_braks(cmd_txt, lbraks, rbraks)
                if "{" in fullbraks and "}" in fullbraks:
                    fullbraks, curlys = extract_curly(fullbraks)
                    fullquotes = add_quotes(fullbraks)
                #                  fullquotes = putback_curly(fullquotes,curlys)
                else:
                    fullquotes = add_quotes(fullbraks)

                #                       PRINT("\nfullbraks:%s\n"%fullbraks)
                #                       PRINT("\nfullquotes:%s\n"%fullquotes)

                protolist = to_list(fullquotes)
                actualist = make_list(protolist)

                return (actualist, curlys)
            except Exception as e:
                print("-Trinitty Error:", str(e))
                return ("~PARSE~ERR~", None)
        else:
            return (False, None)

    #    def putback_curly(str_to_check,dict):
    #        for k,i in dict.items():
    #            if k in str_to_check:
    #                str_to_check = str_to_check.replace(k,i)
    #        return(str_to_check)

    def extract_curly(str_to_check):

        #        PRINT("\nstr_to_check:\n",str_to_check)
        def rnd_str(str_to_check, curly_dict):
            while True:
                characters = string.ascii_letters + string.digits
                rnd = Non_Crypto_Token(5, characters)
                if rnd not in curly_dict and rnd not in str_to_check:
                    return rnd

        curly_dict = {}
        while True:
            start = False
            end = False

            for n, c in enumerate(str_to_check):
                if c == "{" and not start and not end:
                    start = n
                if c == "}" and start and not end:
                    end = n + 1
                if start and end:
                    break

            curly = str_to_check[start:end]
            marker = rnd_str(str_to_check, curly_dict)

            if "," in curly:
                curly = curly.replace("{", "").replace("}", "").split(",")
            else:
                curly = curly.replace("{", "").replace("}", "")

            curly_dict[marker] = curly
            str_to_check = str_to_check[:start] + str(marker) + str_to_check[end:]

            if "{" not in str_to_check and "}" not in str_to_check:
                break

        #    print("\nwithout curly:",str_to_check)
        #    print("\ncurly_dict:")

        #    for i,j in curly_dict.items():
        #        print("%s type= %s:%s"%(i,type(i),j))
        return (str_to_check, curly_dict)

    def Unfold_cmd(cmd_lst, curlys):

        unfolded = []

        for lst in cmd_lst:
            tmp_lst = []

            for item in lst:
                skip = False

                for k, i in curlys.items():
                    if k in item:

                        skip = True
                        if isinstance(i, list):
                            for j in i:
                                tmp_lst.append(item.replace(k, j))
                        else:
                            tmp_lst.append(item.replace(k, i))

                        break
                if not skip:
                    tmp_lst.append(item)

            unfolded.append(tmp_lst)

        for lst in unfolded:
            for item in lst:
                for k in curlys:
                    if k in item:
                        return Unfold_cmd(unfolded, curlys)

        return unfolded

    def join_and_replace(tojoin):
        joined = "".join(tojoin)
        if "  " in joined:
            replaced = joined
            while True:
                replaced = replaced.replace("  ", " ")
                if "  " not in replaced:
                    joined_and_replaced = replaced
                    break
        #                 else:
        #                      print("replaced:",replaced)
        #                      input("")
        else:
            joined_and_replaced = joined

        return joined_and_replaced

    parsed_cmd, curlys = parse_cmd(txt)

    if parsed_cmd:
        final_list = []
        if parsed_cmd == "~PARSE~ERR~":
            PRINT("\n-Trinitty:Special_Syntax():~PARSE~ERR~:txt:\n%s\n" % txt)
            return None
        #         PRINT("\ntxt:\n%s\n"%txt)
        #         PRINT("\nparsed_cmd:\n%s\n"%parsed_cmd)
        if curlys:
            #             PRINT("\n-Trinitty:curlys is full:")
            #             for i,j in curlys.items():
            #                 PRINT("%s:%s"%(i,j))
            unfolded = Unfold_cmd(parsed_cmd, curlys)
            prod = product(*unfolded)
            final_list = [join_and_replace(i) for i in prod]
            if globals().get("SYNTAX_DBG", False):
                PRINT("\n-Trinitty:Output Special Syntax for:\n%s\n\n%s" % (txt, final_list))
            return final_list
        prod = product(*parsed_cmd)
        final_list = [join_and_replace(i) for i in prod]
        if globals().get("SYNTAX_DBG", False):
            PRINT("\n-Trinitty:Output Special Syntax for:\n%s\n\n%s" % (txt, final_list))
        return final_list
    #        PRINT("no advanced syntax:\n",txt)
    return txt

    ##TODO sublvl etc ..
    # for n,p in enumerate(parsed_cmd):
    #   print("sending %s %s"%(n,p))
    #   markers = final_parse(p,pos_lst=n)

    # marker = final_parse(parsed_cmd)
    # print("\n\nfinal marker:")
    # for i,j in markers.items():print("%s:%s"%(i,j))

    # print("\nparsed_cmd:\n")
    # for n,i in enumerate(parsed_cmd):
    #    print("%s =  %s"%(n,i))
    # to_prod,markers = is_inner_lst(parsed_cmd)
    # sys.exit()

    # if markers:
    #    print("\nmarkers is full\n")
    #    prod = product(*parsed_cmd)
    #    for i in prod:
    #       print(i)
    # else:
    #    print("\n\nno markers final:\n")
    #    prod = product(*parsed_cmd)
    #    for i in prod:
    #       print(i)


def Load_Csv():

    global Loaded_History_List
    global Loaded_Trinitty_Name_Requests
    global Loaded_Trinitty_Mean_Requests
    global Loaded_Trinitty_Dev_Requests
    global Loaded_Trinitty_Script_Requests
    global Loaded_Trinitty_Help_Requests
    global Loaded_Prompt_Requests
    global Loaded_Rnd_Requests
    global Loaded_Read_Results
    global Loaded_Repeat_Requests
    global Loaded_Show_History_Requests
    global Loaded_Search_History_Requests
    global Loaded_Delete_Last_History_Requests
    global Loaded_Read_Link_Requests
    global Loaded_Play_Audio_File_Requests
    global Loaded_Search_Web_Requests
    global Loaded_Wait_Words_Requests
    global Loaded_Quit_Words_Requests
    global Loaded_Sort_Results_Requests
    global Loaded_Actions_Words_Requests
    global Loaded_Add_Triggers_Requests
    global Loaded_Mix_Actions_Functions
    global Loaded_Alternatives_Triggers
    global Loaded_Verbs_Words_List
    global Loaded_Synonyms_Words_List
    global Loaded_Mix_Functions_verbs

    Loaded_History_List = []
    Loaded_Trinitty_Name_Requests = []
    Loaded_Trinitty_Mean_Requests = []
    Loaded_Trinitty_Dev_Requests = []
    Loaded_Trinitty_Script_Requests = []
    Loaded_Trinitty_Help_Requests = []
    Loaded_Prompt_Requests = []
    Loaded_Rnd_Requests = []
    Loaded_Repeat_Requests = []
    Loaded_Show_History_Requests = []
    Loaded_Search_History_Requests = []
    Loaded_Delete_Last_History_Requests = []
    Loaded_Read_Results = []
    Loaded_Read_Link_Requests = []
    Loaded_Play_Audio_File_Requests = []
    Loaded_Search_Web_Requests = []
    Loaded_Wait_Words_Requests = []
    Loaded_Quit_Words_Requests = []
    Loaded_Sort_Results_Requests = []
    Loaded_Add_Triggers_Requests = []
    Loaded_Actions_Words_Requests = []
    Loaded_Mix_Actions_Functions = []
    Loaded_Alternatives_Triggers = []
    Loaded_Verbs_Words_List = []
    Loaded_Synonyms_Words_List = []
    Loaded_Mix_Functions_verbs = {}

    PRINT("\n-Trinitty:Dans la fonction Load_Csv .")

    hist_folder = History_Dir()
    if os.path.exists(hist_folder):
        hist_files = [f for f in os.listdir(hist_folder)]
        for file in hist_files:
            filepath = os.path.join(hist_folder, file)
            try:
                with open(filepath, newline="") as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        try:
                            hist_file = row["hist_file"]
                            hist_cats = row["hist_cats"]
                            hist_input_full = row["hist_input_full"]
                            hist_input_short = row["hist_input_short"]
                            hist_input_wav = row["hist_input_wav"]
                            hist_output = row["hist_output"]
                            hist_output_wav = row["hist_output_wav"]
                            hist_urls = row["hist_urls"]
                            hist_epok = row["hist_epok"]
                            hist_tstamp = row["hist_tstamp"]
                            Loaded_History_List.append(
                                {
                                    "hist_file":hist_file,
                                    "hist_cats":hist_cats,
                                    "hist_input_full":hist_input_full,
                                    "hist_input_short":hist_input_short,
                                    "hist_input_wav":hist_input_wav,
                                    "hist_output":hist_output,
                                    "hist_output_wav":hist_output_wav,
                                    "hist_urls":hist_urls,
                                    "hist_epok":hist_epok,
                                    "hist_tstamp":hist_tstamp,
                                }
                            )


                        except Exception as e:
                            print("\n-Trinitty:Error:loadcsv:file:%s %s" % (filepath, str(e)))
            #                      print("\nhist_file:\n",hist_file)
            #                      print("hist_cats:\n",hist_cats)
            #                      print("hist_txt:\n",hist_txt)
            #                      print("hist_answer:\n",hist_answer)
            #                      print("hist_epok:\n",hist_epok)
            #                      print("hist_tstamp:\n",hist_tstamp)
            #                      print("hist_wav:\n",hist_wav)
            except Exception as e:
                print("\n-Trinitty:Error:loadcsv:file:%s %s" % (filepath, str(e)))

    PRINT("\n-Trinitty:Loaded_History_List Loaded")

    if os.path.exists(SYNFILE):
        with open(SYNFILE, newline="") as f:
            data = f.readlines()

            for raw_line in data:
                tmplst = []
                parts = raw_line.strip().split(",")
                for part in parts:
                    if part != "":
                        tmplst.append(part)
                Loaded_Synonyms_Words_List.append(tmplst)

    else:

        return Missing_Runtime_File(SYNFILE)

    PRINT("\n-Trinitty:Loaded_Synonyms_Words_List Loaded")

    if os.path.exists(TRIFILE):
        with open(TRIFILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if "trigger" in row:
                    trigger = row["trigger"]
                else:
                    continue
                if trigger not in Loaded_Alternatives_Triggers:
                    Loaded_Alternatives_Triggers.append(trigger)

    else:

        return Missing_Runtime_File(TRIFILE)

    PRINT("\n-Trinitty:Loaded_Alternatives_Triggers Loaded")
    if os.path.exists(CMDFILE):
        with open(CMDFILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row_index, row in enumerate(reader):
                line_no = row_index + 2
                if "function" in row:
                    function = row["function"]
                    if "trigger" in row:
                        trigger = row["trigger"]
                    else:
                        continue
                    if function == "F_trinity_name":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Name_Requests.append(t)
                            else:
                                Loaded_Trinitty_Name_Requests.append(trigger)
                    elif function == "F_trinity_mean":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Mean_Requests.append(t)
                            else:
                                Loaded_Trinitty_Mean_Requests.append(trigger)
                    elif function == "F_trinity_dev":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Dev_Requests.append(t)
                            else:
                                Loaded_Trinitty_Dev_Requests.append(trigger)
                    elif function == "F_trinity_script":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Script_Requests.append(t)
                            else:
                                Loaded_Trinitty_Script_Requests.append(trigger)
                    elif function == "F_trinity_help":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Help_Requests.append(t)
                            else:
                                Loaded_Trinitty_Help_Requests.append(trigger)
                    elif function == "F_prompt":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Prompt_Requests.append(t)
                            else:
                                Loaded_Prompt_Requests.append(trigger)
                    elif function == "F_rnd":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Rnd_Requests.append(t)
                            else:
                                Loaded_Rnd_Requests.append(trigger)

                    elif function =="F_read_results":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Read_Results.append(t)
                            else:
                                Loaded_Read_Results.append(trigger)

                    elif function == "F_repeat":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Repeat_Requests.append(t)
                            else:
                                Loaded_Repeat_Requests.append(trigger)
                    elif function == "F_show_history":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Show_History_Requests.append(t)
                            else:
                                Loaded_Show_History_Requests.append(trigger)

                    elif function == "F_search_history":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Search_History_Requests.append(t)
                            else:
                                Loaded_Search_History_Requests.append(trigger)
                    elif function == "F_delete_last_history":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Delete_Last_History_Requests.append(t)
                            else:
                                Loaded_Delete_Last_History_Requests.append(trigger)
                    elif function == "F_read_link":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Read_Link_Requests.append(t)
                            else:
                                Loaded_Read_Link_Requests.append(trigger)
                    elif function == "F_play_audio":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Play_Audio_File_Requests.append(t)
                            else:
                                Loaded_Play_Audio_File_Requests.append(trigger)
                    elif function == "F_search_web":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Search_Web_Requests.append(t)
                            else:
                                Loaded_Search_Web_Requests.append(trigger)
                    elif function == "F_wait":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Wait_Words_Requests.append(t)
                            else:
                                Loaded_Wait_Words_Requests.append(trigger)

                    elif function == "F_quit":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Quit_Words_Requests.append(t)
                            else:
                                Loaded_Quit_Words_Requests.append(trigger)

                    elif function == "F_sort_results":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Sort_Results_Requests.append(t)
                            else:
                                Loaded_Sort_Results_Requests.append(trigger)

                    elif function == "F_add_trigger":
                        check_trigger = Special_Syntax(trigger, CMDFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Add_Triggers_Requests.append(t)
                            else:
                                Loaded_Add_Triggers_Requests.append(trigger)
    else:

        return Missing_Runtime_File(CMDFILE)
    PRINT("\n-Trinitty:CMDFILE Loaded")
    #print("Loaded_Read_Results:",Loaded_Read_Results)
    #if len(Loaded_Read_Results) == 0:
    #    exit()
    if os.path.exists(ACTFILE) and os.path.exists(PREFILE):
        with open(ACTFILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:

                if "verb" in row:
                    verb = row["verb"]
                else:
                    continue
                if "indicatif1" in row:
                    ind1 = row["indicatif1"]
                else:
                    continue
                if "indicatif2" in row:
                    ind2 = row["indicatif2"]
                else:
                    continue
                if "conditionnel1" in row:
                    cond1 = row["conditionnel1"]
                else:
                    continue
                if "conditionnel2" in row:
                    cond2 = row["conditionnel2"]
                else:
                    continue
                if "subjonctif1" in row:
                    sub1 = row["subjonctif1"]
                else:
                    continue
                if "subjonctif2" in row:
                    sub2 = row["subjonctif2"]
                else:
                    continue
                if "participe" in row:
                    participe = row["participe"]
                else:
                    continue
                if "suffix1" in row:
                    suffix1 = row["suffix1"]
                else:
                    continue
                if "suffix2" in row:
                    suffix2 = row["suffix2"]
                else:
                    continue
                if "suffix3" in row:
                    suffix3 = row["suffix3"]
                else:
                    continue
                if "functions" in row:
                    functions = row["functions"]
                #                      print("fnc:",functions)
                else:
                    continue

                if verb not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(verb)
                    Loaded_Verbs_Words_List.append(verb)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((verb, alf))
                            if alf not in Loaded_Mix_Functions_verbs:
                                Loaded_Mix_Functions_verbs[alf] = []
                            if verb not in Loaded_Mix_Functions_verbs[alf]:
                                Loaded_Mix_Functions_verbs[alf].append(verb)
                    else:
                        Loaded_Mix_Actions_Functions.append((verb, functions))
                        if functions not in Loaded_Mix_Functions_verbs:
                            Loaded_Mix_Functions_verbs[functions] = []
                        if verb not in Loaded_Mix_Functions_verbs[functions]:
                            Loaded_Mix_Functions_verbs[functions].append(verb)

                if ind1 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(ind1)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((ind1, alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((ind1, functions))

                if ind2 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(ind2)

                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((ind2, alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((ind2, functions))

                if cond1 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond1)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond1, alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((cond1, functions))

                if cond2 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond2)

                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond2, alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((cond2, functions))

                if sub1 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(sub1)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((sub1, alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((sub1, functions))

                if sub2 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(sub2)

                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((sub2, alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((sub2, functions))

                if participe not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(participe)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((participe, alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((participe, functions))

                if ind1 + suffix1 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(ind1 + suffix1)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((ind1 + suffix1, alf))
                            Loaded_Mix_Actions_Functions.append((ind1 + suffix1.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((ind1 + suffix1, functions))
                        Loaded_Mix_Actions_Functions.append((ind1 + suffix1.replace("-", " "), functions))

                if ind2 + suffix1 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(ind2 + suffix1)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((ind2 + suffix1, alf))
                            Loaded_Mix_Actions_Functions.append((ind2 + suffix1.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((ind2 + suffix1, functions))
                        Loaded_Mix_Actions_Functions.append((ind2 + suffix1.replace("-", " "), functions))

                if cond1 + suffix2 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond1 + suffix2)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond1 + suffix2, alf))
                            Loaded_Mix_Actions_Functions.append((cond1 + suffix2.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((cond1 + suffix2, functions))
                        Loaded_Mix_Actions_Functions.append((cond1 + suffix2.replace("-", " "), functions))

                if cond2 + suffix3 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond2 + suffix3)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond2 + suffix3, alf))
                            Loaded_Mix_Actions_Functions.append((cond2 + suffix3.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((cond2 + suffix3, functions))
                        Loaded_Mix_Actions_Functions.append((cond2 + suffix3.replace("-", " "), functions))

                if cond1 + suffix2 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond1 + suffix2)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond1 + suffix2, alf))
                            Loaded_Mix_Actions_Functions.append((cond1 + suffix2.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((cond1 + suffix2, functions))
                        Loaded_Mix_Actions_Functions.append((cond1 + suffix2.replace("-", " "), functions))

                if cond2 + suffix3 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond2 + suffix3)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond2 + suffix3, alf))
                            Loaded_Mix_Actions_Functions.append((cond2 + suffix3.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((sub2 + suffix3, functions))
                        Loaded_Mix_Actions_Functions.append((sub2 + suffix3.replace("-", " "), functions))

                if cond1 + suffix2 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond1 + suffix2)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond1 + suffix2, alf))
                            Loaded_Mix_Actions_Functions.append((cond1 + suffix2.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((cond1 + suffix2, functions))
                        Loaded_Mix_Actions_Functions.append((cond1 + suffix2.replace("-", " "), functions))

                if cond2 + suffix3 not in Loaded_Actions_Words_Requests:
                    Loaded_Actions_Words_Requests.append(cond2 + suffix3)
                    if "***" in functions:
                        allowed_fonctions = functions.split("***")
                        for alf in allowed_fonctions:
                            Loaded_Mix_Actions_Functions.append((cond2 + suffix3, alf))
                            Loaded_Mix_Actions_Functions.append((cond2 + suffix3.replace("-", " "), alf))
                    else:
                        Loaded_Mix_Actions_Functions.append((cond2 + suffix3, functions))
                        Loaded_Mix_Actions_Functions.append((cond2 + suffix3.replace("-", " "), functions))

                with open(PREFILE, newline="") as csvfile2:
                    reader2 = csv.DictReader(csvfile2)

                    for pref_row in reader2:
                        if "present1" in pref_row:
                            present1 = pref_row["present1"]
                        else:
                            continue
                        if "present2" in pref_row:
                            present2 = pref_row["present2"]
                        else:
                            continue
                        if "condi1" in pref_row:
                            cond1 = pref_row["condi1"]
                        else:
                            continue
                        if "condi2" in pref_row:
                            cond2 = pref_row["condi2"]
                        else:
                            continue

                        if not any("que" in var for var in [present1, present2, cond1, cond2]):
                            pre1 = present1 + "*" + verb
                            if pre1 not in Loaded_Actions_Words_Requests:
                                #                                    print(pres1)
                                Loaded_Actions_Words_Requests.append(pre1)
                                if "***" in functions:
                                    allowed_fonctions = functions.split("***")
                                    for alf in allowed_fonctions:
                                        Loaded_Mix_Actions_Functions.append((pre1, alf))
                                else:
                                    Loaded_Mix_Actions_Functions.append((pre1, functions))

                            pre2 = present2 + "*" + verb
                            if pre2 not in Loaded_Actions_Words_Requests:
                                #                                    print(pres2)
                                Loaded_Actions_Words_Requests.append(pre2)
                                if "***" in functions:
                                    allowed_fonctions = functions.split("***")
                                    for alf in allowed_fonctions:
                                        Loaded_Mix_Actions_Functions.append((pre2, alf))
                                else:
                                    Loaded_Mix_Actions_Functions.append((pre2, functions))

                            pre3 = cond1 + "*" + verb
                            if pre3 not in Loaded_Actions_Words_Requests:
                                #                                    print(pre3)
                                Loaded_Actions_Words_Requests.append(pre3)
                                if "***" in functions:
                                    allowed_fonctions = functions.split("***")
                                    for alf in allowed_fonctions:
                                        Loaded_Mix_Actions_Functions.append((pre3, alf))
                                else:
                                    Loaded_Mix_Actions_Functions.append((pre3, functions))

                            pre4 = cond2 + "*" + verb
                            if pre4 not in Loaded_Actions_Words_Requests:
                                #                                    print(pre4)
                                Loaded_Actions_Words_Requests.append(pre4)
                                if "***" in functions:
                                    allowed_fonctions = functions.split("***")
                                    for alf in allowed_fonctions:
                                        Loaded_Mix_Actions_Functions.append((pre4, alf))
                                else:
                                    Loaded_Mix_Actions_Functions.append((pre4, functions))

                        else:
                            pre1 = present1 + "*" + sub1
                            if pre1 not in Loaded_Actions_Words_Requests:
                                #                                    print(pres1)
                                Loaded_Actions_Words_Requests.append(pre1)
                                if "***" in functions:
                                    allowed_fonctions = functions.split("***")
                                    for alf in allowed_fonctions:
                                        Loaded_Mix_Actions_Functions.append((pre1, alf))
                                else:
                                    Loaded_Mix_Actions_Functions.append((pre1, functions))

                            pre2 = present2 + "*" + sub2
                            if pre2 not in Loaded_Actions_Words_Requests:
                                #                                    print(pres2)
                                Loaded_Actions_Words_Requests.append(pre2)
                                if "***" in functions:
                                    allowed_fonctions = functions.split("***")
                                    for alf in allowed_fonctions:
                                        Loaded_Mix_Actions_Functions.append((pre2, alf))
                                else:
                                    Loaded_Mix_Actions_Functions.append((pre2, functions))

        for k in Loaded_Mix_Functions_verbs:
            Loaded_Mix_Functions_verbs[k].append("pouvoir")
            Loaded_Mix_Functions_verbs[k].append("vouloir")
            Loaded_Mix_Functions_verbs[k].append("être")
            Loaded_Mix_Functions_verbs[k].append("falloir")
            Loaded_Mix_Functions_verbs[k].append("devoir")

    else:

        missing_files = [path for path in [ACTFILE, PREFILE] if not os.path.exists(path)]
        return Missing_Runtime_File(", ".join(missing_files))

    PRINT("\n-Trinitty:ACTFILE Loaded")

    if os.path.exists(ALTFILE):
        with open(ALTFILE, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row_index, row in enumerate(reader):
                line_no = row_index + 2

                if "function" in row:
                    function = row["function"]
                else:
                    continue

                if "trigger" in row:
                    trigger = row["trigger"]

                    if function == "F_trinity_name":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Name_Requests.append(t)
                            else:
                                Loaded_Trinitty_Name_Requests.append(trigger)
                    elif function == "F_trinity_mean":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Mean_Requests.append(t)
                            else:
                                Loaded_Trinitty_Mean_Requests.append(trigger)
                    elif function == "F_trinity_dev":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Dev_Requests.append(t)
                            else:
                                Loaded_Trinitty_Dev_Requests.append(trigger)
                    elif function == "F_trinity_script":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Script_Requests.append(t)
                            else:
                                Loaded_Trinitty_Script_Requests.append(trigger)
                    elif function == "F_trinity_help":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Trinitty_Help_Requests.append(t)
                            else:
                                Loaded_Trinitty_Help_Requests.append(trigger)
                    elif function == "F_prompt":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Prompt_Requests.append(t)
                            else:
                                Loaded_Prompt_Requests.append(trigger)
                    elif function == "F_rnd":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Rnd_Requests.append(t)
                            else:
                                Loaded_Rnd_Requests.append(trigger)
                    elif function == "F_repeat":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Repeat_Requests.append(t)
                            else:
                                Loaded_Repeat_Requests.append(trigger)
                    elif function == "F_show_history":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Show_History_Requests.append(t)
                            else:
                                Loaded_Show_History_Requests.append(trigger)

                    elif function == "F_search_history":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Search_History_Requests.append(t)
                            else:
                                Loaded_Search_History_Requests.append(trigger)
                    elif function == "F_delete_last_history":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Delete_Last_History_Requests.append(t)
                            else:
                                Loaded_Delete_Last_History_Requests.append(trigger)
                    elif function == "F_read_link":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Read_Link_Requests.append(t)
                            else:
                                Loaded_Read_Link_Requests.append(trigger)

                    elif function == "F_read_results":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Read_Results.append(t)
                            else:
                                Loaded_Read_Results.append(trigger)

                    elif function == "F_play_audio":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Play_Audio_File_Requests.append(t)
                            else:
                                Loaded_Play_Audio_File_Requests.append(trigger)
                    elif function == "F_search_web":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Search_Web_Requests.append(t)
                            else:
                                Loaded_Search_Web_Requests.append(trigger)
                    elif function == "F_wait":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Wait_Words_Requests.append(t)
                            else:
                                Loaded_Wait_Words_Requests.append(trigger)
                    elif function == "F_quit":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Quit_Words_Requests.append(t)
                            else:
                                Loaded_Quit_Words_Requests.append(trigger)



                    elif function == "F_sort_results":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Sort_Results_Requests.append(t)
                            else:
                                Loaded_Sort_Results_Requests.append(trigger)

                    elif function == "F_add_trigger":
                        check_trigger = Special_Syntax(trigger, ALTFILE, line_no)
                        if check_trigger:
                            if isinstance(check_trigger, list):
                                for t in check_trigger:
                                    Loaded_Add_Triggers_Requests.append(t)
                            else:
                                Loaded_Add_Triggers_Requests.append(trigger)
    else:

        return Missing_Runtime_File(ALTFILE)

    PRINT("\n-Trinitty:ALTFILE Loaded")
    return True
#    for his in Loaded_History_List:
#        print(his)
#        if action_trigger:
#            goto = PostProd(txt,func_name_toadd,specific_trigger=must_contain,main_trigger=action_trigger)
#        else:
#        goto = PostProd(txt, func_name_toadd, specific_trigger=must_contain)

#            valid = checktrigger(
#                new_trigger,
#                funcname,
#                specific_trigger=specific_trigger,
#                main_action=main_trigger,
#            )






def Add_Trigger(trigger_input=None, func_name_to_add=None, specific_trigger=None):

    print("\n-Trinitty:Dans la fonction Add_Trigger.\n")

    help_already_print = False
    help_already_ask = False

    functions_help = [
            (
                "Trinitty_Name()",
                "pour avoir le nom du script de Trinitty",
                "Salut ça va ?Comment tu t'appelle?",
                "comment * t'appelles",
                "[comment {tu t'appelles/vous vous appelez/t'appelles-tu/vous appelez-vous}/quel est {ton/votre} {nom/prénom}]",
                Loaded_Trinitty_Name_Requests,
                "F_trinity_name",
            ),
            (
                "Trinitty_Mean()",
                "pour avoir le sens du nom du script de Trinitty",
                "Pourquoi on a décidé de t'appeler comme ça?",
                "pourquoi *t'appeler comme ça",
                "pourquoi [t'a-t-on/on t'a] [nommé{e/}/appelé{e/}] [ainsi/comme ça/trinitty]",
                Loaded_Trinitty_Mean_Requests,
                "F_trinity_mean",
            ),
            (
                "Trinitty_Dev()",
                "pour connaitre le nom du créateur du script de Trinitty",
                "Qui est-ce qui t'a créé ?",
                "qui * t'a créé",
                "qui [est-ce qui/] [t'a/vous a] [créé{e/}/fabriqué{e/}/développé{e/}/conçu{e/}]",
                Loaded_Trinitty_Dev_Requests,
                "F_trinity_dev",
            ),
            (
                "Trinitty_Help()",
                "pour avoir l'aide du script Trinitty",
                "Affiche moi l'aide de ton script.",
                "affiche*moi *aide * ton script",
                "[montre{-/*/}/affiche{-/*/}] [moi/] [*/l']aide * [ton/votre/du] script [*trinitty/]",
                Loaded_Trinitty_Help_Requests,
                "F_trinity_help",
            ),
            (
                "Prompt()",
                "pour pouvoir écrire à Trinitty",
                "J'ai besoin de t'écrire un truc.",
                "ai * de t'écrire",
                "[{lance/ouvre} {l'interpreteur/le clavier}/j{'ai besoin de/e dois} t'écrire}]",
                Loaded_Prompt_Requests,
                "F_prompt",
            ),
            (
                "Trinitty_Script()",
                "pour afficher la source du script Trinitty",
                "tu peux me montrer ton code source?",
                "peux* montrer * ton code",
                "[montre/affiche][{-/ }moi] [{ton/votre/le} code source/la source {du */de *}{ trinitty/}]",
                Loaded_Trinitty_Script_Requests,
                "F_trinity_script",
            ),
            (
                "Rnd()",
                "pour effectuer un choix aléatoire",
                "Peux-tu faire un choix entre 1 et 2?",
                "peux*tu * choix entre * et ",
                "[peux{-/*/ }tu/pouvez{-/*/ }vous] * [choi{x/sir}] * entre * et ",
                Loaded_Rnd_Requests,
                "F_rnd",
            ),
            (
                "Repeat()",
                "pour demander à Trinitty de répéter",
                "J'ai rien compris tu peux me redire ça ?",
                "tu*peux* redire ça",
                "[{je n'/j'}ai {pas/rien} * compris] [peux{-/*/ }tu/pouvez{-/*/ }vous/tu peux/vous pouvez] répéter",
                Loaded_Repeat_Requests,
                "F_repeat",
            ),
            (
                "Show_History()",
                "pour faire afficher l'historique",
                "Tu peux m'afficher tout l'historique s'il te plaît?",
                "m'afficher * l'historique",
                "[montre/affiche/ouvre][{-/ }moi] l'historique",
                Loaded_Show_History_Requests,
                "F_show_history",
            ),
            (
                "Search_History()",
                "pour faire une recherche dans l'historique",
                "Regarde dans l'historique si tu trouve Albert Einstein",
                "regarde * l'historique * si * trouve",
                "[recherche{z/}/regarde{z/}/trouve{-/ }moi] * dans [ton/] l'historique",
                Loaded_Search_History_Requests,
                "F_search_history",
            ),
            (
                "Delete_Last_History_Entry()",
                "pour effacer la derniere entree de l'historique",
                "Efface la derniere entree de l'historique.",
                "efface * derniere * historique",
                "[efface/supprime/retire] [la/] derniere [entree/reponse] [de/] [l']historique",
                Loaded_Delete_Last_History_Requests,
                "F_delete_last_history",
            ),
            (
                "Read_Link()",
                "pour lire une page web",
                "Tu peux me lire ce qu'il y a dans cette page web?",
                "tu*peux* lire * dans * page web",
                "[{lis/dis}{ moi/-moi/}] [ce qu'il y a/] [sur/dans] [ce{tte page/ site/s pages}/ce site]",
                Loaded_Read_Link_Requests,
                "F_read_link",
            ),
            (
                "Read_Results()",
                "pour lire les résultats d'une recherche",
                "Dis-moi ce que tu as trouvé dans les résultats",
                "dis-moi * trouvé * les résultats",
                "[{lis/dis}{ moi/-moi/}] [ce qu'il y a/ce que {tu as/vous avez} trouv{é/ez}] dans les résultats]",
                Loaded_Read_Results,
                "F_read_results",
            ),
            (
                "Sort_Results()",
                "pour trier les résultats d'une recherche",
                "Trie les résultats par ordre chronologique.",
                "par ordre chronologique",
                "par ordre[ chronologique/ ant{é/i}chronologique]",
                Loaded_Sort_Results_Requests,
                "F_sort_results",
            ),
            (
                "Play_Audio()",
                "Pour lire un fichier audio",
                "Tu peux me jouer ce fichier audio s'il te plaît?",
                "tu*peux* jouer * fichier audio",
                "[{lis/joue}{ moi/-moi/}] [ce qu'il y a/] [sur/dans] [ce{s/} fichier{s/}] ",
                Loaded_Play_Audio_File_Requests,
                "F_play_audio",
            ),
            (
                "Search_Web()",
                "Pour faire une recherche sur internet",
                "Fais-moi une recherche sur google a propos du big bang",
                "fais*moi recherche * google * a propos",
                "[recherche{z/}/regarde{z/}/trouve{-/ }moi] * [dans/sur/avec] * [google/internet/wikipedia]",
                Loaded_Search_Web_Requests,
                "F_search_web",
            ),
            (
                "Wait()",
                "Pour demander à Trinitty d'attendre",
                "Minute papillon je ne suis pas près!",
                "Minute * je * suis pas près",
                "[attends{ moi/-moi/}/arrête] [*/] [je * suis pas près/]",
                Loaded_Wait_Words_Requests,
                "F_wait",
            ),
            (
                "Quit()",
                "Pour demander à Trinitty de quitter le programme ou la fonction en cours",
                "Non c'est bon tu peux quitter Trinitty.",
                "tu * quitter Trinitty",
                "[{tu peux /vous pouvez} {quitter/partir} Trinit{y/i/ie}]",
                Loaded_Quit_Words_Requests,
                "F_quit",
            ),

            (
                "Add_Trigger()",
                "Pour ajouter un nouveau déclencheur de fonction",
                "j'aimerai ajouter un nouveau trigger.",
                "ajouter * nouveau * trigger",
                "[ajoute{r/z/} * [des/un/] [nouveau{x/}/nouvel{les/}] [déclencheur/activateur/trigger]",
                Loaded_Add_Triggers_Requests,
                "F_add_trigger",
            ),
        ]



    def print_help_with_syntax(choice_input):


        try:
           choice_input = int(choice_input)
        except ValueError:
          for index, (_,_,_, _, _, _, function_name) in enumerate(functions_help, start=1):
                     if function_name == choice_input:
                          choice_input = index
                          break
          try:
             choice_input = int(choice_input)
          except Exception as e:
             print("\n-Trinitty:print_help_with_syntax():Error:%s"%str(e))
             return None

        if choice_input < 1 or choice_input > len(functions_help):
            print("\n-Trinitty:print_help_with_syntax():invalid choice:%s" % str(choice_input))
            return None

        function_to_print = functions_help[choice_input - 1][0]
        function_description = functions_help[choice_input - 1][1]
        function_ex1 = functions_help[choice_input - 1][2]
        function_ex2 = functions_help[choice_input - 1][3]
        function_ex3 = functions_help[choice_input - 1][4]
        function_requests = functions_help[choice_input - 1][5]
        function_id_name = functions_help[choice_input - 1][6]


        if help_already_print:
            print(f"Vous avez choisi {function_to_print}: {function_description}")
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/prompt/2.wav")
            return(function_to_print)
        print(f"Vous avez choisi {function_to_print}: {function_description}")
        Play_Audio_File("%s/local_sounds/cmd/instruction.wav" % SCRIPT_PATH)


        print("\n\n\n\n")
        print("==Ajouter un nouveau déclencheur pour la fonction: %s =="%function_to_print)
        print("\n\n\n-Gardez la partie qui identifie l'action %s dans votre phrase."%function_description)
        print("\n-Par example si votre phrase complète ressemble à ceci:\n\n\t-",function_ex1)
        print("\n-J'aimerais que vous ne gardiez que cela:\n\n\t-", function_ex2)
        print("\n-Le symbole * est utilisé içi afin de ne pas tenir compte des mots qu'il peut y avoir à cette position.\n\n")
        print("\n\n-Voici les déclencheurs déjà enregistrés pour cette fonction:\n")

        if len(function_requests) > 25:

            first = function_requests[:10]
            left = len(function_requests) - 20
            last = function_requests[-10:]

            for n, i in enumerate(first):
                 print("\t%s-:%s" % (n, i))

            print("\n\t...(+ %s déclencheurs)..."%str(left))
            print("\t(Liste compléte dans %s et %s)\n"%(CMDFILE,ALTFILE))
            for n, i in enumerate(last,start=len(function_requests)-10):
                 print("\t%s-:%s" % (n, i))
        else:
             for n, i in enumerate(function_requests):
                 print("\t%s-:%s" % (n, i))

        if function_id_name in Loaded_Mix_Functions_verbs:
             print("\n\n-Voici la liste de verbes déjà associés à cette fonction:\n")
             for n, f in enumerate(Loaded_Mix_Functions_verbs[function_id_name]):
                        print("\t%s-:%s" % (n, f))
        else:
             PRINT("\n-Trinitty:print_help_with_syntax():%s not in Loaded_Mix_Functions_verbs:"%function_id_name)
             for k in Loaded_Mix_Functions_verbs:
                 PRINT("-%s"%k)
             PRINT("\n-Trinitty:But not:%s"%function_id_name)

        print("\n-Si votre phrase utilise l'un de ces verbes même sous une forme conjugué il n'est pas nécessaire de l'écrire.")
        print("\n-Vous pouvez néanmoins le faire si vous souhaitez que votre déclencheur soit plus précis.\n")
        print("\n-Les caractéres spéciaux et ponctuations sont automatiquement enlevés.\n")
        print("\n-Il est aussi possible de générer plusieurs déclencheurs en même temps en utilisant la syntaxe avancée par exemple:\n")
        special_ex = Special_Syntax(function_ex3, SCRIPT_PATH+"/trinitty.py", Get_Line)
        for t in special_ex:
            print("-\t%s"%t)
        print("\n-Tous ces déclencheurs ont été générés par cette commande:\n\n-\t%s"%(function_ex3))
##
        print("\n\n-Les symboles '[' et ']' servent à créer une liste d'éléments séparé par le symbole '/'.")
        print("-Les symboles '{' et '}' sont utilisés dans une liste pour créer une sous-liste d'éléments séparé par le symbole '/'.\n")

        return(function_id_name)

    def checktrigger(to_check, funcname, s_syntax=None):

        def has_syn(function_name, sentences, altlst=None):
            synlst = []
            syntoprint = []
            found_syn = []

            if altlst:
                for act in altlst:
                    synlst.append(act)
            else:
                for syn in Loaded_Mix_Actions_Functions:
                    act = syn[0]
                    fn = syn[1]
                    if fn == function_name:
                        # print("adding:",act)
                        synlst.append(act)
                        for v in Loaded_Verbs_Words_List:
                            if v in act and v not in syntoprint:
                                syntoprint.append(v)


            check_sentences = Special_Syntax(sentences, SCRIPT_PATH + "/trinitty.py", Get_Line())
            if not check_sentences:
                return(False)

            if isinstance(check_sentences, list):
                 for sentence in check_sentences:
                      found = SeeknReturn(sentence, synlst)
                      if found:
                         found_syn.append(found)
            else:
                 found = SeeknReturn(sentences, synlst)
                 if found:
                         found_syn.append(found)

            if len(found_syn) == 0:
                Play_Audio_File("%s/local_sounds/cmd/triggers/atleast.wav" % (SCRIPT_PATH))
                if not altlst:
                    print(
                        "\n-Trinitty:Votre phrase doit contenir au minimum l'un des mots suivant:\n\n%s\n\n"
                        % (syntoprint)
                    )
                    return False
                print(
                    "\n-Trinitty:Votre phrase doit contenir au minimum l'un des mots suivant:\n\n%s\n\n" % (altlst)
                )
                return False
            return True

        def minitts(tx, fname):

            try:

                client = tts.TextToSpeechClient()
                audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)

                text_input = tts.SynthesisInput(text=tx)
                voice_params = tts.VoiceSelectionParams(language_code="fr-FR", name="fr-FR-Neural2-A")

                response = client.synthesize_speech(input=text_input, voice=voice_params, audio_config=audio_config)
                audio_response = response.audio_content
                try:
                    with open("%s/local_sounds/cmd/triggers/%s" % (SCRIPT_PATH, fname), "wb") as out:
                        out.write(audio_response)
                except Exception as e:
                    PRINT("\n-Trinitty:Error:%s" % str(e))
            except Exception as e:
                PRINT("\n-Trinitty:Error:%s" % str(e))

        def getwav(f, trigparts):


            function_wav = "%s/local_sounds/cmd/triggers/%s.wav"%(SCRIPT_PATH, f)

            if os.path.exists(function_wav):
                Play_Audio_File(function_wav)
            else:
                PRINT("\n-Trinitty:Error getwav(): %s n'existe pas." % function_wav)
                return()

            to_rm = [" ","_","-","*","'"]
            for trigpart in trigparts:
                normalized_trigpart = unidecode(trigpart.replace(" ", "_").replace("-", "_").replace("*", "_").replace("'", "_"))
                wavname = normalized_trigpart + ".wav"
                while True:
                    if wavname[0] in to_rm:
                       wavname = wavname[1:]
                    else:
                       break
                while True:
                   if "__" in wavname:
                        wavname = wavname.replace("__","_")
                   else:
                        break

                if os.path.exists("%s/local_sounds/cmd/triggers/%s" % (SCRIPT_PATH, wavname)):
                    Play_Audio_File("%s/local_sounds/cmd/triggers/%s" % (SCRIPT_PATH, wavname))
                else:
                    print(
                        "\n-Trinitty:Error Wave file not found:%s/local_sounds/cmd/triggers/%s" % (SCRIPT_PATH, wavname)
                    )
                    minitts(t, wavname)
                    if os.path.exists("%s/local_sounds/cmd/triggers/%s" % (SCRIPT_PATH, wavname)):
                        Play_Audio_File("%s/local_sounds/cmd/triggers/%s" % (SCRIPT_PATH, wavname))
            return ()

    ################################################
        if isinstance(to_check,list) and s_syntax:
            trigger_cmd = s_syntax
        else:

            trigger_cmd = to_check


        if specific_trigger:
            mandatory_trigger = has_syn(funcname,to_check,specific_trigger)

            if not mandatory_trigger:
                    return(False)



        ambiguity = Check_Ambiguity(to_check,to_match=func_name_to_add)

        if not ambiguity:

            if ambiguity is None:
                  PRINT("\n-Trinitty:Add_Trigger():Check_Ambiguity():Main cmd trigger:None.")

            elif ambiguity is False:
                 PRINT("\n-Trinitty:Add_Trigger():Check_Ambiguity():len(ambiguity) == 0")

            print("\n-Parfait,cette phrase semble déclencher la fonction:", funcname)
            Play_Audio_File("%s/local_sounds/cmd/valid.wav" % SCRIPT_PATH)
            Play_Audio_File("%s/local_sounds/cmd/save.wav" % SCRIPT_PATH)
            while True:
                rusure = input(
                    "\n-Sauvegarder cette phrase dans la base de données ?:\n\n%s\n\n-Votre choix:(oui/non/abandonner):"
                    % trigger_cmd
                ).lower()
                if rusure in ["oui", "non", "abandonner"]:
                    if rusure == "oui":
                        if isinstance(to_check,list):
                             for trigger in to_check:
                                 Write_csv(trigger, funcname, ALTFILE)
                        else:
                                Write_csv(to_check, funcname, ALTFILE)
                        return True
                    if rusure == "non":
                        return False
                    if rusure == "abandonner":
                        return True

        else:

            Play_Audio_File("%s/local_sounds/cmd/new_ambiguity.wav" % SCRIPT_PATH)

            print("\n-Cette phrase à déclenchée plusieurs commandes en même temps:\n%s\n" % trigger_cmd)

            for fnc, trigged in ambiguity.items():
                for t, p in trigged:
                    if s_syntax:
                        print("\n\n-Déclencheur généré:\n%s\n" % t)
                    print("\n-La fonction %s est déclenchée par cette partie: %s" % (fnc, p))
                if not s_syntax:
                    getwav(fnc, p)

            Play_Audio_File("%s/local_sounds/cmd/new_ambiguity2.wav" % SCRIPT_PATH)
            return None

##########################################################################
    if not trigger_input and not func_name_to_add and not specific_trigger:

        Play_Audio_File("%s/local_sounds/question/newtrigger.wav" % SCRIPT_PATH)


        for index, (function_name, function_description, _, _, _,_,_) in enumerate(functions_help, start=1):
            print(f"({index}) {function_name} :  {function_description}")

        while True:
            try:
                user_choice = int(input(f"\nChoisissez une fonction (1 à {len(functions_help)}): "))
                if user_choice in range(1, len(functions_help) + 1):
                    break
            except Exception as e:
                PRINT("\n-Trinitty:Ask_To_Add:invalid function choice:%s" % str(e))
                continue

        while True:

            selected_function = print_help_with_syntax(user_choice)
            if not selected_function:
                return None
            help_already_print = True

            new_trigger = input("\n-Nouveau déclencheur pour la fonction %s :" % selected_function)
            checksyntax = Special_Syntax(new_trigger, SCRIPT_PATH + "/trinitty.py", Get_Line())
            if not checksyntax:
                while True:
                    new_trigger = input("\n-Nouveau déclencheur pour la fonction %s :" % selected_function)
                    checksyntax = Special_Syntax(new_trigger, SCRIPT_PATH + "/trinitty.py", Get_Line())
                    if checksyntax:
                        break
            if isinstance(checksyntax, list):
                valid = checktrigger(checksyntax, selected_function, new_trigger)
            else:
                valid = checktrigger(checksyntax, selected_function)

            if valid:
                return selected_function

    #  if trigger_input and func_name_to_add and specific_trigger:
    else:

        while True:
            print("\n\n===============\n\n")

            if not help_already_ask:
                Play_Audio_File("%s/local_sounds/cmd/question_trigger.wav" % SCRIPT_PATH)
                while True:
                    helpme = input(
"-Pouvez-vous m'aider à mieux intégrer cette phrase dans ma base de données?\n-Cela ne prendra pas longtemps.\n\nVotre Choix (oui/non):"
                    ).lower()
                    if helpme in ["oui", "non"]:
                        if "oui" in helpme:
                            helpme = True
                            help_already_ask = True
                        else:
                            helpme = False
                        break
            else:
                helpme = True

            if helpme:

                selected_function = print_help_with_syntax(func_name_to_add)
                if not selected_function:
                    return None
                help_already_print = True

                print("\n-Trinitty:Voici votre phrase initial:\n%s\n"%trigger_input)


                new_trigger = input("\nNouvelle déclencheur pour la fonction %s :" % func_name_to_add)

                checksyntax = Special_Syntax(new_trigger, SCRIPT_PATH + "/trinitty.py", Get_Line())
                if not checksyntax:
                     while True:
                         new_trigger = input("\n-Nouveau déclencheur pour la fonction %s :" % selected_function)
                         checksyntax = Special_Syntax(new_trigger, SCRIPT_PATH + "/trinitty.py", Get_Line())
                         if checksyntax:
                             break

                if isinstance(checksyntax, list):
                     valid = checktrigger(checksyntax, func_name_to_add, new_trigger)
                else:
                     valid = checktrigger(checksyntax, func_name_to_add)

                if valid:
                    return func_name_to_add
            else:
                Play_Audio_File("%s/local_sounds/cmd/sorry.wav" % SCRIPT_PATH)
                Write_csv(trigger_input, func_name_to_add, ALTFILE)
                return func_name_to_add


def Get_Line():
    try:
        frame = inspect.currentframe()
        return frame.f_back.f_lineno
    except Exception as e:
        PRINT("-Trinitty:Error:Get_Line():%s" % str(e))
        return 0


def SeeknReturn(var_to_check, list_elements):
    #          PRINT("\n-Trinitty:Dans la fonction seeknreturn")
    final_found = []
    found_lst = []
    for element in list_elements:
        if "*" in element:
            splited = element.split("*")
            all_inside = all(e in var_to_check for e in splited)
            if all_inside:
                #                      for s in splited:
                #                          found_lst.append(s)
                found_lst.append(element)
        if element in var_to_check:
            found_lst.append(element)
    if found_lst:
#          print("list_elements:",list_elements)
#          print("found_lst:",found_lst)
          for found in found_lst:
               orig_found = found
#               print("orig_found:",orig_found)
               found_parts = re.split(r'\W+', found)
               found_parts = [f for f in found_parts if f]
#               print("found after split:",found)
               bingo = []
               for word in re.split(r'\W+', var_to_check):
                   for f in found_parts:
                       if f == word:
                          bingo.append(f)
#               print("bingo:",bingo)
#               print("found:",found)

               if any(
                   bingo[i:i + len(found_parts)] == found_parts
                   for i in range(len(bingo) - len(found_parts) + 1)
               ):
                    final_found.append(orig_found)

    return final_found


def Detect_Web_Search_Request(txt):
    try:
        query = Normalize_Search_Query_Text(txt)
    except Exception as e:
        Log_Error("Detect_Web_Search_Request", e)
        query = str(txt or "").lower()
    query = query.replace("'", " ")
    query = re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", query)
    query = re.sub(r"\s+", " ", query).strip()

    if not query or re.search(r"\b(historique|history)\b", query):
        return False

    has_web_scope = re.search(r"\b(internet|google|web|wikipedia|wiki)\b", query)
    if not has_web_scope:
        return False

    has_search_noun = re.search(r"\brecherches?\b", query)
    has_search_verb = re.search(
        r"\b(cherche|cherches|cherchez|chercher|recherche|recherches|recherchez|rechercher|trouve|trouves|trouvez|trouver|regarde|regardes|regardez|regarder|verifie|verifies|verifiez|verifier|consulte|consultez|consulter|fais|faire|lance|lancer)\b",
        query,
    )
    return bool(has_search_noun or has_search_verb)


def Disambiguify(ambiguities, txt):

    PRINT("\n-Trinitty:Disambiguify()")

    def bestvalue(dictionary, ordered):
        if not dictionary:
            return False
        values = [dictionary[key] for key in ordered]
        max_value = max(values)
        count_max_value = values.count(max_value)
        if count_max_value == 1:
            return ordered[values.index(max_value)]
        return False

    def bonuspoint(txt, function_tomatch):

        bonus = 0
        bonusyn = 0
        print("\n-Trinitty:function_tomatch:%s" % function_tomatch)
        for af in Loaded_Mix_Actions_Functions:
            action = af[0]
            function = af[1]

            if action in txt and function == function_tomatch:
                PRINT("Bonus point +1 %s in txt and %s is matching %s" % (action, function, function_tomatch))
                bonus += 1

                for syn_group in Loaded_Synonyms_Words_List:
                    for synonym in syn_group:
                        if synonym in txt:
                            for newsyn in syn_group:

                                newtxt = txt.replace(synonym, newsyn)

                                get_triggers = Check_Ambiguity(newtxt, to_get=function_tomatch)

                                if get_triggers:
                                    bonusyn = len(get_triggers[function_tomatch][1])

                                bonusyn += len(SeeknReturn(newtxt, Loaded_Alternatives_Triggers))

                                bonus += bonusyn

        return bonus

    fnc_to_add = None
    trigger_words_toadd = None
    must_contain = None

    score_function = {}
    triggered_parts = {}

    for function_name, seek_results in ambiguities.items():
        for result in seek_results:
            triggers_found = result[1]

#            bonus = bonuspoint(txt, function_name)
            bonus = 0
            score_function[function_name] = len(triggers_found) + bonus
            triggered_parts[function_name] = triggers_found

    sorted_score = dict(sorted(score_function.items(), key=lambda item: item[1], reverse=True))

    ordered_list = list(dict(sorted(score_function.items(), key=lambda item: item[1], reverse=True)).keys())

    winner = bestvalue(sorted_score, ordered_list)

    if winner:

        PRINT("\n-Trinitty:%s has the higher confidence score.\n" % winner)
        for _n, (fnc) in enumerate(ordered_list):
            PRINT(
                "\n-Trinitty:Commande:%s\n-Déclenchée par %s parties:%s\n-Score de Confiance:%s"
                % (
                    fnc,
                    len(triggered_parts[fnc]),
                    triggered_parts[fnc],
                    score_function[fnc],
                )
            )

        return winner
    print("\n\n===============\n\n\n-Trinitty:Cette phrase à déclenchée plusieurs commandes en même temps:")
    print("\n-Trinitty:Votre phrase:", txt)

    Play_Audio_File(SCRIPT_PATH + "/local_sounds/cmd/ambiguty.wav")

    while True:
        for n, (fnc) in enumerate(ordered_list):
            print(
                "\n-Trinitty:Commande:%s\n-Déclenchée par %s parties:%s\n-Score de Confiance:%s"
                % (
                    fnc,
                    len(triggered_parts[fnc]),
                    triggered_parts[fnc],
                    score_function[fnc],
                )
            )
            print("\n==\n-Trinitty:Pour choisir cette commande (%s) tapez:%s\n==\n" % (fnc, n))

            if n + 1 == 1:
                Play_Audio_File("%s/local_sounds/cmd/intro_%s.wav" % (SCRIPT_PATH, fnc))
            elif n + 1 > 1 and n + 1 < len(ordered_list):
                Play_Audio_File("%s/local_sounds/cmd/%s.wav" % (SCRIPT_PATH, fnc))
            elif n + 1 == len(ordered_list):
                Play_Audio_File("%s/local_sounds/cmd/outro_%s.wav" % (SCRIPT_PATH, fnc))

        print("\n==\n-Trinitty:Pour choisir une autre fonction tapez:%s\n==\n" % len(sorted_score))

        print("\n==\n-Trinitty:Si ce n'était pas une commande tapez:%s\n==\n" % str(len(sorted_score) + 1))

        Play_Audio_File("%s/local_sounds/cmd/hit%s.wav" % (SCRIPT_PATH, str(len(sorted_score)+1)))

        response = input("\n-Trinitty:Choisissez la bonne réaction pour cette phrase:")
        try:
            #           if 1 == 1 :
            response = int(response.strip())
            if response > len(sorted_score) + 1:
                continue
            if response == len(sorted_score) + 1:
                return False
            if response == len(sorted_score):
                return Add_Trigger()
            fnc_to_add = ordered_list[response]
            PRINT("\n-Trinitty:Disambiguify():fnc_to_add:%s" % fnc_to_add)
            trigger_words_toadd = sorted_score[fnc_to_add]
            PRINT("\n-Trinitty:Disambiguify():trigger_words_toadd:%s" % trigger_words_toadd)
            must_contain = triggered_parts[ordered_list[response]]
            break
        except Exception as e:
            PRINT("\n-Trinitty:Disambiguify():response:error:%s"%str(e))

    if fnc_to_add and trigger_words_toadd and must_contain:

        print("\n-Trinitty:La fonction %s à été choisie pour cette phrase.\n" % fnc_to_add)

#        goto = PostProd(txt, func_name_toadd, specific_trigger=must_contain)

        goto = Add_Trigger(txt, fnc_to_add, must_contain)

        if goto:
            return goto
        return False
    if not fnc_to_add:
        PRINT("\n-Trinitty:Disambiguify():fnc_to_add is missing")
    if not trigger_words_toadd:
        PRINT("\n-Trinitty:Disambiguify():trigger_words_toadd is missing")
    if not must_contain:
        PRINT("\n-Trinitty:Disambiguify():must_contain is missing")
    return False


def Check_Ambiguity(txt_input,allowed_functions=None, to_match=None, to_get=None,from_function=None):
    _ = from_function

    new_ambiguity = {}
    main_check = False

    if isinstance(txt_input, list):
        PRINT("\n-Trinitty:Check_Ambiguity():Verification d'une liste de déclencheurs.")
        Triggers = txt_input
    else:
        PRINT("\n-Trinitty:Check_Ambiguity():Verification d'un déclencheur.")
        Triggers = [txt_input]

    for trigger in Triggers:

        PRINT("\n-Trinitty:Check_Ambiguity():vérification de:%s"%trigger)

        found_actions_triggers = SeeknReturn(trigger, Loaded_Actions_Words_Requests)  ##
        found_alt_triggers = SeeknReturn(trigger, Loaded_Alternatives_Triggers)  ##

        found_add_trigger = ("F_add_trigger", SeeknReturn(trigger, Loaded_Add_Triggers_Requests))

        found_trinitty_name = ("F_trinity_name", SeeknReturn(trigger, Loaded_Trinitty_Name_Requests))

        found_trinitty_mean = ("F_trinity_mean", SeeknReturn(trigger, Loaded_Trinitty_Mean_Requests))

        found_trinitty_dev = ("F_trinity_dev", SeeknReturn(trigger, Loaded_Trinitty_Dev_Requests))

        found_trinitty_script = ("F_trinity_script", SeeknReturn(trigger, Loaded_Trinitty_Script_Requests))

        found_trinitty_help = ("F_trinity_help", SeeknReturn(trigger, Loaded_Trinitty_Help_Requests))

        found_prompt = ("F_prompt", SeeknReturn(trigger, Loaded_Prompt_Requests))

        found_rnd = ("F_rnd", SeeknReturn(trigger, Loaded_Rnd_Requests))

        found_repeat = ("F_repeat", SeeknReturn(trigger, Loaded_Repeat_Requests))

        found_read_results = ("F_read_results",SeeknReturn(trigger, Loaded_Read_Results))

        found_show_history = ("F_show_history",SeeknReturn(trigger, Loaded_Show_History_Requests))

        found_search_history = ("F_search_history",SeeknReturn(trigger, Loaded_Search_History_Requests))

        found_delete_last_history = ("F_delete_last_history", SeeknReturn(trigger, Loaded_Delete_Last_History_Requests))

        found_search_web = ("F_search_web", SeeknReturn(trigger, Loaded_Search_Web_Requests))
        direct_search_web = Detect_Web_Search_Request(trigger)
        if direct_search_web:
            search_web_triggers = list(found_search_web[1])
            if "recherche*internet" not in search_web_triggers:
                search_web_triggers.append("recherche*internet")
            found_search_web = ("F_search_web", search_web_triggers)

        found_read_link = ("F_read_link", SeeknReturn(trigger, Loaded_Read_Link_Requests))

        found_play_audio = ("F_play_audio", SeeknReturn(trigger, Loaded_Play_Audio_File_Requests))

        found_wait = ("F_wait", SeeknReturn(trigger, Loaded_Wait_Words_Requests))

        found_quit = ("F_quit", SeeknReturn(trigger, Loaded_Quit_Words_Requests))

        found_sort = ("F_sort_results", SeeknReturn(trigger, Loaded_Sort_Results_Requests))

        PRINT("found_quit:%s" % (found_quit,))

        if allowed_functions:
             allowed_functions = list(dict.fromkeys(list(allowed_functions) + ["F_wait", "F_quit"]))
             Tmp_Found_Lists = [
                 found_add_trigger,
                 found_trinitty_name,
                found_trinitty_mean,
                found_trinitty_dev,
                found_trinitty_script,
                found_trinitty_help,
                found_prompt,
                found_rnd,
	                 found_repeat,
	                 found_show_history,
	                 found_search_history,
	                 found_delete_last_history,
	                 found_search_web,
                 found_read_link,
                 found_play_audio,
                found_wait,
                found_quit,
                found_sort,
                found_read_results,
            ]

#             Found_List = [f for f in Tmp_Found_Lists if f[0] in allowed_functions]
             Found_Lists = []
             for f in Tmp_Found_Lists:
                 if f[0] in allowed_functions:
#                      print("f[0] in allowed_functions::",f[0])
                      try:
                          if f[1]:
                              Found_Lists.append(f)
                      except Exception as e:
                          PRINT("\n-Trinitty:Check_Ambiguity():failed:Found_Lists:", str(e))
             PRINT("Found_List:%s" % Found_Lists)
        else:
             Found_Lists = [
                 found_add_trigger,
                 found_trinitty_name,
                 found_trinitty_mean,
                 found_trinitty_dev,
                 found_trinitty_script,
                 found_trinitty_help,
                 found_prompt,
                 found_rnd,
	                 found_repeat,
	                 found_show_history,
	                 found_search_history,
	                 found_delete_last_history,
	                 found_search_web,
                 found_read_link,
                 found_play_audio,
                 found_wait,
                 found_quit,
                 found_sort,
                 found_read_results,
             ]

        if found_actions_triggers or found_alt_triggers or direct_search_web:

            main_check = True

            for seek_tuple in Found_Lists:

                function_name = seek_tuple[0]
                triggers_found = seek_tuple[1]

                PRINT("function_name:%s triggers_found:%s"%(function_name,triggers_found))

                if to_match:
                    if triggers_found and to_match != function_name:
                        if function_name in new_ambiguity:
                            new_ambiguity[function_name].append((trigger, triggers_found))
                        else:
                            new_ambiguity[function_name] = [(trigger, triggers_found)]
                elif to_get:
                    if triggers_found and to_get == function_name:
                        if function_name in new_ambiguity:
                            new_ambiguity[function_name].append((trigger, triggers_found))
                        else:
                            new_ambiguity[function_name] = [(trigger, triggers_found)]
                else:
                    if triggers_found:
                        if function_name in new_ambiguity:
                            new_ambiguity[function_name].append((trigger, triggers_found))
                        else:
                            new_ambiguity[function_name] = [(trigger, triggers_found)]


    if main_check or to_get: # or to_match
        if len(new_ambiguity) > 0:
            PRINT("\n-Trinitty:Check_Ambiguity():main_check or to_get:new_ambiguity:\n%s"%new_ambiguity)
            return new_ambiguity

        PRINT("\n-Trinitty:Check_Ambiguity():main_check or to_get:failed:found_actions_triggers:\n%s"%found_actions_triggers)
        PRINT("\n-Trinitty:Check_Ambiguity():main_check or to_get:failed:found_alt_triggers:\n%s"%found_alt_triggers)
        return False
    PRINT("\n-Trinitty:Check_Ambiguity():main_check:%s or to_get:%s"%(main_check,to_get))
    return None



def Dbg_Search():

    PRINT("\n\n-Trinitty:Dans la fonction Dbg_Search()")
    while True:
         print("\n\t-1: F_search_history")
         print("\t-2: F_search_web")
         user_input = input("\n-Trinitty:Dbg_Search():Choix fonction [1/2]:")
         if user_input == "1":
            user_input = "F_search_history"
            break
         if user_input == "2":
             user_input = "F_search_web"
             break
    txt_input = input("\n-Trinitty:Dbg_Search():Phrase à verifier:")
    output = Isolate_Search(txt_input, user_input)
    print("\n-Trinitty:Dbg_Search():Output:%s"%output)
    return Dbg_Search()




def Dbg_Input():
    PRINT("\n-Trinitty:Dans la fonction Dbg_Input()")
    user_input = input("\n-Trinitty:Dbg_Input():Comment puis-je vous aider ?:")
    if len(str(user_input)) > 0:

            cmd = Commandes(user_input)
            if not cmd:
                print("\n-Trinitty:Dbg_Input():Pas de cmd")
                return Dbg_Input()
            print("\n-Trinitty:Dbg_Input():commande:%s"%cmd)
            return Dbg_Input()
    print("\n-Trinitty:Dbg_Input():Pas d'input")
    return Dbg_Input()


def Command_Classifier_Command_Texts():
    command_lists = [
        Loaded_Actions_Words_Requests,
        Loaded_Alternatives_Triggers,
        Loaded_Add_Triggers_Requests,
        Loaded_Trinitty_Name_Requests,
        Loaded_Trinitty_Mean_Requests,
        Loaded_Trinitty_Dev_Requests,
        Loaded_Trinitty_Script_Requests,
        Loaded_Trinitty_Help_Requests,
        Loaded_Prompt_Requests,
        Loaded_Rnd_Requests,
        Loaded_Repeat_Requests,
        Loaded_Show_History_Requests,
        Loaded_Search_History_Requests,
        Loaded_Delete_Last_History_Requests,
        Loaded_Search_Web_Requests,
        Loaded_Read_Link_Requests,
        Loaded_Play_Audio_File_Requests,
        Loaded_Wait_Words_Requests,
        Loaded_Quit_Words_Requests,
        Loaded_Sort_Results_Requests,
        Loaded_Read_Results,
    ]
    command_texts = []
    for command_list in command_lists:
        for raw_command_text in command_list:
            command_text = str(raw_command_text or "").strip()
            if command_text:
                command_texts.append(command_text.replace("*", " "))
    return list(dict.fromkeys(command_texts))


def Command_Classifier_Training_Samples(command_texts=None, negative_texts=None):
    if command_texts is None:
        command_texts = Command_Classifier_Command_Texts()
    if negative_texts is None:
        negative_texts = [
            "bonjour",
            "merci",
            "raconte moi quelque chose",
            "je ne sais pas",
            "non rien",
            "d'accord",
        ]

    samples = []
    for raw_text in command_texts:
        text = str(raw_text or "").strip()
        if text:
            samples.append((text, 1))
    for raw_text in negative_texts:
        text = str(raw_text or "").strip()
        if text:
            samples.append((text, 0))
    return samples


def Train_Command_Classifier(command_texts=None, negative_texts=None, model_path=None, epochs=20):
    global COMMAND_CLASSIFIER_MODEL

    if not Dependency_Available(tensorflow):
        Log_Error("Train_Command_Classifier", "tensorflow missing")
        return None

    samples = Command_Classifier_Training_Samples(command_texts, negative_texts)
    if not samples:
        return None

    texts = [text for text, _label in samples]
    labels = [label for _text, label in samples]
    vectorizer = tensorflow.keras.layers.TextVectorization(max_tokens=2000, output_sequence_length=24)
    vectorizer.adapt(texts)
    model = tensorflow.keras.Sequential(
        [
            vectorizer,
            tensorflow.keras.layers.Embedding(2000, 16),
            tensorflow.keras.layers.GlobalAveragePooling1D(),
            tensorflow.keras.layers.Dense(16, activation="relu"),
            tensorflow.keras.layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
    model.fit(texts, labels, epochs=int(epochs), verbose=0)

    if model_path is None:
        model_path = globals().get("COMMAND_CLASSIFIER_MODEL_PATH", "")
    if model_path:
        model.save(model_path)

    COMMAND_CLASSIFIER_MODEL = model
    return model


def Load_Command_Classifier_Model(model_path=None):
    global COMMAND_CLASSIFIER_MODEL

    if not Dependency_Available(tensorflow):
        return None
    if model_path is None:
        model_path = globals().get("COMMAND_CLASSIFIER_MODEL_PATH", "")
    model_path = str(model_path or "").strip()
    if not model_path or not os.path.exists(model_path):
        return None
    COMMAND_CLASSIFIER_MODEL = tensorflow.keras.models.load_model(model_path)
    return COMMAND_CLASSIFIER_MODEL


def Command_Classifier_Predict(text, model=None):
    if model is None:
        model = globals().get("COMMAND_CLASSIFIER_MODEL", None)
    if model is None:
        model = Load_Command_Classifier_Model()
    if model is None:
        return None
    prediction = model.predict([str(text or "")], verbose=0)
    return float(prediction[0][0])


def Command_Classifier_Allows_Command(text):
    if not globals().get("COMMAND_CLASSIFIER_ENABLED", False):
        return True
    score = Command_Classifier_Predict(text)
    if score is None:
        return True
    return score >= float(globals().get("COMMAND_CLASSIFIER_THRESHOLD", 0.65))


def Read_Results_Command_Is_Specific(text):
    normalized = str(text or "").lower()
    try:
        normalized = unidecode(normalized)
    except Exception as e:
        Log_Error("Read_Results_Command_Is_Specific", e)
    normalized = re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return any(
        pattern in normalized
        for pattern in [
            "resultat",
            "resultats",
            "ce que tu as trouve",
            "ce que vous avez trouve",
            "tout ca",
            "tout cela",
        ]
    )


def Normalize_Help_Command_Text(text):
    normalized = str(text or "").lower()
    try:
        normalized = unidecode(normalized)
    except Exception as e:
        Log_Error("Normalize_Help_Command_Text", e)
    normalized = normalized.replace("'", " ")
    normalized = re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def Detect_Trinitty_Help_Request(text):
    normalized = Normalize_Help_Command_Text(text)
    if not normalized:
        return False

    exact_requests = {
        "aide",
        "help",
        "commandes",
        "fonctions",
        "fonctionnalites",
        "possibilites",
        "aide trinitty",
        "aide trinity",
    }
    if normalized in exact_requests:
        return True

    capability_patterns = [
        r"\bque peux tu faire\b",
        r"\bque pouvez vous faire\b",
        r"\bqu est ce que tu sais faire\b",
        r"\bqu est ce que vous savez faire\b",
        r"\ba quoi sers tu\b",
        r"\ba quoi servez vous\b",
    ]
    if any(re.search(pattern, normalized) for pattern in capability_patterns):
        return True

    help_words = r"\b(aide|help|commande|commandes|fonction|fonctions|fonctionnalite|fonctionnalites|possibilite|possibilites)\b"
    action_words = (
        r"\b(affiche|affiches|affichez|montre|montres|montrez|liste|listes|listez|donne|donnes|donnez|"
        r"explique|expliques|expliquez|presente|presentes|presentez|indique|indiques|indiquez|"
        r"quelles|quels|quoi|comment)\b"
    )
    return bool(re.search(help_words, normalized) and re.search(action_words, normalized))


def Results_Hub_Direct_Command(text, allowed_functions=None):
    normalized = Results_Hub_Normalize_Text(text)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized).strip()
    if not normalized:
        return None

    allowed = set(allowed_functions or [])
    tokens = set(normalized.split())
    has_result_scope = bool(
        tokens.intersection(
            {
                "resultat",
                "resultats",
                "reponse",
                "reponses",
                "numero",
                "numeros",
                "num",
                "n",
            }
        )
    )
    has_selection = Results_Hub_Selection_Range(normalized, 1000) is not None
    if not has_result_scope and not has_selection:
        return None

    open_words = {
        "ouvre",
        "ouvrez",
        "ouvrir",
        "lien",
        "liens",
        "url",
        "page",
        "site",
        "internet",
    }
    read_words = {
        "lis",
        "lire",
        "lisez",
        "dis",
        "dites",
        "parle",
        "parlez",
        "raconte",
        "racontez",
        "explique",
        "expliquez",
    }

    if tokens.intersection(open_words) and (not allowed or "F_read_link" in allowed):
        return "F_read_link"
    if tokens.intersection(read_words) and (not allowed or "F_read_results" in allowed):
        return "F_read_results"
    return None


def Commandes(txt=None,allowed_functions=None,from_function=None):

    direct_url = Extract_First_Url(txt)
    if direct_url and (allowed_functions is None or "F_read_link" in allowed_functions):
        if from_function == "Results_Hub" or CMD_DBG:
            return "F_read_link"
        ReadLink(txtinput=txt, urlinput=direct_url)
        return True

    decoded = unidecode(
             txt.lower()
            .replace(",", " ")
            .replace("!", " ")
            .replace("?", " ")
            .replace("  ", " ")
            .replace(".", " ")
            )

    if from_function == "Results_Hub":
        direct_results_command = Results_Hub_Direct_Command(decoded, allowed_functions=allowed_functions)
        if direct_results_command:
            PRINT("\n-Trinitty:Commandes():Results_Hub direct command:%s" % direct_results_command)
            return direct_results_command

    if (
        from_function != "Results_Hub"
        and (allowed_functions is None or "F_trinity_help" in allowed_functions)
        and Detect_Trinitty_Help_Request(decoded)
    ):
        PRINT("\n-Trinitty:Commandes():direct help command.")
        if CMD_DBG or from_function:
            return "F_trinity_help"
        return Trinitty_Help()

    #    filter = ["s'il te plait","si te plait","sil te plait","merci"," stp "]
    #    to_remove = [" fais ","estce"," peux faire "," recherche ","faismoi"," fais ","peux ","fais recherche "," parle ","s'il te plait"," stp "," svp"," sur ","sil plait"]
    #    decoded = SeeknDestroy(filter, decoded)
    if allowed_functions is None and not Command_Classifier_Allows_Command(decoded):
        PRINT("\n-Trinitty:Commandes():rejected by command classifier.")
        return False

    if allowed_functions:
        ambiguity = Check_Ambiguity(decoded,allowed_functions)
    else:
        ambiguity = Check_Ambiguity(decoded)
    goto = None

    if ambiguity is None:
        PRINT("\n-Trinitty:Commandes():Check_Ambiguity():Main cmd trigger:None.")
    elif ambiguity is False:
        PRINT("\n-Trinitty:Commandes():Check_Ambiguity():len(ambiguity) == 0")
    elif len(ambiguity) > 1:
        PRINT("\n-Trinitty:Commandes():Ambiguités détectée.")
        goto = Disambiguify(ambiguity, decoded)
    elif len(ambiguity) == 1:
        PRINT("\n-Trinitty:Commandes():Commande détecté.")
        goto = next(k for k in ambiguity)

    if CMD_DBG:
       if ambiguity:
           PRINT("\n-Trinitty:Commandes():len(ambiguity):%s"%len(ambiguity))
       else:
           PRINT("\n-Trinitty:Commandes():ambiguity:%s"%ambiguity)

       PRINT("%s"%ambiguity)
       return(goto)


    if from_function:
       PRINT("from_function:%s" % from_function)
       if goto:
          PRINT("goto:%s" % goto)
       PRINT("txt:%s" % txt)
       PRINT("allowed_functions:%s" % allowed_functions)

    if goto:

        PRINT("\n-Trinitty:Commandes():Va dans la fonction :%s" % goto)

        #Commandes(txt, allowed_functions, "Results_Hub")

        if goto == "F_read_results" and from_function != "Results_Hub":
            if not Read_Results_Command_Is_Specific(decoded):
                PRINT("\n-Trinitty:Commandes():F_read_results ignored; trigger is too broad.")
                return False

        if from_function == "Results_Hub":
            return goto


        if goto == "F_add_trigger":
            Add_Trigger()
            return True

        if goto == "F_wait":
            Wait()
            return True

        if goto == "F_trinity_name":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/saved_answer/trinity.wav")
            return True

        if goto == "F_trinity_mean":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/saved_answer/matrix.wav")
            return True
        if goto == "F_trinity_dev":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/saved_answer/botmaster.wav")
            return True

        if goto == "F_rnd":
            rnd = str(Non_Crypto_Randint(1, 2))
            ouinon = SCRIPT_PATH + "/local_sounds/ouinon/" + rnd + ".wav"
            Play_Audio_File(ouinon)
            return True
        if goto == "F_repeat":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/repeat/isaid.wav")
            Play_Audio_File(Runtime_Tmp_Path("current_answer.wav"))
            return True

        if goto == "F_prompt":
            Prompt()
            return True
        if goto == "F_trinity_help":
            return Trinitty_Help()

        if goto == "F_trinity_script":
            Trinitty_Script()
            return True

        if goto == "F_read_results":
            Read_Results(globals().get("LAST_DIALOG", []))
            return True

        if goto == "F_quit":
            Quit()
            return True

        if goto == "F_play_audio":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/question/sound_file.wav")
            sound_input = input("Entrez le chemin du fichier à lire:")
            if Audio_File_Is_Playable(sound_input):
                Play_Response(sound_input, stay_awake=False, save_history=False)
                return True
            return True

        if goto == "F_show_history":

            Show_History()
            return True

        if goto == "F_search_history":

            Search_History(decoded)

            return True

        if goto == "F_delete_last_history":
            return Delete_Last_History_Entry()

        if goto == "F_read_link":
            ReadLink(txtinput=txt)

            return True
        if goto == "F_search_web":

            if "wikipedia" in decoded:
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/server/wikipedia.wav")
                Wikipedia(decoded)
                return True
            Google(decoded)
            return True

        return False
    print("return false")
    return False


SEARCH_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) "
        "Gecko/20100101 Firefox/126.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}


def Search_Result_Url_Is_Usable(url):
    url = str(url or "").strip()
    if not url:
        return False
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    query = parsed.query.lower()
    if host.endswith("duckduckgo.com"):
        return False
    if host.endswith("google.com") and path in ("/search", "/url", "/preferences"):
        return False
    if path.endswith("/aclick") or "ad_domain=" in query or "ad_type=" in query:
        return False
    return True


def Decode_Search_Result_Url(url):
    raw_url = str(url or "").strip()
    if not raw_url:
        return ""
    if raw_url.startswith("//"):
        raw_url = "https:%s" % raw_url

    parsed = urlparse(raw_url)
    if parsed.netloc.endswith("duckduckgo.com"):
        if parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            target = unquote(target).strip()
            return target if Search_Result_Url_Is_Usable(target) else ""
        return ""
    if parsed.netloc.endswith("google.com") and parsed.path == "/url":
        target = parse_qs(parsed.query).get("q", [""])[0]
        target = unquote(target).strip()
        return target if Search_Result_Url_Is_Usable(target) else ""
    if parsed.netloc.endswith("bing.com") and parsed.path == "/ck/a":
        target = parse_qs(parsed.query).get("u", [""])[0]
        if target.startswith("a1"):
            target = target[2:]
        try:
            target += "=" * (-len(target) % 4)
            target = base64.urlsafe_b64decode(target).decode("utf-8", errors="ignore").strip()
        except Exception as e:
            Log_Error("Decode_Search_Result_Url:bing", e)
            target = ""
        return target if Search_Result_Url_Is_Usable(target) else ""
    return raw_url if Search_Result_Url_Is_Usable(raw_url) else ""


def Search_Result_Matches_Site(url, site=None):
    if not site:
        return True
    url = str(url or "").lower()
    site = str(site or "").lower()
    if site == "wikipedia":
        return "wikipedia.org" in url
    return site in url


def Googlesearch_Module_Search(to_search, rnbr=10, site=None):
    results = []
    google_query = googlesearch.search(to_search, num_results=rnbr, lang="fr", advanced=True)
    for result in google_query:
        if isinstance(result, str):
            title = result
            description = ""
            url = result
        else:
            title = getattr(result, "title", "")
            description = getattr(result, "description", "")
            url = getattr(result, "url", "")
        url = Decode_Search_Result_Url(url)
        if not title or not url or not Search_Result_Matches_Site(url, site):
            continue
        PRINT("\n-Trinitty:google_result:", title)
        results.append(Google_Result_Item(title, description, url))
        if len(results) >= rnbr:
            break
    return results


def Fallback_Search_Sources(to_search):
    return [
        {
            "name": "duckduckgo-html-get",
            "method": "get",
            "url": "https://html.duckduckgo.com/html/",
            "params": {"q": to_search},
            "engine": "duckduckgo",
        },
        {
            "name": "duckduckgo-html-post",
            "method": "post",
            "url": "https://html.duckduckgo.com/html/",
            "data": {"q": to_search},
            "engine": "duckduckgo",
        },
        {
            "name": "brave",
            "method": "get",
            "url": "https://search.brave.com/search",
            "params": {"q": to_search, "source": "web"},
            "engine": "brave",
        },
        {
            "name": "bing",
            "method": "get",
            "url": "https://www.bing.com/search",
            "params": {"q": to_search, "setlang": "fr-FR"},
            "engine": "bing",
        },
    ]


def Fetch_Fallback_Search_Source(source):
    kwargs = {"headers": SEARCH_HTTP_HEADERS, "timeout": 10}
    if source["method"] == "post":
        return requests.post(source["url"], data=source.get("data", {}), **kwargs)
    return requests.get(source["url"], params=source.get("params", {}), **kwargs)


def Extract_Fallback_Search_Results(response_text, engine, rnbr=10, site=None):
    soup = BeautifulSoup(response_text, "html.parser")
    results = []
    seen_urls = set()

    if engine == "bing":
        nodes = soup.select("li.b_algo")
        for node in nodes:
            link = node.select_one("h2 a[href]")
            if not link:
                continue
            title = link.get_text(" ", strip=True)
            url = Decode_Search_Result_Url(link.get("href"))
            if not title or not url or url in seen_urls or not Search_Result_Matches_Site(url, site):
                continue
            snippet_node = node.select_one(".b_caption p")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            seen_urls.add(url)
            results.append(Google_Result_Item(title, snippet, url))
            if len(results) >= rnbr:
                break
        return results

    if engine == "brave":
        nodes = soup.select("div.result-content")
        for node in nodes:
            link = node.select_one("a.l1[href], a[href]")
            if not link:
                continue
            title_node = node.select_one(".title")
            title = title_node.get_text(" ", strip=True) if title_node else link.get_text(" ", strip=True)
            url = Decode_Search_Result_Url(link.get("href"))
            if not title or not url or url in seen_urls or not Search_Result_Matches_Site(url, site):
                continue
            snippet_node = node.select_one(".generic-snippet .content")
            snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
            seen_urls.add(url)
            results.append(Google_Result_Item(title, snippet, url))
            if len(results) >= rnbr:
                break
        return results

    for link in soup.select("a.result__a, a.result-link"):
        title = link.get_text(" ", strip=True)
        url = Decode_Search_Result_Url(link.get("href"))
        if not title or not url or url in seen_urls or not Search_Result_Matches_Site(url, site):
            continue

        container = link.find_parent(class_="result")
        snippet = ""
        if container:
            snippet_node = container.select_one(".result__snippet")
            if snippet_node:
                snippet = snippet_node.get_text(" ", strip=True)

        seen_urls.add(url)
        results.append(Google_Result_Item(title, snippet, url))
        if len(results) >= rnbr:
            break
    return results


def Fallback_Web_Search(to_search, rnbr=10, site=None):
    PRINT("\n-Trinitty:Using fallback web search.")
    for source in Fallback_Search_Sources(to_search):
        try:
            response = Fetch_Fallback_Search_Source(source)
            if response.status_code != 200:
                PRINT(
                    "\n-Trinitty:Fallback web search %s status:%s"
                    % (source["name"], response.status_code)
                )
                continue

            results = Extract_Fallback_Search_Results(
                response.text,
                source["engine"],
                rnbr=rnbr,
                site=site,
            )
            if results:
                for result in results:
                    PRINT("\n-Trinitty:fallback_web_result:", result["google_title"])
                return results
            PRINT("\n-Trinitty:Fallback web search %s no parsed result" % source["name"])
        except Exception as e:
            Log_Error("Fallback_Web_Search:%s" % source["name"], e)
            PRINT("\n-Trinitty:Fallback web search %s Error:%s" % (source["name"], str(e)))
    return []


def Search_Result_Title(results):
    if not results:
        return ""
    return str(results[0].get("google_title") or "").strip()


def GetTitleLink(txt, site=None):
    PRINT("\n-Trinitty:Dans la fonction GetTitleLink()")
    PRINT("\n-Trinitty:txt:", txt)
    PRINT("\n-Trinitty:txt:", site)

    SearchFallback = False
    title_search = ""

    if len(GOOGLE_KEY) != 0 and len(GOOGLE_ENGINE) != 0:

        PRINT("\n-Trinitty:Using Custom Search Google Api.")

        try:
            google_query = "https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&q=%s&start=1" % (
                GOOGLE_KEY,
                GOOGLE_ENGINE,
                quote_plus(txt),
            )

            response = requests.get(google_query, timeout=10)

            if response.status_code != 200:
                SearchFallback = True
                PRINT("\n-Trinitty:Google Custom Search status:%s" % response.status_code)
            else:
                data = response.json()

                search_items = data.get("items") or []

                for result in search_items:
                    title_search = str(result.get("title") or "").strip()
                    url = Decode_Search_Result_Url(result.get("link"))
                    if len(title_search) == 0 or not Search_Result_Matches_Site(url, site):
                        continue
                    break

        except Exception as e:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_Google.wav")
            Log_Error("GetTitleLink:custom_search", e)
            PRINT("\n-Trinitty:Custom search Error:", str(e))
            SearchFallback = True

        if len(title_search) == 0:
            PRINT("\n-Trinitty:-Google() no result from google")
            SearchFallback = True
        else:
            return title_search

    if (len(GOOGLE_KEY) == 0 and len(GOOGLE_ENGINE) == 0) or SearchFallback:

        try:
            title_search = Search_Result_Title(Googlesearch_Module_Search(txt, rnbr=10, site=site))
            if len(title_search) == 0:
                title_search = Search_Result_Title(Fallback_Web_Search(txt, rnbr=10, site=site))

            if len(title_search) == 0:
                PRINT("\n-Trinitty:GetTitleLink no result from google")
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_result_google.wav")
                return None

            return title_search

        except Exception as e:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_google.wav")
            PRINT("\n-Trinitty:Error:", str(e))
            return None

    return None


def Normalize_Search_Query_Text(txt):
    query = str(txt or "").lower()
    try:
        query = unidecode(query)
    except Exception as e:
        Log_Error("Normalize_Search_Query_Text", e)
    if any(ord(char) > 127 for char in query):
        query = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode("ascii")
    return query


def Clean_Wikipedia_Search_Query(txt):
    original = str(txt or "").strip()
    query = Normalize_Search_Query_Text(original)
    query = query.replace("’", "'")

    polite_patterns = [
        r"\bs\s*'?\s*il\s+(te|vous)\s+pla[iî]t\b",
        r"\b(stp|svp|merci)\b",
    ]
    command_patterns = [
        r"\best[\s-]*ce\s+que\b",
        r"\btu\s+peux\b",
        r"\bpouvez\s+vous\b",
        r"\bpeux\s+tu\b",
        r"\bfais\s+(moi\s+)?une\s+recherche\b",
        r"\bfaire\s+(moi\s+)?une\s+recherche\b",
        r"\bune\s+recherche\b",
        r"\bfaire\s+des\s+recherches\b",
        r"\brecherche(?:r|s)?\b",
        r"\bcherche(?:r|s)?\b",
        r"\btrouve(?:r|s)?\b",
        r"\bregarde(?:r|s)?\b",
        r"\bwikipedia\b",
        r"\bwikipédia\b",
    ]
    for pattern in polite_patterns + command_patterns:
        query = re.sub(pattern, " ", query)

    query = re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", query)
    query = re.sub(
        r"\b(sur|dans|avec|a|au|aux|de|des|du|d|la|le|les|l|un|une|s)\b",
        " ",
        query,
    )
    query = re.sub(r"\s+", " ", query).strip()
    return query or original


def Clean_Web_Search_Query(txt):
    original = str(txt or "").strip()
    query = Normalize_Search_Query_Text(original)
    query = query.replace("’", "'")

    patterns = [
        r"\bs\s*'?\s*il\s+(te|vous)\s+pla[iî]t\b",
        r"\b(stp|svp|merci)\b",
        r"\best[\s-]*ce\s+que\b",
        r"\btu\s+peux\b",
        r"\bpouvez\s+vous\b",
        r"\bpeux\s+tu\b",
        r"\bfais\s+(moi\s+)?une\s+recherche\b",
        r"\bfaire\s+(moi\s+)?une\s+recherche\b",
        r"\bune\s+recherche\b",
        r"\bfaire\s+des\s+recherches\b",
        r"\brecherche(?:r|s)?\b",
        r"\bcherche(?:r|s)?\b",
        r"\btrouve(?:r|s)?\b",
        r"\bregarde(?:r|s)?\b",
        r"\b(google|internet|web|wikipedia|wikipédia)\b",
    ]
    for pattern in patterns:
        query = re.sub(pattern, " ", query)

    query = re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", query)
    query = re.sub(
        r"\b(sur|dans|avec|a|au|aux|de|des|du|d|la|le|les|l|un|une|s)\b",
        " ",
        query,
    )
    query = re.sub(r"\s+", " ", query).strip()
    return query or original


def Clean_History_Search_Query(txt):
    original = str(txt or "").strip()
    query = Normalize_Search_Query_Text(original)
    query = query.replace("’", "'")

    patterns = [
        r"\bs\s*'?\s*il\s+(te|vous)\s+pla[iî]t\b",
        r"\b(stp|svp|merci)\b",
        r"\best[\s-]*ce\s+que\b",
        r"\btu\s+peux\b",
        r"\bpouvez\s+vous\b",
        r"\bpeux\s+tu\b",
        r"\brappelle(?:s)?(?:\s*toi)?\b",
        r"\bsouviens(?:\s*toi)?\b",
        r"\bsais(?:\s*tu)?\b",
        r"\bce\s+qu\s+on\s+(a|avait)?\s*(dit|vu|cherche|trouve|explique|parle)\b",
        r"\bqu\s+on\s+(a|avait)?\s*(dit|vu|cherche|trouve|explique|parle)\b",
        r"\bce\s+dont\s+on\s+(a|avait)?\s*parle\b",
        r"\bdont\s+on\s+(a|avait)?\s*parle\b",
        r"\bon\s+(a|avait)?\s*(dit|vu|cherche|trouve|explique|parle)\b",
        r"\bcherche(?:r|z|-moi|s)?\b",
        r"\btrouve(?:r|z|-moi|s)?\b",
        r"\bregarde(?:r|z|-moi|s)?\b",
        r"\bverifie(?:r|z|-moi|s)?\b",
        r"\bparle(?:r|z|s)?\b",
        r"\bdit\b",
        r"\brecherche(?:r|s)?\b",
        r"\bdans\s+l\s+historique\b",
        r"\bl\s+historique\b",
        r"\bhistorique\b",
        r"\b(deja|avec toi|avec vous|ensemble)\b",
    ]
    for pattern in patterns:
        query = re.sub(pattern, " ", query)

    query = re.sub(r"[^0-9a-zA-ZÀ-ÿ]+", " ", query)
    query = re.sub(
        r"\b(sur|dans|avec|a|au|aux|de|des|du|d|la|le|les|l|un|une|s|ce|cet|cette|ces|que|qu|qui|quoi|on|nous|vous|tu|te|t|moi|mon|ma|mes|ton|ta|tes|votre|vos|notre|nos|en|y)\b",
        " ",
        query,
    )
    query = re.sub(r"\s+", " ", query).strip()
    return query or original


def Normalize_History_Search_Text(txt):
    return Normalize_Search_Query_Text(txt)


def Google_Result_Item(title=None, description=None, url=None):
    title = str(title or "Sans titre").strip()
    description = str(description or "no description").strip()
    url = str(url or "").strip()
    return {"google_title": title, "google_description": description, "google_url": url}


def Google_Result_Description(result):
    description = result.get("snippet") or result.get("htmlSnippet") or ""
    if description:
        return description
    try:
        return result.get("pagemap", {}).get("metatags", [{}])[0].get("og:description", "")
    except Exception:
        return ""


def Google_Custom_Search_Query(to_search, start=1, site_search="", sort_by_date=False):
    sort_param = "&sort=date" if sort_by_date else ""
    return "https://www.googleapis.com/customsearch/v1?key=%s&cx=%s&q=%s%s%s&start=%s" % (
        GOOGLE_KEY,
        GOOGLE_ENGINE,
        quote_plus(to_search),
        site_search,
        sort_param,
        start,
    )


def ReadLink(txtinput=None, titleinput=None, urlinput=None):

    PRINT("\n-Trinitty: txtinput: %s", txtinput)

    if not urlinput:
        urlinput = Extract_First_Url(txtinput)

    if len(urlinput) > 0:
        if "wikipedia" in urlinput:
            if not titleinput:
                wiki_title = GetTitleLink(txtinput, "wikipedia")
            else:
                wiki_title = titleinput

            if wiki_title:
                PRINT("\n-Trinitty:wiki_title:", wiki_title)
                return Wikipedia(txtinput, Title=wiki_title)

            PRINT("\n-Trinitty:no title using txtinput:", txtinput)
            return Wikipedia(txtinput)

        try:

            response = requests.get(urlinput, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            text_data = ""
            for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
                text_data += tag.get_text()
            if len(text_data) > 0:
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/reading_link.wav")
                last_sentence.put(txtinput + " %s" % urlinput)
                Text_To_Speech(text_data, stayawake=True)
                return ()
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_read_link_no_txt.wav")
            return ()
        except Exception as e:
            PRINT("\n-Trinitty:Error:", str(e))
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_read_link_request.wav")

    else:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/question/read_link_url.wav")

        url_input = input("Entrez un lien:")

        urlinput = Extract_First_Url(url_input)

    if len(urlinput) > 0:
        #           if "wikipedia" in urlinput: ##TO REWRITE

        #               if not titleinput: ####ToCHECKurlinputVStxtinput
        #                   wiki_title = GetTitleLink(txtinput,"wikipedia")
        #               else:
        #                   wiki_title = titleinput
        #
        #               if wiki_title:
        #                   PRINT("\n-Trinitty:wiki_title:",wiki_title)
        #                   return(Wikipedia(txtinput,title=wiki_title))

        #               else:
        #                   PRINT("\n-Trinitty:Pas de titre title utilisation de txtinput:",txtintput)
        #                   return(Wikipedia(txtinput))

        #           else:
        try:

            response = requests.get(urlinput, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            text_data = ""
            for tag in soup.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6"]):
                text_data += tag.get_text()
            if len(text_data) > 0:
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/reading_link.wav")
                last_sentence.put(txtinput + " %s" % urlinput)
                Text_To_Speech(text_data, stayawake=True)
                return ()
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_read_link_no_txt.wav")
            return ()
        except Exception as e:
            PRINT("\n-Trinitty:Error:", str(e))
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_read_link_request.wav")
            return ()
    else:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_url_not_valid.wav")
        return ()
    return None


def Google(to_search, rnbr=50,wiki_failed=False):  # ,tstmode = True):

    SearchFallback = False
    google_result = []

    to_search = Clean_Web_Search_Query(Isolate_Search(to_search,"F_search_web"))

    PRINT("\n-Trinitty:Google():to_search:%s"%to_search)
    PRINT("\n-Trinitty:Google():wiki_failed:%s"%wiki_failed)

    if len(GOOGLE_KEY) != 0 and len(GOOGLE_ENGINE) != 0:

        PRINT("\n-Trinitty:Using Custom Search Google Api.")

        maxpage = max(1, int((rnbr + 9) / 10))
        for page in range(maxpage):
            start = page * 10 + 1
            try:
                if wiki_failed:
                    siteSearch = "&siteSearch=fr.wikipedia.org&siteSearchFilter=i"
                else:
                    siteSearch = ""

                google_query = Google_Custom_Search_Query(
                    to_search,
                    start=start,
                    site_search=siteSearch,
                    sort_by_date=globals().get("GOOGLE_SORT_BY_DATE", False),
                )

                response = requests.get(google_query, timeout=10)

                if response.status_code != 200:
                    SearchFallback = True
                    continue
                SearchFallback = False
                data = response.json()

                search_items = data.get("items") or []

                for result in search_items:

                    title = result.get("title")
                    description = Google_Result_Description(result) or "no description"
                    url = result.get("link")

                    google_result.append(Google_Result_Item(title, description, url))
                    if len(google_result) >= rnbr:
                        break

            except Exception as e:
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_Google.wav")
                Log_Error("Google:custom_search", e)
                PRINT("\n-Trinitty:Custom search Error:", str(e))
                SearchFallback = True

        if len(google_result) == 0:
            PRINT("\n-Trinitty:-Google() no result from google")
            SearchFallback = True

    if (len(GOOGLE_KEY) == 0 and len(GOOGLE_ENGINE) == 0) or SearchFallback:

        PRINT("\n-Trinitty:Using module googlesearch.")
        try:
            site = "wikipedia" if wiki_failed else None
            google_result.extend(Googlesearch_Module_Search(to_search, rnbr=rnbr, site=site))

            if len(google_result) == 0:
                google_result.extend(Fallback_Web_Search(to_search, rnbr=rnbr, site=site))

        except Exception as e:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_Google.wav")
            Log_Error("Google:googlesearch", e)
            PRINT("\n-Trinitty:Googlesearch Error:", str(e))
            google_result.extend(Fallback_Web_Search(to_search, rnbr=rnbr, site="wikipedia" if wiki_failed else None))

        if len(google_result) == 0:
            PRINT("\n-Trinitty:-Google() no result from google")
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_result_google.wav")
            return ()

    top20 = google_result[:20]

    return(Results_Hub(google_result,top20,from_function="Google"))


def Wikipedia(to_search, Title=None, FULL=None):

    choice = "summary"
    to_search = to_search.strip()


    original_search = to_search

    to_search = Isolate_Search(to_search,"F_search_web")


    PRINT("\n-Trinitty:Dans la fonction Wikipedia.")
    PRINT("\n-Trinitty:to_search:", to_search)
    PRINT("\n-Trinitty:title:", Title)
    PRINT("\n-Trinitty:FULL:", FULL)


    try:
        wikipedia.set_lang("fr")

        wiki_candidates = []
        if Title:
            wiki_candidates.append(Title)
        else:
            clean_search = Clean_Wikipedia_Search_Query(to_search)
            clean_original = Clean_Wikipedia_Search_Query(original_search)

            if "wikipedia" not in clean_search.lower():
                to_search_title = "wikipedia " + clean_search
            else:
                to_search_title = clean_search

            wiki_search = GetTitleLink(to_search_title, site="wikipedia")
            if wiki_search:
                wiki_candidates.append(wiki_search)

            for candidate in [clean_search, clean_original, to_search, original_search]:
                clean_candidate = Clean_Wikipedia_Search_Query(candidate)
                if clean_candidate and clean_candidate not in wiki_candidates:
                    wiki_candidates.append(clean_candidate)

        query_list = []
        for wiki_search in wiki_candidates:
            PRINT("\n-Trinitty:Wikipedia search candidate:", wiki_search)
            try:
                query_list = wikipedia.search(wiki_search)
            except Exception as e:
                PRINT("\n-Trinitty:Wikipedia search candidate error:", str(e))
                query_list = []
            if query_list:
                break
        #        query_list = [i.replace(" ","_") for i in query_list]

        if len(query_list) > 0:
            for r in query_list:
                PRINT("\n-Trinitty:wiki reponse:", r)
        else:
            PRINT("\n-Trinitty:no result from wikipedia")
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_result_wiki.wav")
            return(Google(original_search,wiki_failed=True))

        if len(query_list) > 0:
            PRINT("\n-Trinitty:Going to search : ", query_list[0])
            try:
                if not FULL:

                    Play_Audio_File(SCRIPT_PATH + "/local_sounds/question/wikipedia.wav")

                    txt = ""
                    opinion = None

                    if Start_Thread_Record() is not False and Wait_for("audio"):
                        audio = Queue_Get_Optional(audio_datas, timeout=0.2, default=None)
                        if audio is not None:
                            (
                                transcripts,
                                transcripts_confidence,
                                words,
                                words_confidence,
                                Err_msg,
                            ) = Speech_To_Text(audio)
                            txt, _fconf = Check_Transcript(
                                transcripts,
                                transcripts_confidence,
                                words,
                                words_confidence,
                                Err_msg,
                            )

                    if len(txt) > 0:
                        opinion = Detect_Question_Opinion(txt)
                        if opinion is None:
                            Question(txt)
                            if Wait_for("question"):
                                opinion = Queue_Get_Optional(score_sentiment, timeout=0.2, default=None)
                    else:
                        opinion = False

                    if opinion is None:
                        choice = Non_Crypto_Choice(["summary", "full"])
                        if choice == "summary":
                            Play_Audio_File(SCRIPT_PATH + "/local_sounds/ouinon/wiki_summary.wav")
                        if choice == "full":
                            Play_Audio_File(SCRIPT_PATH + "/local_sounds/ouinon/wiki_full.wav")
                    elif opinion is False:
                        choice = "summary"
                        Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/wiki_summary.wav")
                    elif opinion is True:
                        choice = "full"
                        Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/wiki_full.wav")

                elif FULL:
                    choice = "full"
                    Play_Audio_File(SCRIPT_PATH + "/local_sounds/ouinon/wiki_full.wav")

                if choice == "summary":

                    try:
                        summary = wikipedia.summary(query_list[0])
                    except Exception:
                        try:
                            summary = wikipedia.summary(title=query_list[0], auto_suggest=True)
                        except Exception as e:
                            PRINT("\n-Trinitty:Error:", str(e))
                            try:
                                summary = wikipedia.summary(
                                    title=query_list[0].replace(" ", "").replace("_", ""),
                                    auto_suggest=True,
                                )
                            except Exception as e:
                                PRINT("\n-Trinitty:Error:", str(e))
                                Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_wiki.wav")
                                return(Google(original_search,wiki_failed=True))

#                    last_sentence.put(to_search)
                    last_sentence.put(original_search)
                    Text_To_Speech(summary, stayawake=True)
                    return ()


                try:
                    page = wikipedia.page(query_list[0])
                    content = page.content
                except Exception:
                    try:
                        page = wikipedia.page(title=query_list[0], auto_suggest=True)
                        content = page.content
                    except Exception as e:
                        PRINT("\n-Trinitty:Error:", str(e))
                        try:
                            page = wikipedia.page(
                                title=query_list[0].replace(" ", "").replace("_", ""),
                                auto_suggest=True,
                            )
                            content = page.content
                        except Exception as e:
                            PRINT("\n-Trinitty:Error:", str(e))
                            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_wiki.wav")
                            return(Google(original_search,wiki_failed=True))

                if "== Notes" in content:
                    content = content.split("== Notes")[0]

                if "=== Notes" in content:
                    content = content.split("=== Notes")[0]

                if "===" in content:
                    content = content.replace("===", " ")

                if "==" in content:
                    content = content.replace("== ", " ")

                if len(content) > 0:
                    #last_sentence.put(to_search)
                    last_sentence.put(original_search)
                    Text_To_Speech(content, stayawake=True)
                    return ()

                PRINT("\n-Trinitty:no result from content wikipedia")
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_result_wiki.wav")
                return ()
            except Exception as e:
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_wiki.wav")
                PRINT("Error:", str(e))
                return(Google(original_search,wiki_failed=True))

    except Exception as e:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_func_wiki.wav")
        PRINT("\n-Trinitty:Error:", str(e))
        return(Google(original_search,wiki_failed=True))


def Prompt(allowed_functions=None,from_function=None):
    PRINT("\n-Trinitty:Dans la fonction Prompt")
    if from_function == "Results_Hub":
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/question/search_history_cmds.wav")
    Play_Audio_File(SCRIPT_PATH + "/local_sounds/prompt/2.wav")
    user_input = input("\n-Trinitty:Comment puis-je vous aider ?:").strip()
    if len(str(user_input)) > 2:

        cmd = Commandes(user_input,allowed_functions=allowed_functions,from_function=from_function)
        if not cmd and not from_function:
            PRINT("\n-Trinitty:Prompt():pas de cmd")
            return To_Gpt(str(user_input))
        if not cmd and from_function:
            PRINT("\n-Trinitty:Prompt():pas de cmd mais from_function:%s"%from_function)
            if from_function == "Results_Hub":
                return ("no cmd", user_input)
            return("no cmd")
        if cmd and from_function:
            PRINT("\n-Trinitty:Prompt():cmd:%s  from_function:%s"%(cmd,from_function))
            if from_function == "Results_Hub":
                return (cmd, user_input)
            return(cmd)
        Go_Back_To_Sleep()
        return None

    PRINT("\n-Trinitty:Prompt():pas d'input")
    No_Input.put(True)
    rnd = str(Non_Crypto_Randint(1, 11))
    Play_Audio_File(SCRIPT_PATH + "/local_sounds/noinput/" + rnd + ".wav")
    if from_function == "Results_Hub":
        return ("no cmd", user_input)
    return Go_Back_To_Sleep()


def Simulate_Conversation(user_inputs, responder=None, execute_commands=False):
    if isinstance(user_inputs, str):
        user_inputs = [user_inputs]

    transcript = []
    for raw_user_text in user_inputs:
        user_text = str(raw_user_text)
        command_result = None
        if execute_commands:
            command_result = Commandes(user_text)

        if command_result:
            assistant_text = "Commande executee: %s" % command_result
        elif responder:
            assistant_text = str(responder(user_text, list(transcript)))
        else:
            assistant_text = "Simulation: %s" % user_text

        turn = {
            "user": user_text,
            "assistant": assistant_text,
            "command": command_result,
        }
        transcript.append(turn)

    return transcript


def Check_Transcript(transcripts, transcripts_confidence, words, words_confidence, Err_msg=""):

    avg_conf = 0
    bad_word = []
    bad_word_conf = []
    final_confidence = False

    PRINT("\n-Trinitty:checktranscript")

    if len(Err_msg) > 0:
        if Err_msg.startswith("Speech_To_Text:"):
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_stt.wav")
            PRINT("\n-Trinitty:Speech_To_Text failed; returning to wake loop instead of prompting.")
            Log_Error("Check_Transcript", Err_msg)
            return ("", False)

    if len(transcripts) > 0:
        PRINT("\n-Trinitty:transcripts:\n\n%s" % transcripts)
        PRINT("\n-Trinitty:transcripts_confidence:%s" % transcripts_confidence)

        if len(words) > 0 and len(words_confidence) > 0:
            for w, wc in zip(words, words_confidence, strict=False):
                PRINT("\n-Trinitty:confidence:%s word:%s" % (wc, w))
                if wc < STT_WORD_CONFIDENCE_MIN:
                    PRINT("\n-Trinitty:That word has bad confidence : %s %s" % (w, wc))
                    bad_word.append(w)
                    bad_word_conf.append(wc)
            avg_conf = sum(words_confidence) / len(words_confidence)
            PRINT("\n-Trinitty:Average words confidence :%s" % avg_conf)

        try:
            transcript_confidence = float(transcripts_confidence)
        except Exception:
            transcript_confidence = 0.0

        if transcript_confidence == 0.0:
            PRINT("\n-Trinitty:Transcript no confidence level\n.")
            if avg_conf >= STT_AVG_WORD_CONFIDENCE_MIN and not bad_word:
                final_confidence = True
                PRINT("\n-Trinitty:Words confidence seems ok\n.")
        elif transcript_confidence < STT_TRANSCRIPT_CONFIDENCE_MIN:
            PRINT("\n-Trinitty:Transcript has bad confidence\n.")
            final_confidence = False
        else:
            final_confidence = True
            PRINT("\n-Trinitty:Transcript seems ok\n.")

        if avg_conf > 0 and avg_conf < STT_AVG_WORD_CONFIDENCE_MIN:
            final_confidence = False
            PRINT("\n-Trinitty:Average words confidence is too low\n.")
        if bad_word:
            final_confidence = False
            PRINT("\n-Trinitty:Some words have bad confidence:%s" % bad_word)

        return (transcripts.replace("\\", ""), final_confidence)

    Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_respons.wav")
    #      Go_Back_To_Sleep()
    return ("", False)


def Normalize_Opinion_Text(txt):
    text = str(txt or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def Opinion_Text_Has_Phrase(normalized_text, phrase):
    normalized_phrase = Normalize_Opinion_Text(phrase)
    if not normalized_phrase:
        return False
    return re.search(r"(?:^|\s)%s(?:\s|$)" % re.escape(normalized_phrase), normalized_text) is not None


def Detect_Question_Opinion(txt):
    normalized = Normalize_Opinion_Text(txt)
    if not normalized:
        return None

    positive_phrases = [
        "oui",
        "ouais",
        "yes",
        "yep",
        "c est ca",
        "c est bien ca",
        "c est bon",
        "exactement",
        "tout a fait",
        "tu as bien compris",
        "vous avez bien compris",
        "valide",
        "confirme",
    ]
    negative_phrases = [
        "non",
        "no",
        "nope",
        "pas ca",
        "pas du tout",
        "c est pas ca",
        "ce n est pas ca",
        "ce n est pas bon",
        "incorrect",
        "faux",
        "recommence",
        "repete",
    ]

    positive = any(Opinion_Text_Has_Phrase(normalized, phrase) for phrase in positive_phrases)
    negative = any(Opinion_Text_Has_Phrase(normalized, phrase) for phrase in negative_phrases)
    if positive and not negative:
        return True
    if negative and not positive:
        return False
    return None


def Question(txt):

    PRINT("\n-Trinitty:Dans la fonction Question")
    lexical_opinion = Detect_Question_Opinion(txt)
    if lexical_opinion is not None:
        PRINT("\n-Trinitty:Question lexical opinion:%s" % lexical_opinion)
        score_sentiment.put(lexical_opinion)
        return ()

    score = 0
    try:

        client = language_v1.LanguageServiceClient()
        document = language_v1.Document(content=txt, language="fr", type_=language_v1.Document.Type.PLAIN_TEXT)
        sentiment = client.analyze_sentiment(request={"document": document}).document_sentiment

        PRINT(f"\n-Trinitty:Text: {txt}")
        PRINT(f"\n-Trinitty:Sentiment: {sentiment.score}, {sentiment.magnitude}")

        PRINT("\n\n\n-Trinitty:Sentimentfull:\n%s" % sentiment)

        score = sentiment.score
    except Exception as e:
        PRINT("\n-Trinitty:Error :%s" % str(e))

    if score > -0.15 and score < 0.15:
        PRINT("\n-Trinitty:Score is None")
        score_sentiment.put(None)
    elif score < -0.15:
        PRINT("\n-Trinitty:Score is False")
        score_sentiment.put(False)
    elif score > 0.15:
        PRINT("\n-Trinitty:Score is True")
        score_sentiment.put(True)

    return ()


def Repeat(txt):

    negation = [
        "laisse tomber",
        "c'est pas grave",
        "non c'est bon",
        "j'ai pas envie",
        "j'ai plus envie",
        "non merci",
    ]
    Loaded_Prompt_Requests = [
        "affiche moi le prompt",
        "préfère l'écrire",
        "préfère écrire",
        "vais l'écrire",
        "va l'écrire",
        "vais te l'écrire",
        "t'as rien compris",
        "tu n'as rien compris",
    ]

    opinion = Detect_Question_Opinion(txt)
    if opinion is None:
        Question(txt)
        if Wait_for("question"):
            opinion = Queue_Get_Optional(score_sentiment, timeout=0.2, default=None)
        else:
            opinion = None

    if opinion is False:
        no = any(element in txt.lower() for element in negation)
        if no:
            go_prompt = any(element in txt.lower() for element in Loaded_Prompt_Requests)
            if go_prompt:
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/1.wav")
                return Prompt()
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/1.wav")
            Go_Back_To_Sleep()
        else:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/1.wav")

            return Commandes(txt)
    else:

        Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/1.wav")
        return Commandes(txt)
    return None

def Bad_Stt(txt):
    PRINT("\n-Trinitty:Dans la fonction Bad_Stt")
    fname = Runtime_Tmp_Path("last_bad_stt.wav")
    os.makedirs(os.path.dirname(fname), exist_ok=True)
    try:

        client = tts.TextToSpeechClient()
        audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)

        text_input = tts.SynthesisInput(text=txt)
        voice_params = tts.VoiceSelectionParams(language_code="fr-FR", name="fr-FR-Neural2-A")

        response = client.synthesize_speech(input=text_input, voice=voice_params, audio_config=audio_config)
        audio_response = response.audio_content

        try:
            with open(fname, "wb") as out:
                out.write(audio_response)
        except Exception as e:
            PRINT("\n-Trinitty:Error:", str(e))
            Log_Error("Bad_Stt:write", e)
            return None

    except Exception as e:
        PRINT("\n-Trinitty:Error:%s" % str(e))
        try:
            Run_Pico2Wave(fname, txt)
        except Exception as e:
            PRINT("\n-Trinitty:Error:", str(e))
            Log_Error("Bad_Stt:pico2wave", e)
            return None

    if os.path.exists(fname):
        return Play_Audio_File(fname)
    return None


def Run_Pico2Wave(output_path, text):
    output_dir = os.path.dirname(str(output_path))
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    pico2wave_bin = which("pico2wave") or "pico2wave"
    subprocess.run(  # noqa: S603 - fixed executable and arguments; user text is passed as one argument.
        [pico2wave_bin, "-l", "fr-FR", "-w", output_path, str(text)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return output_path


def Correct_Misunderstood_Sentence(original_sentence=None, correction=None):
    original_sentence = str(original_sentence or "").strip()
    if correction is None:
        correction = input("\n-Trinitty:Correction de la phrase mal comprise:")
    correction = str(correction or "").strip()

    if correction:
        return To_Gpt(correction)
    if original_sentence:
        return To_Gpt(original_sentence)
    return Prompt()


def Bad_Confidence(txt):
    PRINT("\n-Trinitty:Dans la fonction Bad_Confidence")

    Orig_sentence = txt

    PRINT("\n-Trinitty:txt:", txt)
    PRINT("\n-Trinitty:Orig_sentence:", Orig_sentence)

    if globals().get("INTERPRETOR", False):
        return Correct_Misunderstood_Sentence(Orig_sentence)

    rnd = str(Non_Crypto_Randint(1, 10))
    bad_sound = SCRIPT_PATH + "/local_sounds/badconf/" + rnd + ".wav"
    Play_Audio_File(bad_sound)

    Bad_Stt(txt)

    question_sound = SCRIPT_PATH + "/local_sounds/question/1.wav"
    Play_Audio_File(question_sound)

    if Start_Thread_Record() is not False and Wait_for("audio"):
        audio = Queue_Get_Optional(audio_datas, timeout=0.2, default=None)
        if audio is None:
            score_sentiment.put(False)
        else:
            transcripts, transcripts_confidence, words, words_confidence, Err_msg = Speech_To_Text(audio)
            txt, _fconf = Check_Transcript(transcripts, transcripts_confidence, words, words_confidence, Err_msg)
            if len(txt) > 0:
                Question(txt)
                if not Wait_for("question"):
                    score_sentiment.put(False)
            else:
                score_sentiment.put(False)
    else:
        score_sentiment.put(False)
    opinion = Queue_Get_Optional(score_sentiment, timeout=0.2, default=False)

    if opinion is None:
        choice = Non_Crypto_Choice(["repeat", "send", "prompt"])
        if choice == "send":
            if len(Orig_sentence) > 0:
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/1.wav")
                return To_Gpt(Orig_sentence)
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/forgot/1.wav")
            choice = Non_Crypto_Choice(["repeat", "prompt"])
            if choice == "repeat":
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/repeat/1.wav")
                return Trinitty("Repeat")
            if choice == "prompt":
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/prompt/1.wav")
                return Prompt()

        if choice == "repeat":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/repeat/1.wav")
            return Trinitty("Repeat")
        if choice == "prompt":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/prompt/1.wav")
            return Prompt()
    elif opinion is False:
        choice = Non_Crypto_Choice(["repeat", "prompt"])
        if choice == "repeat":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/repeat/1.wav")
            return Trinitty("Repeat")
        if choice == "prompt":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/prompt/1.wav")
            return Prompt()
    elif opinion is True:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/1.wav")
        if len(Orig_sentence) > 0:
            return To_Gpt(Orig_sentence)
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/forgot/1.wav")
        choice = Non_Crypto_Choice(["repeat", "prompt"])
        if choice == "repeat":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/repeat/1.wav")
            return Trinitty("Repeat")
        if choice == "prompt":
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/prompt/1.wav")
            return Prompt()
    return None


def Split_Text(txt):

    PRINT("\n-Trinitty:Dans la fonction Split_text")
    result = []
    txt_len = len(txt)
    needle = 0
    while True:
        part = txt[needle : needle + 450]
        if len(part) >= 450:
            #            print("len part > 450:\n",part)
            last_ponct = part.rfind("\n")
            if last_ponct > 0:
                part = part[: last_ponct + 1]
            else:
                last_ponct = part.rfind(".")
                if last_ponct > 0:
                    part = part[: last_ponct + 1]
                else:
                    last_ponct = part.rfind(" ")
                    if last_ponct > 0:
                        part = part[: last_ponct + 1]
                    else:
                        part = txt[needle : needle + 250]
        else:
            #            print("len part < 450:\n",part)
            result.append(part.strip())
            break

        result.append(part.strip())

        if needle >= txt_len:
            break
        needle += len(part)

    return result


def Speech_To_Text(audio):
    PRINT("\n-Trinitty:Dans la fonction Speech_To_Text")

    Err_msg = ""
    try:
        stt_timeout = Config_Positive_Float(globals().get("GOOGLE_STT_TIMEOUT", 20.0), 20.0)
        PRINT("\n-Trinitty:Speech_To_Text timeout:%s" % stt_timeout)
        PRINT(
            "\n-Trinitty:GOOGLE_APPLICATION_CREDENTIALS:%s"
            % os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        )
        with Runtime_Timeout(stt_timeout, "Google Speech-to-Text"):
            PRINT("\n-Trinitty:Speech_To_Text init Google client")
            client = speech.SpeechClient()
            to_txt = speech.RecognitionAudio(content=audio)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                #        max_alternatives=3,
                enable_word_confidence=True,
                enable_automatic_punctuation=True,
                sample_rate_hertz=16000,
                audio_channel_count=1,
                language_code="fr-FR",
            )
            PRINT("\n-Trinitty:Speech_To_Text recognize")
            google_stt = client.recognize(request={"config": config, "audio": to_txt}, timeout=stt_timeout)
    except Exception as e:
        Err_msg = "Speech_To_Text:" + str(e)
        Log_Error("Speech_To_Text", e)
        PRINT("\n-Trinitty:Error:%s" % str(e))
    #    PRINT("google_stt %s:\n%s"%(type(google_stt),google_stt))

    transcripts = ""
    transcripts_confidence = 0
    words = []
    words_confidence = []

    if len(Err_msg) == 0:
        try:
            for result in google_stt.results:
                transcripts = result.alternatives[0].transcript
                transcripts_confidence = result.alternatives[0].confidence

                if result.alternatives[0].words:
                    for word in result.alternatives[0].words:
                        words.append(word.word)
                        words_confidence.append(word.confidence)
        except Exception as e:
            PRINT("\n-Trinitty:Error:%s" % str(e))

    if len(transcripts) > 0:
        print("\n-Trinitty:User said:", transcripts)

    return (transcripts, transcripts_confidence, words, words_confidence, Err_msg)


def Text_To_Speech(txtinput, stayawake=False, savehistory=True):

    def Resample(file):
        try:
            to_rename = Runtime_Tmp_Path("resampled.wav")
            sample = sox.Transformer()
            sample.set_output_format(rate=24000)
            sample.build(file, to_rename)
            print("\n-Trinitty:%s resampled to 24000." % file)
            os.rename(to_rename, file)
            print("\n-Trinitty:%s saved." % file)
            return True
        except Exception as e:
            print("\n-Trinitty:Error:Resample:", str(e))
            return False

    PRINT("\n-Trinitty:Dans la fonction Text_To_Speech")

    PRINT("\n-Trinitty:len(txtinput):", len(txtinput))

    print("\n-Trinitty:\n\n%s\n\n" % txtinput)

    parsed_response = parse_response(str(txtinput))
    PRINT("\n-After Parse:\n%s\n\n" % parsed_response)

    #    err_list = []#TODO
    txt_list = Split_Text(parsed_response)
    wav_list = []
    to_sox = []

    final_wav = Runtime_Tmp_Path("current_answer.wav")
    os.makedirs(Runtime_Tmp_Path(), exist_ok=True)

    Move_To_Error_Folder = False

    Err_Tts = False
    Err_Skip = False
    Err_Pysox = False
    Err_Sample = False
    Err_Concatenation = False

    for n, txt in enumerate(txt_list):
        time.sleep(0.5)
        leadn = str(n).zfill(4)
        #        if len(txt_list) > 1:
        #                fname = "/tmp/answer"+str(leadn)+".wav"
        #        else:
        #                fname = "/tmp/current_answer.wav"
        fname = Runtime_Tmp_Path("answer" + str(leadn) + ".wav")
        Err_cnt = 0
        while True:
            Retry = False
            try:

                client = tts.TextToSpeechClient()
                audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)

                text_input = tts.SynthesisInput(text=txt)
                voice_params = tts.VoiceSelectionParams(language_code="fr-FR", name="fr-FR-Neural2-A")

                response = client.synthesize_speech(input=text_input, voice=voice_params, audio_config=audio_config)
                audio_response = response.audio_content

                try:
                    with open(fname, "wb") as out:
                        out.write(audio_response)
                    wav_list.append(fname)
                except Exception as e:
                    PRINT("\n-Trinitty:Error:", str(e))  # TODO
                    #                     err_list.append("Err_cnt:%s write(gtss)file:%s err:%s"%(str(Err_cnt),SCRIPT_PATH+fname,str(e)))
                    Err_cnt += 1
                    Retry = True

            except Exception as e:
                PRINT("\n-Trinitty:Error:%s" % str(e))
                Err_cnt += 1
                Retry = True

            if Err_cnt == 2:
                Err_Tts = True
                Err_cnt = 0
                try:
                    Run_Pico2Wave(fname, txt)
                    # RESAMPLE 16000 to 24000
                    wav_list.append(fname)
                    Retry = False
                except Exception as e:
                    PRINT("\n-Trinitty:Error:", str(e))
                    Retry = False
                    Err_Skip = True

            if not Retry:
                break
            time.sleep(0.5)

    for f in wav_list:
        if os.path.exists(f):
            try:
                sample_rate = int(sox.file_info.sample_rate(f))
                if sample_rate != 24000:
                    resampled = Resample(f)
                    if resampled:
                        to_sox.append(f)
                    else:
                        Err_Sample = True
                else:
                    to_sox.append(f)
            except Exception as e:
                print("\n-Trinitty:Error:", str(e))
                Err_Sample = True
        else:
            print("\n-Trinitty:Error:Le fichier %s n'existe pas.", str(f))
            Err_Skip = True

    #    print("to_sox:",to_sox)

    if len(to_sox) > 1:
        try:
            cbn = sox.Combiner()
            cbn.convert(samplerate=24000, n_channels=1)
            try:
                cbn.set_input_format(file_type=["wav" for i in to_sox])
            except Exception as e:
                print("\n-Trinitty:Error:", str(e))
            cbn.build(to_sox, final_wav, "concatenate")
        except Exception as e:
            print("\n-Trinitty:Error:Concatenation:", str(e))
            Err_Concatenation = True
    elif len(to_sox) == 1:
        try:
            sample = sox.Transformer()
            sample.set_output_format(rate=24000)
            sample.build(to_sox[0], final_wav)
        except Exception as e:
            PRINT("\n-Trinitty:to_sox:\n%s" % to_sox[0])
            print("\n-Trinitty:Error:pysox:", str(e))
            Err_Pysox = True

    if Err_Tts:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_tts.wav")
    if Err_Skip:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_skip_sox.wav")
        Move_To_Error_Folder = True
    if Err_Pysox:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_answer_sox.wav")
        Move_To_Error_Folder = True
    if Err_Sample:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_sample_sox.wav")
        Move_To_Error_Folder = True
    if Err_Concatenation:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_conc_sox.wav")
        Move_To_Error_Folder = True

    tmp_folder = Runtime_Tmp_Path()
    err_folder = Saved_Answer_Path("saved_error")

    to_skip = ["current_answer.wav", "last_bad_stt.wav"]

    wav_files = [f for f in os.listdir(tmp_folder) if f.endswith(".wav") and f not in to_skip]

    if Move_To_Error_Folder and len(to_sox) > 0:

        while True:
            characters = string.ascii_letters + string.digits
            rnd = Non_Crypto_Token(5, characters)
            rnd_folder = os.path.join(err_folder, rnd)
            if not os.path.exists(rnd_folder):
                try:
                    os.makedirs(rnd_folder)
                    err_folder = rnd_folder
                    break
                except Exception as e:
                    print("\n-Trinitty:Error:os.makedirs(rnd_folder):%s" % str(e))
                    break

        PRINT("\n-Trinitty:Déplacements des fichiers wav temporaire vers %s" % err_folder)

        err_move = False
        for w in wav_files:
            try:
                move(os.path.join(tmp_folder, str(w)), err_folder)
            except Exception as e:
                print("\n-Trinitty:Error:Move:", str(e))
                err_move = True

        if err_move:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_while_moving_to_err.wav")
        else:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_move_to_err.wav")
    else:
        PRINT("\n-Trinitty:Effacement des fichiers wav temporaire de %s" % tmp_folder)

        err_del = False
        for w in wav_files:
            try:
                os.remove(os.path.join(tmp_folder, str(w)))
            except Exception as e:
                print("\n-Trinitty:Error:Move:", str(e))
                err_del = True

        if err_del:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_del_wav.wav")

    if len(to_sox) > 0:

        if Err_Concatenation:
            return Play_Response(stay_awake=stayawake, save_history=savehistory, answer_txt=txtinput)

        return Play_Response(
            audio_response=final_wav,
            stay_awake=stayawake,
            save_history=savehistory,
            answer_txt=txtinput,
        )


    Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_audio_sox.wav")

    if len(txtinput) > 0:

        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_audio_but_txt_sox.wav")
        print("\n\n-Trinitty:Réponse:\n", txtinput)

        return Play_Response(stay_awake=stayawake, save_history=savehistory, answer_txt=txtinput)
    return Play_Response(stay_awake=stayawake, save_history=False)


#    return(Play_Response(audio_response=final_wav,stay_awake=stayawake,save_history=savehistory,answer_txt=txtinput))


def Audio_File_Is_Playable(filepath):
    return str(filepath or "").lower().endswith((".wav", ".mp3", ".ogg", ".flac"))


def Playback_Stop_Command_Detected(text):
    text = str(text or "").strip()
    if not text:
        return False
    ambiguity = Check_Ambiguity(text, allowed_functions=["F_wait", "F_quit"])
    if not ambiguity:
        return False
    return "F_wait" in ambiguity or "F_quit" in ambiguity


def Playback_Interrupt_Listener(stop_event, timeout=None):
    if (
        globals().get("INTERPRETOR", False)
        or globals().get("PUSH_TO_TALK", False)
        or not globals().get("PLAYBACK_INTERRUPT_ENABLED", False)
    ):
        return False

    if timeout is None:
        timeout = globals().get("PLAYBACK_INTERRUPT_TIMEOUT", 30.0)

    try:
        if Start_Thread_Record() is False:
            return False
        deadline = time.monotonic() + float(timeout)
        audio = None
        while not stop_event.is_set() and time.monotonic() < deadline:
            audio = Queue_Get_Optional(audio_datas, timeout=PLAYBACK_POLL_INTERVAL, default=None)
            if audio is not None:
                break

        if stop_event.is_set() or audio is None:
            Stop_Recording()
            return False

        transcripts, transcripts_confidence, words, words_confidence, err_msg = Speech_To_Text(audio)
        text, recognized = Check_Transcript(transcripts, transcripts_confidence, words, words_confidence, err_msg)
        if recognized and Playback_Stop_Command_Detected(text):
            cancel_operation.put(True)
            Stop_Recording()
            return True
    except Exception as e:
        Log_Error("Playback_Interrupt_Listener", e)
        PRINT("\n-Trinitty:Playback_Interrupt_Listener:Error:%s" % str(e))
    return False


def Start_Playback_Interrupt_Listener():
    if (
        globals().get("INTERPRETOR", False)
        or globals().get("PUSH_TO_TALK", False)
        or not globals().get("PLAYBACK_INTERRUPT_ENABLED", False)
    ):
        return None
    Queue_Drain(audio_datas)
    Queue_Drain(No_Input)
    stop_event = Event()
    listener = Thread(target=Playback_Interrupt_Listener, args=(stop_event,), daemon=True)
    listener.start()
    return (stop_event, listener)


def Stop_Playback_Interrupt_Listener(listener_info):
    if not listener_info:
        return
    stop_event, listener = listener_info
    stop_event.set()
    Stop_Recording()
    listener.join(timeout=0.2)


def Run_Playback_Command(command, cancel_event=None):
    if isinstance(command, str):
        PRINT("\n-Trinitty:Run_Playback_Command:refusing raw string command")
        return 127
    try:
        command = [str(part) for part in command]
    except TypeError:
        PRINT("\n-Trinitty:Run_Playback_Command:invalid command")
        return 127
    if not command or not command[0].strip():
        PRINT("\n-Trinitty:Run_Playback_Command:empty command")
        return 127

    try:
        process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603 - argv is validated above and shell is not used.
    except Exception as e:
        Log_Error("Run_Playback_Command", e)
        PRINT("\n-Trinitty:Run_Playback_Command:Error:%s" % str(e))
        return 127

    cancel_queue = globals().get("cancel_operation")
    while process.poll() is None:
        if cancel_event is not None and cancel_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
            return 130
        if cancel_queue is not None and not cancel_queue.empty():
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1)
            return 130
        time.sleep(PLAYBACK_POLL_INTERVAL)

    return process.returncode


def Play_Audio_File(filepath, cancel_event=None):
    filepath = str(filepath or "").strip()
    if not filepath:
        return 1
    if cancel_event is None:
        if filepath.lower().endswith(".wav"):
            return Run_Playback_Command([APLAY_BIN, "-q", filepath])
        return Run_Playback_Command([PLAY_BIN, "-q", filepath])
    if filepath.lower().endswith(".wav"):
        return Run_Playback_Command([APLAY_BIN, "-q", filepath], cancel_event=cancel_event)
    return Run_Playback_Command([PLAY_BIN, "-q", filepath], cancel_event=cancel_event)


def Play_Response(audio_response=None, stay_awake=False, save_history=True, answer_txt=None):
    PRINT("\n-Trinitty:Dans la fonction Play_Response")

    if audio_response:
        listener = Start_Playback_Interrupt_Listener()
        try:
            Play_Audio_File(audio_response)
        finally:
            Stop_Playback_Interrupt_Listener(listener)

    if save_history:
        if audio_response:
            Save_History(answer_txt)
        else:
            Save_History(answer_txt, no_audio=True)

    if not stay_awake:
        Go_Back_To_Sleep(True)


def dbg_queue():

    PRINT("\n-Trinitty:sleep.empty:%s" % cancel_operation.empty())
    PRINT("\n-Trinitty:start.empty:%s" % wake_me_up.empty())
    PRINT("\n-Trinitty:chunks.empty:%s" % chunks.empty())
    PRINT("\n-Trinitty:audio_datas:%s" % audio_datas.empty())


def Start_Thread_Record():
    PRINT("\n-Trinitty:start thread rec")
    if not Audio_Input_Available():
        cancel_operation.put(True)
        No_Input.put(True)
        return False

    record_on.put(True)

    RQ = Thread(target=Record_Query, daemon=True)
    RQ.start()
    CS = Thread(target=Check_Silence, daemon=True)
    CS.start()
    return True


def Go_Back_To_Sleep(go_trinitty=True):

    global Current_Category

    PRINT("\n\n------\n-Trinitty:Remise en veille-----\n\n")

    Queue_Drain(record_on)
    Queue_Drain(chunks)
    Queue_Drain(wake_me_up)
    wake_me_up.put(True)
    Queue_Drain(awake)
    Queue_Drain(cancel_operation)
    Queue_Drain(No_Input)
    Queue_Drain(score_sentiment)
    Queue_Drain(audio_datas)
    Queue_Drain(last_sentence)

    if len(Current_Category) > 0:
        Current_Category = []

    if go_trinitty:
        PRINT("\n-Trinitty:Retour vers trinitty()\n")
        return Trinitty("WakeMe")
    return ()


def Wait_for(action, timeout=None):
    PRINT("\n-Trinitty:wait for %s" % action)

    if timeout is None:
        timeout = WAIT_FOR_TIMEOUT
    deadline = time.monotonic() + float(timeout)

    while time.monotonic() < deadline:

        if action == "audio":
            if not audio_datas.empty():
                break

        if action == "question":
            if not score_sentiment.empty():
                break

        if not cancel_operation.empty():
            break

        time.sleep(WAIT_FOR_POLL_INTERVAL)
    else:
        PRINT("\n-Trinitty:Operation %s timed out." % action)
        Stop_Recording()
        cancel_operation.put(True)
        return False

    if not cancel_operation.empty():
        PRINT("\n-Trinitty:Operation %s cancelled." % action)
        return False
    PRINT("\n-Trinitty:Operation %s finished." % action)
    return True


#       time.sleep(1)


def similar(txt1, txt2):
    PRINT("\n-Trinitty:txt1:", txt1)
    PRINT("\n-Trinitty:txt2:", txt2)
    similarity = SequenceMatcher(None, txt1, txt2).ratio()
    PRINT("\n-Trinitty:Similarity : ", similarity)
    return similarity


def get_wordnet_pos(treebank_tag):
    if treebank_tag.startswith("J"):
        return wordnet.ADJ
    if treebank_tag.startswith("V"):
        return wordnet.VERB
    if treebank_tag.startswith("N"):
        return wordnet.NOUN
    if treebank_tag.startswith("R"):
        return wordnet.ADV
    return wordnet.NOUN


def preprocess(txt,Isolate_Search=False):
    _ = Isolate_Search
    sentence = unidecode(txt)
    sentence = sentence.lower()
    sentence = "".join(char for char in sentence if char not in string.punctuation)
    tokens = word_tokenize(sentence)
    stop_words = set(stopwords.words("french"))
    tokens = [word for word in tokens if word.isalnum() and word not in stop_words]
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(word, get_wordnet_pos(tag)) for word, tag in pos_tag(tokens)]
    return " ".join(tokens)

def Quit(from_function=None):


    if from_function:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/quit/quit_fnc.wav")
    else:
        hour = datetime.now().hour
        if hour > 20 or hour < 8:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/quit/quit_night.wav")
        elif hour >= 8 and hour < 13:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/quit/quit_day.wav")
        elif hour >= 13 and hour < 18:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/quit/quit_afternoon.wav")
        elif hour >= 18 and hour <=20:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/quit/quit_evening.wav")
        PRINT("\n-Trinitty:Quit():local_sounds/boot/xspx.wav")
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/boot/xspx.wav")
        sys.exit(0)

def Wait(self_launched=False,allowed_functions=None,from_function=None,timeout=None):
    PRINT("\n-Trinitty:Dans la fonction Standing_By")

    if INTERPRETOR:
        return Prompt(allowed_functions,from_function)
    if globals().get("PUSH_TO_TALK", False):
        return Push_To_Talk()

    if timeout is None and not self_launched:
        timeout = WAIT_FOR_TIMEOUT
    deadline = None
    if timeout is not None:
        timeout = float(timeout)
        if timeout > 0:
            deadline = time.monotonic() + timeout

    word_key = SCRIPT_PATH + "/models/trinity_fr_raspberry-pi_v3_0_0.ppn"
    word_key2 = SCRIPT_PATH + "/models/interpreteur_fr_raspberry-pi_v3_0_0.ppn"
    pvfr = SCRIPT_PATH + "/models/porcupine_params_fr.pv"
    porcupine = None
    keyword_index = None
    audio_stream = None
    pa = None

    if self_launched:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/wait/selfwait.wav")

    else:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/wait.wav")

    try:
        porcupine = pvporcupine.create(
            access_key=PICO_KEY,
            model_path=pvfr,
            keyword_paths=[word_key,word_key2],
            sensitivities=[1,1],
        )
        with ignoreStderr():
            pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
        )
        print("\n-Trinitty:En attente d'instruction...")

        while deadline is None or time.monotonic() < deadline:
            pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            keyword_index = porcupine.process(pcm)
            if keyword_index == 0:
                PRINT("\n-Trinitty:keyword_index:", keyword_index)
                rnd = str(Non_Crypto_Randint(1, 15))
                wake_sound = SCRIPT_PATH + "/local_sounds/wakesounds/" + rnd + ".wav"
                Play_Audio_File(wake_sound)
                break
            if keyword_index == 1:
                break
        else:
            PRINT("\n-Trinitty:Wait timed out.")
            keyword_index = WAIT_TIMEOUT
    except Exception as e:
        Log_Error("Wait", e)
        PRINT("\n-Trinitty:Wait:Error:%s" % str(e))
        return Go_Back_To_Sleep(go_trinitty=False)
    finally:
        PRINT("\n-Trinitty:Awake.")
        if porcupine is not None:
            porcupine.delete()
        if audio_stream is not None:
            audio_stream.close()
        if pa is not None:
            pa.terminate()
    if keyword_index is WAIT_TIMEOUT:
        return WAIT_TIMEOUT
    if keyword_index == 1:
        return Prompt(allowed_functions,from_function)
    return None


def Push_To_Talk():
    if not Audio_Input_Available():
        return Go_Back_To_Sleep(False)
    input("\n-Trinitty:Appuyez sur Entree pour parler.")
    return Trinitty("Speech_To_Text")


def Isolate_Search(txt, function_name):

    def rm_trigger(trigtok,isolated_tokens,full_tokens):

       Forbiden_Id = []

       for trig in trigtok:
           bucket_name = []
           bucket_id = []
           starlock = False
           idx = 0
           for token in full_tokens:
               PRINT(f"\n-Trinitty:rm_trigger:Texte: {token.text}, Hash: {token.orth} i:{token.i} idx:{token.idx}")
               if idx >= len(trig):
                  PRINT("\n-Trinitty:rm_trigger:Break: idx %s > len(trig) %s"%( idx,len(trig)) )
                  break
               if trig[idx] == "*":
                  idx += 1
                  starlock = True
               elif trig[idx] == token.text:
                    PRINT(f"\n-Trinitty:rm_trigger:trig[idx]:{trig[idx]} == token:{token.text}")
                    bucket_id.append(token.i)
                    bucket_name.append(token.text)
                    idx += 1
                    PRINT("\n-Trinitty:rm_trigger:bucket_name:",bucket_name)
                    PRINT("\n-Trinitty:rm_trigger:bucket_id:",bucket_id)
                    if starlock:
                       starlock = False
               elif starlock :
                       continue
               else:
                       bucket_id = []
                       bucket_name = []
                       starlock = False
                       idx =  0
                       PRINT("\n-Trinitty:rm_trigger:starlock reset bucket reset")

           for id in bucket_id:
              if id not in Forbiden_Id:
                  Forbiden_Id.append(id)


       clean_request = []
       for it in isolated_tokens:
            PRINT(f"\n-Trinitty:rm_trigger:it.txt {it.text} it.i {it.i} it.i in bucket_id:{it.i in bucket_id}")
            if it.i not in Forbiden_Id:
                clean_request.append(it.text)

       PRINT("\n-Trinitty:Isolate_Search():rm_trigger:txt:",txt)
       PRINT("\n-Trinitty:Isolate_Search():rm_trigger:function_name:%s" % function_name)
       PRINT("\n-Trinitty:rm_trigger:trigtok:",trigtok)
       PRINT("\n-Trinitty:rm_trigger:Isolated_token:%s\n"%[tok.text for tok in isolated_tokens])
       PRINT("\n-Trinitty:rm_trigger:clean_request:",clean_request)
       return(" ".join(clean_request))


    nlp = spacy.load(globals().get("SPACY_MODEL", "fr_core_news_md"))
    doc = nlp(txt)
    tokenizer = nlp.tokenizer

    trigtok = []
    isolated_wanabe = []

    for _n,token in enumerate(doc):
        if token.text == ".":
              if token.is_punct and token.head.pos_ == "VERB" and len(isolated_wanabe) > 0:
                  PRINT("\nBreakpoint")
                  break

        elif any(dep in token.dep_ for dep in ["obj", "obl"]) and token.dep_ != "iobj" and token.head.pos_ == "VERB":

              PRINT(f"\nIsolate_Search:Texte: {token.text}")
              PRINT(f"Isolate_Search:Lemme: {token.lemma_}")
              PRINT(f"Isolate_Search:Token len: {len(token.text)}")
              PRINT(f"Isolate_Search:Token type (POS): {token.pos_}")
              PRINT(f"Isolate_Search:Tag de POS détaillé: {token.tag_}")
              PRINT(f"Isolate_Search:Dépendance: {token.dep_} - {spacy.explain(token.dep_)}")
              PRINT(f"Isolate_Search:Token principal (head): {token.head.text}")
              PRINT(f"Isolate_Search:token.head.pos_: {token.head.pos_}")
              PRINT(f"Isolate_Search:Entité nommée: {token.ent_type_}")
              PRINT(f"Isolate_Search:Est un stop word ? {token.is_stop}")
              PRINT(f"Isolate_Search:Est alphabétique ? {token.is_alpha}")
              PRINT(f"Isolate_Search:Est en minuscule ? {token.is_lower}")
              PRINT(f"Isolate_Search:Est en majuscule ? {token.is_upper}")
              PRINT(f"Isolate_Search:Est un nombre ? {token.like_num}")
              PRINT(f"Isolate_Search:Est une ponctuation ? {token.is_punct}")
              PRINT(f"Isolate_Search:Est un espace ? {token.is_space}")
              PRINT(f"Isolate_Search:Forme originale : {token.shape_}")

              PRINT(f"Isolate_Search:subtree: {[t.text for t in token.subtree]}")
              PRINT(f"Isolate_Search:Ancetres: {[t.text for t in token.ancestors]}")

              PRINT(f"Isolate_Search:left_edge: {token.left_edge}")
              PRINT(f"Isolate_Search:right_edge: {token.right_edge}")

              PRINT("Isolate_Search:Enfants du token :")
              for child in token.children:
                  PRINT(f"  Enfant : {child.text}, Dépendance : {child.dep_}")

              PRINT("Isolate_Search:Tokens à gauche :")
              for left in token.lefts:
                  PRINT(f"  Gauche : {left.text}, Dépendance : {left.dep_}")

              PRINT("Isolate_Search:Tokens à droite :")
              for right in token.rights:
                  PRINT(f"  Droite : {right.text}, Dépendance : {right.dep_}")

              PRINT("-------------------------------")


              if token not in isolated_wanabe:
                  for st in token.subtree:
                      if st not in isolated_wanabe:
                             isolated_wanabe.append(st)
                      else:
                            PRINT(f"Isolate_Search:token subtree {st.text} already in isolated_wanabe")
              else:
                  PRINT(f"Isolate_Search:token {token.text} already in isolated_wanabe")


    triggers = Check_Ambiguity(txt, to_get=function_name)
    try:
         if triggers:
              triggers = triggers[function_name][0][1]
              for trig in triggers:
                  trigtok.append([token.text for token in tokenizer(trig)])
         else:
              PRINT("\n-Trinitty:Isolate_Search():Failed at triggers")
              return(" ".join([iw.text for iw in isolated_wanabe]))
    except Exception as e:
         PRINT("\n-Trinitty:Isolate_Search():Failed:Error:\n%s"%str(e))
         return(txt)



    return rm_trigger(trigtok,isolated_wanabe,doc)




def Reducto(txt):
    if len(txt) > 300:
        txt = txt[:300] + "(...)"
    return txt


def NbrToTts(number=None,timestamp=None):
    def datewav(*parts):
         return Local_Sound_Path("dates", *parts)

    def nbrtowav(n):
         pathwav = []
         if n >= 1000:
             milliers_part = n // 1000
             n = n % 1000
             pathwav.append(datewav("milliers", MILLIERS[milliers_part - 1].replace(" ","_")+".wav"))
         if n >= 100:
             centaines_part = n // 100
             n = n % 100
             pathwav.append(datewav("centaines", CENTAINES[centaines_part - 1].replace(" ","_")+".wav"))
         if n > 0:
             pathwav.append(datewav("nombres", NOMBRES[n - 1].replace(" ","_")+".wav"))
         return pathwav

    wavs = []
    if number is not None and timestamp is None:
        return " ".join(nbrtowav(number))
    if timestamp is not None and number is None:
         dobject = datetime.fromtimestamp(timestamp)
         daystr = JOURS[dobject.weekday()]
         mnthstr = MOIS[dobject.month - 1]
         fdate = "%s %s %s %s" % (daystr, dobject.day, mnthstr, dobject.year)
         print("fdate:",fdate)

         daynbr = dobject.day
         wavday = nbrtowav(daynbr)
         yearnbr = dobject.year
         wavyear = nbrtowav(yearnbr)

         wavs.append(datewav("jours", daystr+".wav"))
         wavs.extend(wavday)
         wavs.append(datewav("mois", mnthstr+".wav"))
         wavs.extend(wavyear)

         print("wavs:",wavs)

         aplay_cmd = [APLAY_BIN, "-q"] + wavs
         print("aplay_cmd:", " ".join(aplay_cmd))
         return Run_Playback_Command(aplay_cmd)
    return None


def Trinitty_Script_Profile():
   script_file = SCRIPT_PATH + "/trinitty.py"
   todo_file = SCRIPT_PATH + "/TODO"
   profile = {
      "script_file": script_file,
      "line_count": 0,
      "function_count": 0,
      "functions": [],
      "todo_open": [],
      "todo_partial": [],
      "suggestions": [],
   }

   if os.path.exists(script_file):
      with open(script_file) as f:
         source = f.read()
      profile["line_count"] = len(source.splitlines())
      profile["functions"] = re.findall(r"^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source, re.MULTILINE)
      profile["function_count"] = len(profile["functions"])

   if os.path.exists(todo_file):
      with open(todo_file) as f:
         for line in f:
            stripped = line.strip()
            if stripped.startswith("# TODO -"):
               profile["todo_open"].append(stripped.replace("# TODO -", "").strip())
            elif stripped.startswith("# PARTIAL -"):
               profile["todo_partial"].append(stripped.replace("# PARTIAL -", "").strip())

   if profile["todo_open"]:
      profile["suggestions"].append("Prioriser: %s" % profile["todo_open"][0])
   if profile["todo_partial"]:
      profile["suggestions"].append("Finaliser: %s" % profile["todo_partial"][0])
   if not profile["suggestions"]:
      profile["suggestions"].append("Continuer a ajouter des tests de regression avant les refactors.")

   return profile


def Trinitty_Script_Text(profile=None):
   profile = profile or Trinitty_Script_Profile()
   text = (
      "Le script principal est %s. Il contient %s lignes et %s fonctions."
      % (
         profile["script_file"],
         profile["line_count"],
         profile["function_count"],
      )
   )
   if profile["todo_open"]:
      text += " Prochain chantier: %s." % profile["todo_open"][0]
   if profile["suggestions"]:
      text += " Suggestion: %s." % profile["suggestions"][0]
   return text


def Trinitty_Script():
   script_file = SCRIPT_PATH + "/trinitty.py"
   script_text = Trinitty_Script_Text()
   print("\n-Trinitty:Script source:%s" % script_file)
   print("\n-Trinitty:Script profile:%s" % script_text)
   if globals().get("INTERPRETOR", False):
       return script_file
   try:
       Text_To_Speech(script_text, stayawake=False, savehistory=False)
   except Exception as e:
       PRINT("\n-Trinitty:Trinitty_Script():Text_To_Speech error:%s" % str(e))
   return script_file


def Result_Text(result_object):
   if result_object is None:
      return ""

   if isinstance(result_object, (list, tuple)):
      text_parts = []
      for item in result_object:
         item_text = Result_Text(item)
         if item_text:
            text_parts.append(item_text)
      return "\n\n".join(text_parts).strip()

   if isinstance(result_object, dict):
      text_fields = [
          "google_title",
          "google_description",
          "hist_input_full",
          "hist_input_short",
          "hist_output",
      ]
      text_parts = []
      for field in text_fields:
         value = result_object.get(field)
         if value:
            text_parts.append(str(value))
      if text_parts:
         return "\n".join(text_parts).strip()

   return str(result_object).strip()


def Result_Display_Text(result_object, result_number=None):
   if not isinstance(result_object, dict):
      return Result_Text(result_object)

   labels = [
      ("google_title", "Titre"),
      ("google_description", "Description"),
      ("google_url", "URL"),
      ("hist_input_full", "Question"),
      ("hist_input_short", "Question courte"),
      ("hist_output", "Reponse"),
      ("hist_urls", "URLs"),
      ("hist_tstamp", "Date"),
      ("hist_score", "Score"),
   ]
   lines = []
   if result_number is not None:
      lines.append("Resultat %s" % result_number)

   for field, label in labels:
      value = result_object.get(field)
      if value:
         lines.append("%s: %s" % (label, value))

   return "\n".join(lines).strip()


def Display_Result(result_object, result_number=None):
   display_text = Result_Display_Text(result_object, result_number=result_number)
   if display_text:
      print("\n%s" % display_text)
   return display_text


def Read_Results(result_object):

   PRINT("\n-Trinitty:Read_Results:object:%s" % (result_object,))
   text = Result_Text(result_object)
   if not text:
      PRINT("\n-Trinitty:Read_Results:no readable text")
      return ""

   print("\n-Trinitty:Read_Results:\n%s" % text)
   if globals().get("INTERPRETOR", False):
      return text

   try:
      Text_To_Speech(text, stayawake=False, savehistory=False)
   except Exception as e:
      PRINT("\n-Trinitty:Read_Results():Text_To_Speech error:%s" % str(e))
   return text


def Results_Hub_Normalize_Text(text):
   text = str(text or "").lower()
   try:
      text = unidecode(text)
   except Exception as e:
      Log_Error("Results_Hub_Normalize_Text", e)
   return text


def Results_Hub_Selection_Rules():
   rules_file = SCRIPT_PATH + "/datas/numbers.trinity"
   rules = []
   if not os.path.exists(rules_file):
      return rules

   try:
      with open(rules_file, newline="") as csvfile:
         reader = csv.DictReader(csvfile)
         for row in reader:
            if row.get("function") != "F_select_result":
               continue
            phrase = Results_Hub_Normalize_Text(row.get("txt_nbr", "")).strip()
            value = str(row.get("value", "")).strip().strip('"').strip()
            if phrase:
               rules.append((phrase, value))
   except Exception as e:
      PRINT("\n-Trinitty:Results_Hub_Selection_Rules():%s" % str(e))

   return sorted(rules, key=lambda item: len(item[0]), reverse=True)


def Results_Hub_Parse_Range_Value(value, result_count):
   if not value:
      if result_count <= 0:
         return None
      result_id = Non_Crypto_Randint(0, result_count - 1)
      return result_id, result_id + 1

   if ":" in value:
      try:
         start, end = value.split(":", 1)
         start = int(start.strip())
         end = int(end.strip())
      except Exception:
         return None
   else:
      try:
         start = int(value.strip()) - 1
         end = start + 1
      except Exception:
         return None

   start = max(0, start)
   end = min(result_count, end)
   if start >= end:
      return None
   return start, end


def Results_Hub_Number_Words():
   return {
      "premier": 1,
      "premiere": 1,
      "premiers": 1,
      "premieres": 1,
      "un": 1,
      "une": 1,
      "second": 2,
      "seconde": 2,
      "seconds": 2,
      "secondes": 2,
      "deuxieme": 2,
      "deuxiemes": 2,
      "deux": 2,
      "troisieme": 3,
      "troisiemes": 3,
      "trois": 3,
      "quatrieme": 4,
      "quatriemes": 4,
      "quatre": 4,
      "cinquieme": 5,
      "cinquiemes": 5,
      "cinq": 5,
      "sixieme": 6,
      "sixiemes": 6,
      "six": 6,
      "septieme": 7,
      "septiemes": 7,
      "sept": 7,
      "huitieme": 8,
      "huitiemes": 8,
      "huit": 8,
      "neuvieme": 9,
      "neuviemes": 9,
      "neuf": 9,
      "dixieme": 10,
      "dixiemes": 10,
      "dix": 10,
   }


def Results_Hub_Number_From_Token(token):
   if not token:
      return None
   if re.match(r"^\d+$", token):
      return int(token)
   return Results_Hub_Number_Words().get(token)


def Results_Hub_Match_Rule_Phrase(normalized_text, phrase):
   phrase = re.sub(r"[^a-z0-9]+", " ", Results_Hub_Normalize_Text(phrase)).strip()
   if not phrase:
      return False
   return re.search(r"(^|\s)%s(\s|$)" % re.escape(phrase), normalized_text) is not None


def Results_Hub_Text_Has_Duration(tokens):
   duration_tokens = set([
      "seconde",
      "secondes",
      "minute",
      "minutes",
      "heure",
      "heures",
   ])
   wait_tokens = set([
      "attend",
      "attends",
      "attendez",
      "attendre",
      "pause",
      "veille",
      "patiente",
      "patientez",
      "laisse",
      "laissez",
      "stop",
   ])
   return bool(duration_tokens.intersection(tokens) and wait_tokens.intersection(tokens))


def Results_Hub_Selection_Range(command_text, result_count):
   if result_count <= 0:
      return None

   normalized = re.sub(r"[^a-z0-9]+", " ", Results_Hub_Normalize_Text(command_text)).strip()
   tokens = normalized.split()
   selector_tokens = set([
      "resultat",
      "resultats",
      "reponse",
      "reponses",
      "numero",
      "numeros",
      "num",
      "n",
      "fichier",
      "fichiers",
      "audio",
      "audios",
   ])
   filler_tokens = selector_tokens | set(["le", "la", "les", "du", "de", "des", "deg"])

   for index, token in enumerate(tokens[:-1]):
      number = Results_Hub_Number_From_Token(token)
      if not number:
         continue
      if tokens[index + 1] in ("premier", "premiere", "premiers", "premieres"):
         parsed = Results_Hub_Parse_Range_Value("0:%s" % number, result_count)
         if parsed:
            return parsed

   for index, token in enumerate(tokens):
      number = Results_Hub_Number_From_Token(token)
      if not number:
         continue
      if index > 0 and tokens[index - 1] in ("les", "tout", "tous", "toutes"):
         parsed = Results_Hub_Parse_Range_Value("0:%s" % number, result_count)
         if parsed:
            return parsed

   for index, token in enumerate(tokens):
      if token not in selector_tokens:
         continue
      for candidate in tokens[index + 1:index + 6]:
         if candidate in filler_tokens:
            continue
         number = Results_Hub_Number_From_Token(candidate)
         if number:
            parsed = Results_Hub_Parse_Range_Value(str(number), result_count)
            if parsed:
               return parsed
         break

   if not any(token in selector_tokens for token in tokens) and Results_Hub_Text_Has_Duration(tokens):
      return None

   for token in tokens:
      number = Results_Hub_Number_From_Token(token)
      if number:
         parsed = Results_Hub_Parse_Range_Value(str(number), result_count)
         if parsed:
            return parsed

   for phrase, value in Results_Hub_Selection_Rules():
      if Results_Hub_Match_Rule_Phrase(normalized, phrase):
         parsed = Results_Hub_Parse_Range_Value(value, result_count)
         if parsed:
            return parsed

   return None


def Results_Hub_Select_Results(command_text, results_list, default_all=True):
   if not results_list:
      return []

   result_range = Results_Hub_Selection_Range(command_text, len(results_list))
   if result_range:
      start, end = result_range
      return results_list[start:end]

   if default_all:
      return results_list
   return results_list[:1]


def Results_Hub_First_Value(results_list, fields):
   for result in results_list:
      if not isinstance(result, dict):
         continue
      for field in fields:
         value = result.get(field)
         if not value:
            continue
         if isinstance(value, list):
            if value:
               return str(value[0])
         value = str(value).strip()
         if not value:
            continue
         urls = re.findall(r"""https?://[^\s,'"()\[\]]+""", value)
         if urls:
            return urls[0]
         return value
   return ""


def Results_Hub_Sort_Results(command_text, results_list):
   normalized = Results_Hub_Normalize_Text(command_text)
   reverse = not ("anti" in normalized or "ancien" in normalized)

   def sort_value(result):
      if not isinstance(result, dict):
         return 0
      for field in ["hist_epok", "hist_score"]:
         value = result.get(field)
         try:
            return float(value)
         except (TypeError, ValueError):
            continue
      return 0

   return sorted(results_list, key=sort_value, reverse=reverse)


def Results_Hub_Allowed_Functions(result_functions):
   allowed = []
   for function_name in list(result_functions or []) + ["F_read_results", "F_sort_results", "F_rnd", "F_wait", "F_quit"]:
      if function_name not in allowed:
         allowed.append(function_name)
   return allowed


def Results_Hub_Handle_Command(command, results_list, command_text=None, from_function=None):
    if command is WAIT_TIMEOUT:
        return Go_Back_To_Sleep(go_trinitty=True)

    if isinstance(command, tuple):
        command, command_text = command

    if not command:
        return RESULTS_HUB_CONTINUE

    if command == "no cmd":
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/err_cmd.wav")
        return ()

    if command == "F_read_results":
        selected_results = Results_Hub_Select_Results(command_text, results_list, default_all=True)
        Read_Results(selected_results)
        return Go_Back_To_Sleep(go_trinitty=True)

    if command == "F_read_link":
        selected_results = Results_Hub_Select_Results(command_text, results_list, default_all=False)
        url = Results_Hub_First_Value(selected_results, ["google_url", "hist_urls"])
        if url:
            return ReadLink(txtinput=Result_Text(selected_results), urlinput=url)
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_url_not_valid.wav")
        return ()

    if command == "F_play_audio":
        selected_results = Results_Hub_Select_Results(command_text, results_list, default_all=False)
        wav_file = Results_Hub_First_Value(selected_results, ["hist_output_wav", "hist_input_wav"])
        if wav_file:
            return Play_Response(wav_file, stay_awake=False, save_history=False)
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_respons.wav")
        return ()

    if command == "F_sort_results":
        sorted_results = Results_Hub_Sort_Results(command_text, results_list)
        return Results_Hub(sorted_results, from_function=from_function or "Search_History")

    if command == "F_rnd":
        if not results_list:
            return RESULTS_HUB_CONTINUE
        Read_Results([Non_Crypto_Choice(results_list)])
        return Go_Back_To_Sleep(go_trinitty=True)

    if command == "F_quit":
        return Quit(from_function="Results_Hub")

    if command == "F_wait":
        return Wait(from_function="Results_Hub")

    PRINT("\n-Trinitty:Results_Hub():unsupported command from prompt:%s" % command)
    return Go_Back_To_Sleep(go_trinitty=False)


def Results_Hub(original_result,topx_res=None,from_function=None):

    Exit = False

    normalised_results = []
    fnc_rhub = []
    keys_to_function = {
                       "hist_input_full":["F_read_results"],
                       "hist_input_short":["F_read_results"],
                       "hist_input_wav":["F_play_audio"],
                       "hist_output_wav":["F_play_audio"],
                       "hist_urls":["F_read_link"],
                       "google_title":["F_read_results"],
                       "google_description":["F_read_results"],
                       "google_url":["F_read_link"],
                       }

#google_result.append({"google_title":title,"google_description":description, "google_url":url})

    if topx_res:
        PRINT("\n-Trinitty:Results_Hub(original_result items nbr=%s,topx_res items nbr:%s,from_function=%s)\n"%(len(original_result),len(topx_res),str(from_function)))
        results_list = topx_res
    else:
        PRINT("\n-Trinitty:Results_Hub(original_result items nbr=%s,from_function=%s)\n"%(len(original_result),str(from_function)))
        results_list = original_result


    if from_function == "Show_History":
          Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/show_history.wav")

    elif from_function == "Search_History":

         if len(results_list) == 1:
             Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/found_one.wav")
         elif len(results_list) == 2:
             Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/found_two.wav")
         elif len(results_list) == 3:
             Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/found_three.wav")
         elif len(results_list) == 4:
             Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/found_four.wav")
         elif len(results_list) >= 5 and topx_res:
             Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/found_five.wav")
         elif len(results_list) >= 5 and not topx_res:
             Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/found_all.wav")
         else:
             Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/no_result.wav")
             return ()

    elif from_function == "Google":
         Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/googleres.wav")

    for n,res in enumerate(results_list,start=1):

       print("\n\n==Résultat: %s==\n"%str(n))
       Display_Result(res, result_number=n)

       bucket = {}

       for k, v in res.items():
           if k in keys_to_function and v:
               PRINT("keys_to_function[%s]:%s v=%s" % (k, keys_to_function[k], v))
               if isinstance(keys_to_function[k], list):
                  for fnc in keys_to_function[k]:
                      tmpbucket = []
                      if fnc not in fnc_rhub:
                          fnc_rhub.append(fnc)
                          tmpbucket.append(fnc)
                      bucket[k] = tmpbucket
               elif keys_to_function[k] not in fnc_rhub:
                  fnc_rhub.append(keys_to_function[k])
                  bucket[k] = keys_to_function[k]

#           print("-%s: %s"%(k,v))

       if bucket:
          bucket = {'r_nbr': n, **bucket}
          normalised_results.append(bucket)
    if globals().get("DEBUG", False):
        print("\nfnc_rhub:",fnc_rhub)
    #    print("\nnormalised_results:")

        for n in normalised_results:
            print(n)

##
##
    allowed_results_functions = Results_Hub_Allowed_Functions(fnc_rhub)
    cmd_from_prompt = Wait(self_launched=True,allowed_functions=allowed_results_functions,from_function="Results_Hub")
##
##
    handled_command = Results_Hub_Handle_Command(cmd_from_prompt, results_list, from_function=from_function)
    if handled_command is not RESULTS_HUB_CONTINUE:
         return handled_command

    attempts = 0
    while attempts < RESULTS_HUB_MAX_ATTEMPTS:
        time.sleep(0.5)
        attempts += 1
        Exit = False

        if len(results_list) > 1:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/question/search_history_cmds.wav")
        else:
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/question/search_history_cmd.wav")

#        if not INTERPRETOR:
        if Start_Thread_Record() is False:
            return Go_Back_To_Sleep(go_trinitty=False)

        if Wait_for("audio"):
            audio = Queue_Get_Optional(audio_datas, timeout=0.2, default=None)
            if audio is not None:
                transcripts, transcripts_confidence, words, words_confidence, Err_msg = Speech_To_Text(audio)
                txt, _fconf = Check_Transcript(transcripts, transcripts_confidence, words, words_confidence, Err_msg)
                Exit = Commandes(txt=txt,allowed_functions=allowed_results_functions,from_function="Results_Hub")
                #def Commandes(txt,allowed_functions=None,from_function=None)
        else:
            return Go_Back_To_Sleep(go_trinitty=True)

        handled_command = Results_Hub_Handle_Command(Exit, results_list, command_text=txt, from_function=from_function)
        if handled_command is not RESULTS_HUB_CONTINUE:
            return handled_command

        Play_Audio_File(SCRIPT_PATH + "/local_sounds/history/err_cmd.wav")

    return Go_Back_To_Sleep(go_trinitty=True)

def Show_History():
    PRINT("\n-Trinitty:Show_History()")
    if len(Loaded_History_List) == 0:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_history.wav")
        return ()

    history_sort_asc = []

    for n,hitem in enumerate(Loaded_History_List):
        try:
            float(hitem["hist_epok"])
            history_sort_asc.append(hitem)
        except Exception:
            print("\n-Trinitty:Show_History():Error Loaded_History_List[%s]['epok'] != float:"%n)
            print("\n-Trinitty:Loaded_History_List[%s]:\n%s"%(n,hitem))


    return( Results_Hub(history_sort_asc,from_function="Show_History") )


def History_Fieldnames():
    return [
        "hist_file",
        "hist_cats",
        "hist_input_full",
        "hist_input_short",
        "hist_input_wav",
        "hist_output",
        "hist_output_wav",
        "hist_urls",
        "hist_epok",
        "hist_tstamp",
    ]


def History_Category_File_Name(category):
    value = str(category or "nocat")
    value = value.replace("/", ".").replace("\\", ".")
    value = value.replace("-", ".").replace("&", "and").replace(",", ".").replace(")", ".").replace("(", ".")
    value = re.sub(r"[^\w.]+", ".", value)
    value = re.sub(r"\.+", ".", value).strip(".")
    return value or "nocat"


def History_Dir():
    return Writable_Runtime_Dir("history")


def History_File_Path(hist_file):
    return os.path.join(History_Dir(), History_Category_File_Name(hist_file))


def Write_History_File(filepath, rows):
    with open(filepath, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=History_Fieldnames())
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in History_Fieldnames()})


def Delete_Last_History_Entry():
    global Loaded_History_List

    candidates = []
    for index, entry in enumerate(Loaded_History_List):
        try:
            candidates.append((float(entry.get("hist_epok", 0)), index, entry))
        except (TypeError, ValueError):
            continue

    if not candidates:
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/errors/err_no_history.wav")
        return False

    _epok, index, entry = max(candidates, key=lambda candidate: candidate[0])
    filepath = History_File_Path(entry.get("hist_file"))
    if not os.path.exists(filepath):
        PRINT("\n-Trinitty:Delete_Last_History_Entry:history file missing:%s" % filepath)
        return False

    with open(filepath, newline="") as csvfile:
        rows = list(csv.DictReader(csvfile))

    target_epok = str(entry.get("hist_epok", ""))
    new_rows = []
    removed = False
    for row in rows:
        if not removed and str(row.get("hist_epok", "")) == target_epok:
            removed = True
            continue
        new_rows.append(row)

    if not removed:
        PRINT("\n-Trinitty:Delete_Last_History_Entry:entry not found in:%s" % filepath)
        return False

    Write_History_File(filepath, new_rows)
    del Loaded_History_List[index]
    PRINT("\n-Trinitty:Delete_Last_History_Entry:removed:%s" % target_epok)
    return True



def Search_History(to_search):
    to_search = Clean_History_Search_Query(Isolate_Search(to_search,"F_search_history"))

    PRINT("\n-Trinitty:Dans la fonction SearchHistory to_search %s in history." % to_search)

    MatchResults = []

    PRINT("\n-Trinitty:Search_History:%s" % to_search)
    for args in Loaded_History_List:

        hist_file = args["hist_file"]
        hist_cats = args["hist_cats"]
        hist_input_full = args["hist_input_full"]
        hist_input_short = args["hist_input_short"]
        hist_input_wav = args["hist_input_wav"]
        hist_output = args["hist_output"]
        hist_output_wav = args["hist_output_wav"]
        hist_urls = args["hist_urls"]
        hist_epok = args["hist_epok"]
        hist_tstamp = args["hist_tstamp"]
        hist_input_full_search = Normalize_History_Search_Text(hist_input_full)
        hist_input_short_search = Normalize_History_Search_Text(hist_input_short)
        hist_output_search = Normalize_History_Search_Text(hist_output)

        bingoat = 0
        if " " in to_search:
            for n, raw_word in enumerate(to_search.split(" ")):

                if n == 0:
                    word = "%s " % raw_word
                elif n == len(to_search.split(" ")) - 1:
                    word = " %s" % raw_word
                else:
                    word = " %s " % raw_word

                if word in hist_input_full_search:
                    PRINT("\n-Trinitty:Search_History:found partial result in hist_input_full:[%s]" % word)
                    bingoat += 1
                if word in hist_input_short_search:
                    PRINT("\n-Trinitty:Search_History:found partial result in hist_input_short:[%s]" % word)
                    bingoat += 1
                if word in hist_output_search:
                    PRINT("\n-Trinitty:Search_History:found partial result in hist_output:[%s]" % word)
                    bingoat += 1

            if to_search in hist_input_full_search:
                PRINT("\n-Trinitty:Search_History:full match in hist_input_full:[%s]" % to_search)
                bingoat += 5
            if to_search in hist_input_short_search:
                PRINT("\n-Trinitty:Search_History:full match in hist_input_short:[%s]" % to_search)
                bingoat += 5
            if to_search in hist_output_search:
                PRINT("\n-Trinitty:Search_History:full match in hist_output:[%s]" % to_search)
                bingoat += 5
        else:
            if to_search in hist_input_full_search:
                PRINT("\n-Trinitty:Search_History:full match in hist_input_full:[%s]" % to_search)
                bingoat += 1
            if to_search in hist_input_short_search:
                PRINT("\n-Trinitty:Search_History:full match in hist_input_short:[%s]" % to_search)
                bingoat += 1
            if to_search in hist_output_search:
                PRINT("\n-Trinitty:Search_History:full match in hist_output:[%s]" % to_search)
                bingoat += 1

        if bingoat > 0:
            MatchResults.append(
            {
                "hist_file":hist_file,
                "hist_cats":hist_cats,
                "hist_input_full":hist_input_full,
                "hist_input_short":hist_input_short,
                "hist_input_wav":hist_input_wav,
                "hist_output":hist_output,
                "hist_output_wav":hist_output_wav,
                "hist_urls":hist_urls,
                "hist_epok":hist_epok,
                "hist_tstamp":hist_tstamp,
                "hist_score":bingoat,
            }
            )

    if len(MatchResults) > 0:
        SortedMatched = sorted(MatchResults, key=lambda x: x["hist_score"], reverse=True)
        MatchedNbr = len(SortedMatched)
    else:
        SortedMatched = []
        MatchedNbr = 0

    if MatchedNbr > 5:
        MatchedNbr = 5

    TopFive = SortedMatched[:MatchedNbr]

    return(Results_Hub(SortedMatched,TopFive,from_function="Search_History"))


def Check_Time_Dialogue(time_to_substract=None,string=None):
    global LAST_DIALOG

    if not REMEMBER_LAST_15M:
        return string

    if len(LAST_DIALOG) == 0:
        return string

    try:
        last_string = LAST_DIALOG[0]
        last_stamp = LAST_DIALOG[1]

        time_difference = (time_to_substract - last_stamp).total_seconds()
        if time_difference > 1500:
            LAST_DIALOG = ()
            return string
        return """La phrase commencant par "last_input=" représente la derniére phrase qu'un utilisateur t'a posé et tu y as dèja répondu même si tu ne t'en souviens pas.
La phrase commencant par "new_input=" représente une nouvelle interaction du même utilisateur avec toi tu devras répondre à ce que contient "new_input=".
La phrase commencant par "last_input=" peut n'avoir aucun rapport avec "new_input=" tu es donc libre de l'ignorer ou non en fonction de sa pertinence avec "new_input=".
Ne fais aucune mention dans ta réponse de cette consigne.
last_input='%s'
new_input='%s'"""%(last_string,string)
    except Exception as e:
        PRINT("\n-Trinitty:Error:Check_Time_Dialogue:Error", str(e))
        LAST_DIALOG = ()
        return string


def History_Category_Known(categories=None):
    if categories is None:
        categories = globals().get("Current_Category", [])
    if isinstance(categories, str):
        categories = [categories]
    if not categories:
        return False
    first_category = str(categories[0] or "").strip().lower()
    return bool(first_category) and first_category != "nocat"


def Start_History_Classification_Worker(text_content):
    if not Config_Bool(globals().get("HISTORY_CLASSIFICATION_ENABLED", True), default=True):
        return None
    if not text_content or History_Category_Known():
        return None

    def classify_worker():
        try:
            Classify(text_content)
        except Exception as e:
            Log_Error("History_Classify_Worker", e)

    worker = Thread(target=classify_worker, daemon=True)
    worker.start()
    return worker


def Ensure_Current_Category(text_content=None, classify=None):
    global Current_Category

    if isinstance(Current_Category, str):
        Current_Category = [Current_Category.strip()] if Current_Category.strip() else []
    elif Current_Category is None:
        Current_Category = []
    elif not isinstance(Current_Category, list):
        Current_Category = list(Current_Category)

    if classify is None:
        classify = Config_Bool(globals().get("HISTORY_CLASSIFICATION_ENABLED", True), default=True)

    if (
        classify
        and (len(Current_Category) == 0 or not str(Current_Category[0]).strip())
        and text_content
    ):
        Classify(text_content)

    if len(Current_Category) == 0 or not str(Current_Category[0]).strip():
        Current_Category = ["nocat"]

    return Current_Category


def Save_History(answer, no_audio=False):

    global Loaded_History_List
    global LAST_DIALOG

    PRINT("\n-Trinitty:Dans la fonction History")

    if not answer:
        PRINT("\n-Trinitty:No answer saved exiting History")
        return ()

    txt = Queue_Get_Optional(last_sentence, timeout=0.2, default=None)
    if not txt:
        PRINT("\n-Trinitty:No last_ sentence saved exiting History")
        return ()

    PRINT("\n-Trinitty:last sentence:", txt)

    Start_History_Classification_Worker(txt)
    categories = Ensure_Current_Category(txt, classify=False)

    Cat_File = History_Category_File_Name(categories[0])

    Cat_List = ".".join(categories)
    Cat_List = Cat_List.removeprefix(".")

    Lemmatizer = preprocess(txt)

    PRINT("\n-Trinitty:lemmatized last sentence:", Lemmatizer)

    if no_audio:

        new_wav = SCRIPT_PATH + "/local_sounds/errors/err_no_audio_saved.wav"

    else:

        rnd_name = Non_Crypto_Token(16) + ".wav"

        new_wav = Saved_Answer_Path(rnd_name)
        current_wav = Runtime_Tmp_Path("current_answer.wav")

        if os.path.exists(current_wav):
            copyfile(current_wav, new_wav)
        else:
            PRINT("\n-Trinitty:Save_History:current answer wav missing:%s" % current_wav)
            new_wav = SCRIPT_PATH + "/local_sounds/errors/err_no_audio_saved.wav"

    print("\n-Trinitty:Save_History:wav saved at: %s\n"%new_wav)

    tformat = "%Y-%m-%d %H:%M:%S"
    now = datetime.now()

    LAST_DIALOG = (txt,now)

    hist_epok = now.timestamp()

    hist_tstamp = time.strftime(tformat, time.localtime(hist_epok))

    #  hist_file,hist_cats,hist_txt,hist_answer,hist_epok,hist_tstamp,hist_wav

    try:
        history_file = History_File_Path(Cat_File)
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, "a+", newline="") as csvfile:
            fieldnames = [
                "hist_file",
                "hist_cats",
                "hist_input_full",
                "hist_input_short",
                "hist_input_wav",
                "hist_output",
                "hist_output_wav",
                "hist_urls",
                "hist_epok",
                "hist_tstamp",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(
                {
                    "hist_file": Cat_File,
                    "hist_cats": Cat_List,
                    "hist_input_full": txt,
                    "hist_input_short": Lemmatizer,
                    "hist_input_wav":"",
                    "hist_output": answer,
                    "hist_output_wav": new_wav,
                    "hist_urls": URLExtract().find_urls(answer),
                    "hist_epok": hist_epok,
                    "hist_tstamp": hist_tstamp,
                }
            )

            PRINT("\n-Trinitty:wrote history to:%s" % history_file)
            Loaded_History_List.append(

                {
                    "hist_file": Cat_File,
                    "hist_cats": Cat_List,
                    "hist_input_full": txt,
                    "hist_input_short": Lemmatizer,
                    "hist_input_wav":"",
                    "hist_output": answer,
                    "hist_output_wav": new_wav,
                    "hist_urls": URLExtract().find_urls(answer),
                    "hist_epok": hist_epok,
                    "hist_tstamp": hist_tstamp,
                }
            )
            PRINT("\n-Trinitty:Loaded_History_List updated:%s" % len(Loaded_History_List))

    except Exception as e:
        Log_Error("Save_History", e)
        print("\n-Trinitty:Save_History:Error:%s" % str(e))


def Check_History(question, before_replay=None):

    PRINT("\n-Trinitty:Dans la fonction Check_History")

    PRINT("\n-Trinitty:question:", question)

    category_known_before_check = History_Category_Known()
    Start_History_Classification_Worker(question)

    lemmatized = preprocess(question)

    categories = Ensure_Current_Category(question, classify=False)

    Cat_File = History_Category_File_Name(categories[0])

    Joined_Cat = ".".join(categories)
    Joined_Cat = Joined_Cat.removeprefix(".")

    Best_Score = []
    Best_Txt = []
    Best_Answer = []
    Best_Wav = []

    for args in Loaded_History_List:

        hist_file = args["hist_file"]
        hist_cats = args["hist_cats"]
        hist_input_full = args["hist_input_full"]
        hist_input_short = args["hist_input_short"]
        hist_output = args["hist_output"]
        hist_output_wav = args["hist_output_wav"]



        if not category_known_before_check or (Cat_File == hist_file and hist_cats == Joined_Cat):
            hist_input_for_score = hist_input_short or hist_input_full
            score = similar(lemmatized, hist_input_for_score)
            if "wikipedia" in hist_output:
                if score > 0.85:

                    PRINT("\n-Trinitty:hist_cats:", hist_cats)
                    PRINT("\n-Trinitty:hist_input_full:", hist_input_full)
                    PRINT("\n-Trinitty:hist_input_short:", hist_input_short)
                    PRINT("\n-Trinitty:hist_answer:", hist_output)
                    PRINT("\n-Trinitty:hist_wav:", hist_output_wav)
                    PRINT("\n-Trinitty:Score:", score)

                    Best_Score.append(score)
                    if len(hist_input_full) > 0:
                        Best_Txt.append(hist_input_full)
                    else:
                        Best_Txt.append(hist_input_short)
                    Best_Answer.append(hist_output)
                    Best_Wav.append(hist_output_wav)

            else:
                if score > 0.5:
                    PRINT("\n-Trinitty:hist_cats:", hist_cats)
                    PRINT("\n-Trinitty:hist_input_full:", hist_input_full)
                    PRINT("\n-Trinitty:hist_input_short:", hist_input_short)
                    PRINT("\n-Trinitty:hist_answer:", hist_output)
                    PRINT("\n-Trinitty:hist_wav:", hist_output_wav)
                    PRINT("\n-Trinitty:Score:", score)

                    Best_Score.append(score)
                    if len(hist_input_full) > 0:
                        Best_Txt.append(hist_input_full)
                    else:
                        Best_Txt.append(hist_input_short)
                    Best_Answer.append(hist_output)
                    Best_Wav.append(hist_output_wav)

    final_score = 0
    final_wav = ""
    for s in Best_Score:
        if s > final_score:
            final_score = s

    for s, t, _answer, w in zip(Best_Score, Best_Txt, Best_Answer, Best_Wav, strict=False):
        if s == final_score:
            PRINT("\n-Trinitty:Best matches :", t)
            final_wav = w

    if len(final_wav) > 0:

        if callable(before_replay):
            before_replay()

        Play_Audio_File(SCRIPT_PATH + "/local_sounds/already/1.wav")
        Play_Audio_File(final_wav)
        Play_Audio_File(SCRIPT_PATH + "/local_sounds/question/amigood.wav")

        if Start_Thread_Record() is not False and Wait_for("audio"):
            audio = Queue_Get_Optional(audio_datas, timeout=0.2, default=None)
            if audio is None:
                score_sentiment.put(False)
            else:
                transcripts, transcripts_confidence, words, words_confidence, Err_msg = Speech_To_Text(audio)
                txt, _fconf = Check_Transcript(transcripts, transcripts_confidence, words, words_confidence, Err_msg)
                if len(txt) > 0:
                    Question(txt)
                    if not Wait_for("question"):
                        score_sentiment.put(False)
                else:
                    score_sentiment.put(False)
            opinion = Queue_Get_Optional(score_sentiment, timeout=0.2, default=False)
            if opinion in (None, False):
                Play_Audio_File(SCRIPT_PATH + "/local_sounds/notok/1.wav")
                return False
            Play_Audio_File(SCRIPT_PATH + "/local_sounds/ok/1.wav")
            return True
        return False
    return False


def Classify(text_content):

    global Current_Category
    PRINT("\n-Trinitty:Dans la fonction Classify")

    categories = []

    try:
        language_timeout = Config_Positive_Float(globals().get("GOOGLE_LANGUAGE_TIMEOUT", 8.0), 8.0)
        PRINT("\n-Trinitty:Classify timeout:%s" % language_timeout)
        PRINT(
            "\n-Trinitty:GOOGLE_APPLICATION_CREDENTIALS:%s"
            % os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        )
        with Runtime_Timeout(language_timeout, "Google Natural Language classify_text"):
            client = language_v1.LanguageServiceClient()

            type_ = language_v1.Document.Type.PLAIN_TEXT
            language = "fr"
            document = {"content": text_content, "type_": type_, "language": language}
            content_categories_version = language_v1.ClassificationModelOptions.V2Model.ContentCategoriesVersion.V2
            response = client.classify_text(
                request={
                    "document": document,
                    "classification_model_options": {
                        "v2_model": {"content_categories_version": content_categories_version}
                    },
                },
                timeout=language_timeout,
            )

            for category in response.categories:
                categories.append(category.name.replace("/", "-").replace(" ", "-"))
    except Exception as e:
        PRINT("\n-Trinitty:Error:", str(e))
        Log_Error("Classify", e)
        categories = ["nocat"]

    if len(categories) == 0:
        categories = ["nocat"]

    Current_Category = categories
    PRINT("\n-Trinitty:Current_Category:\n", Current_Category)

    return ()


def Trinitty(fname="WakeMe"):

    PRINT("\n-Trinitty:")
    PRINT("\n-Trinitty:fname:", fname)

    if INTERPRETOR:
      PRINT("\n-Trinitty:INTERPRETOR TRUE")
      return Prompt()

    if fname == "WakeMe" and globals().get("PUSH_TO_TALK", False):
        return Push_To_Talk()

    if fname == "WakeMe":

        wake_up()
        awake.put(True)
    else:

        if fname == "Speech_To_Text":
            if Start_Thread_Record() is False:
                return Go_Back_To_Sleep(False)
            if Wait_for("audio"):
                audio = Queue_Get_Optional(audio_datas, timeout=0.2, default=None)
                if audio is None:
                    return Go_Back_To_Sleep()
                (
                    transcripts,
                    transcripts_confidence,
                    words,
                    words_confidence,
                    Err_msg,
                ) = Speech_To_Text(audio)
                txt, fconf = Check_Transcript(
                    transcripts,
                    transcripts_confidence,
                    words,
                    words_confidence,
                    Err_msg,
                )

                if len(txt) > 0:
                    if fconf:
                        cmd = Commandes(txt)
                        if cmd:
                            return Go_Back_To_Sleep()
                        To_Gpt(txt)

                    else:
                        return Bad_Confidence(txt)
                else:
                    return Go_Back_To_Sleep()
            else:
                return Go_Back_To_Sleep()

        elif fname == "Repeat":

            if Start_Thread_Record() is False:
                return Go_Back_To_Sleep(False)
            if Wait_for("audio"):
                audio = Queue_Get_Optional(audio_datas, timeout=0.2, default=None)
                if audio is None:
                    return Go_Back_To_Sleep()
                (
                    transcripts,
                    transcripts_confidence,
                    words,
                    words_confidence,
                    Err_msg,
                ) = Speech_To_Text(audio)
                txt, fconf = Check_Transcript(
                    transcripts,
                    transcripts_confidence,
                    words,
                    words_confidence,
                    Err_msg,
                )
                if len(txt) > 0:
                    Repeat(txt)
                else:
                    return Go_Back_To_Sleep()
            else:
                return Go_Back_To_Sleep()
        else:
            PRINT("\n-Trinitty:TOUCHDOWN\n")
            return Go_Back_To_Sleep()
    return None


def Load_Runtime_Keys():
    global PICO_KEY
    global GOOGLE_KEY
    global GOOGLE_ENGINE
    global GOOGLE_TRANSLATE
    global DLANG_KEY
    global PUSH_TO_TALK

    if INTERPRETOR or PUSH_TO_TALK:
        PICO_KEY = None
        PRINT("\n-Trinitty:INTERPRETOR/PUSH_TO_TALK active, skipping Pico key load.")
    else:
        PICO_KEY = PicoLoadKeys()
        if not PICO_KEY:
            PUSH_TO_TALK = True
            print("\n-Trinitty:Picovoice key unavailable; switching to PUSH_TO_TALK mode.")

    GOOGLE_KEY, GOOGLE_ENGINE, GOOGLE_TRANSLATE = GoogleLoadKeys()
    DLANG_KEY = DetectLanguageLoadKeys()
    if DLANG_KEY:
        detectlanguage.configuration.api_key = DLANG_KEY


def GetConf():
    global DEBUG
    global XCB_ERROR_FIX
    global SAVED_ANSWER
    global GPT4FREE_SERVERS_LIST
    global GPT4FREE_SERVERS_STATUS
    global GPT4FREE_SERVERS_AUTH
    global GPT4FREE_COOKIES_AUTO_SYNC
    global GPT4FREE_COOKIES_SYNC_DIR
    global GPT4FREE_AUTO_REJECT_NOTWORKING
    global INTERPRETOR
    global PUSH_TO_TALK
    global PLAYBACK_INTERRUPT_ENABLED
    global PLAYBACK_INTERRUPT_TIMEOUT
    global COMMAND_CLASSIFIER_ENABLED
    global COMMAND_CLASSIFIER_THRESHOLD
    global COMMAND_CLASSIFIER_MODEL_PATH
    global OPENAI_ENABLED
    global OPENAI_API_KEY
    global OPENAI_API_KEY_FILE
    global OPENAI_MODEL
    global OPENAI_TIMEOUT
    global OPENAI_INSTRUCTIONS
    global SPACY_MODEL
    global GOOGLE_STT_TIMEOUT
    global GOOGLE_LANGUAGE_TIMEOUT
    global HISTORY_CLASSIFICATION_ENABLED
    global GOOGLE_SORT_BY_DATE
    global CHECK_UPDATE
    global CMD_DBG
    global SYNTAX_DBG
    global SEARCH_DBG

    options = [
        "DEBUG",
        "XCB_ERROR_FIX",
        "SAVED_ANSWER",
        "INTERPRETOR",
        "PUSH_TO_TALK",
        "PLAYBACK_INTERRUPT_ENABLED",
        "PLAYBACK_INTERRUPT_TIMEOUT",
        "COMMAND_CLASSIFIER_ENABLED",
        "COMMAND_CLASSIFIER_THRESHOLD",
        "COMMAND_CLASSIFIER_MODEL_PATH",
        "OPENAI_ENABLED",
        "OPENAI_API_KEY_FILE",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_TIMEOUT",
        "OPENAI_INSTRUCTIONS",
        "SPACY_MODEL",
        "GOOGLE_STT_TIMEOUT",
        "GOOGLE_LANGUAGE_TIMEOUT",
        "HISTORY_CLASSIFICATION_ENABLED",
        "GOOGLE_SORT_BY_DATE",
        "GPT4FREE_SERVERS_LIST",
        "GPT4FREE_SERVERS_STATUS",
        "GPT4FREE_SERVERS_AUTH",
        "GPT4FREE_COOKIES_AUTO_SYNC",
        "GPT4FREE_COOKIES_SYNC_DIR",
        "GPT4FREE_AUTO_REJECT_NOTWORKING",
        "CHECK_UPDATE",
        "CMD_DBG",
        "SYNTAX_DBG",
        "SEARCH_DBG",
    ]
    conf = False

    PRINT("\n-Trinitty:GetConf()")

    conf_files = [
        SCRIPT_PATH + "/datas/conf.trinity",
        SCRIPT_PATH + "/datas/conf.local.trinity",
        *User_Data_Path_Candidates("datas", "conf.local.trinity"),
        *User_Data_Path_Candidates("datas", "conf.trinity"),
    ]
    existing_conf_files = [conf_file for conf_file in conf_files if os.path.exists(conf_file)]

    if existing_conf_files:
        f = []
        for conf_file in existing_conf_files:
            with open(conf_file) as config_file:
                f.extend(config_file.readlines())

        for raw_conf_line in f:

            stripped_conf_line = raw_conf_line.strip()
            if not stripped_conf_line or stripped_conf_line.startswith("#"):
               continue

            conf_line = stripped_conf_line

            if "=" not in conf_line:
                continue

            key, conf = Config_Option_Value(conf_line)
            option = key if key in options else ""

            #PRINT("L:", conf_line)
            if not option:
                PRINT("\n-Trinitty:Error skipped line :", conf_line)
                continue
#            else:
#                pass
#                print("Option:%s"%option)
#                print("conf:%s"%conf)
#                input("pause")

            if option == "SAVED_ANSWER":

                try:
                    Configure_Saved_Answer_Path(conf)
                except Exception as e:
                    print("\n-Trinitty:Error:GetConf:SAVED_ANSWER:%s" % str(e))

            elif option == "INTERPRETOR":
                 if conf.lower() == "true":
                       INTERPRETOR = True
                 else:
                       INTERPRETOR = False

            elif option == "PUSH_TO_TALK":
                 PUSH_TO_TALK = Config_Bool(conf, default=False)

            elif option == "PLAYBACK_INTERRUPT_ENABLED":
                 PLAYBACK_INTERRUPT_ENABLED = Config_Bool(conf, default=False)

            elif option == "PLAYBACK_INTERRUPT_TIMEOUT":
                try:
                    PLAYBACK_INTERRUPT_TIMEOUT = float(conf)
                except Exception:
                    PLAYBACK_INTERRUPT_TIMEOUT = 30.0

            elif option == "COMMAND_CLASSIFIER_ENABLED":
                 COMMAND_CLASSIFIER_ENABLED = Config_Bool(conf, default=False)

            elif option == "COMMAND_CLASSIFIER_THRESHOLD":
                try:
                    COMMAND_CLASSIFIER_THRESHOLD = float(conf)
                except Exception:
                    COMMAND_CLASSIFIER_THRESHOLD = 0.65

            elif option == "COMMAND_CLASSIFIER_MODEL_PATH":
                COMMAND_CLASSIFIER_MODEL_PATH = conf

            elif option == "OPENAI_ENABLED":
                OPENAI_ENABLED = Openai_Config_Bool(conf, default=True)

            elif option == "OPENAI_API_KEY_FILE":
                OPENAI_API_KEY_FILE = conf

            elif option == "OPENAI_API_KEY":
                OPENAI_API_KEY = conf

            elif option == "OPENAI_MODEL":
                if conf:
                    OPENAI_MODEL = conf

            elif option == "OPENAI_TIMEOUT":
                try:
                    OPENAI_TIMEOUT = float(conf)
                except Exception:
                    print("-Trinitty:Error OPENAI_TIMEOUT has to be a number.")

            elif option == "OPENAI_INSTRUCTIONS":
                OPENAI_INSTRUCTIONS = conf

            elif option == "SPACY_MODEL":
                if conf:
                    SPACY_MODEL = conf

            elif option == "GOOGLE_STT_TIMEOUT":
                GOOGLE_STT_TIMEOUT = Config_Positive_Float(conf, 20.0)

            elif option == "GOOGLE_LANGUAGE_TIMEOUT":
                GOOGLE_LANGUAGE_TIMEOUT = Config_Positive_Float(conf, 8.0)

            elif option == "HISTORY_CLASSIFICATION_ENABLED":
                HISTORY_CLASSIFICATION_ENABLED = Config_Bool(conf, default=True)

            elif option == "GOOGLE_SORT_BY_DATE":
                GOOGLE_SORT_BY_DATE = Config_Bool(conf, default=False)

            elif option == "GPT4FREE_SERVERS_LIST":
                    GPT4FREE_SERVERS_LIST = Parse_Gpt4free_Server_List(conf)

            elif option == "GPT4FREE_SERVERS_STATUS" and not GPT4FREE_SERVERS_LIST:
                if conf.lower() == "all":
                    GPT4FREE_SERVERS_STATUS = "All"
                elif conf.lower() == "active":
                    GPT4FREE_SERVERS_STATUS = "Active"
                elif conf.lower() == "unknown":
                    GPT4FREE_SERVERS_STATUS = "Unknown"
                elif conf.lower() == "none":
                    GPT4FREE_SERVERS_STATUS = None
                else:
                    print("-Trinitty:Error GPT4FREE_SERVERS_STATUS has to be All,Active,Unknown or None.")

            elif option == "GPT4FREE_SERVERS_AUTH":
                if conf.lower() == "true":
                    GPT4FREE_SERVERS_AUTH = True
                elif conf.lower() == "false":
                    GPT4FREE_SERVERS_AUTH = False
                elif conf.lower() == "all":
                    GPT4FREE_SERVERS_AUTH = "All"
                else:
                    print("-Trinitty:Error GPT4FREE_SERVERS_STATUS has to be All,True or False.")

            elif option == "GPT4FREE_COOKIES_AUTO_SYNC":
                GPT4FREE_COOKIES_AUTO_SYNC = Config_Bool(conf, default=True)

            elif option == "GPT4FREE_COOKIES_SYNC_DIR":
                GPT4FREE_COOKIES_SYNC_DIR = conf

            elif option == "GPT4FREE_AUTO_REJECT_NOTWORKING":
                GPT4FREE_AUTO_REJECT_NOTWORKING = Config_Bool(conf, default=True)


            elif option == "CHECK_UPDATE":
                if conf.lower() == "true":
                    CHECK_UPDATE = True
                elif conf.lower() == "false":
                    CHECK_UPDATE = False
                else:
                    print("-Trinitty:Error CHECK_UPDATE has to be either True or False.")

            elif option == "SYNTAX_DBG":
                if conf.lower() == "true":
                    SYNTAX_DBG = True
                elif conf.lower() == "false":
                    SYNTAX_DBG = False
                else:
                    print("-Trinitty:Error SYNTAX_DBG has to be either True or False.")


            elif option == "CMD_DBG":
                if conf.lower() == "true":
                    CMD_DBG = True
                elif conf.lower() == "false":
                    CMD_DBG = False
                else:
                    print("-Trinitty:Error CMD_DBG has to be either True or False.")

            elif option == "SEARCH_DBG":
                if conf.lower() == "true":
                    SEARCH_DBG = True
                elif conf.lower() == "false":
                    SEARCH_DBG = False
                else:
                    print("-Trinitty:Error SEARCH_DBG has to be either True or False.")


            elif option == "DEBUG":
                if conf.lower() == "true":
                    DEBUG = True
                elif conf.lower() == "false":
                    DEBUG = False
                else:
                    print("-Trinitty:Error DEBUG has to be either True or False.")

            elif option == "XCB_ERROR_FIX":
                if conf.lower() == "true":
                    XCB_ERROR_FIX = True
                elif conf.lower() == "false":
                    XCB_ERROR_FIX = False
                else:
                    print("-Trinitty:Error XCB_ERROR_FIX has to be either True or False.")

    else:
        os.makedirs(SCRIPT_PATH + "/datas", exist_ok=True)
        with open(SCRIPT_PATH + "/datas/conf.trinity", "w") as f:
            data = """SAVED_ANSWER = default
OPENAI_ENABLED = True #True or False - use OpenAI before gpt4free
OPENAI_MODEL = gpt-5.5
OPENAI_API_KEY_FILE = keys/openai.key
OPENAI_TIMEOUT = 30
OPENAI_INSTRUCTIONS = Reponds en francais de facon concise et naturelle.
SPACY_MODEL = fr_core_news_md
GOOGLE_STT_TIMEOUT = 20
GOOGLE_LANGUAGE_TIMEOUT = 8
HISTORY_CLASSIFICATION_ENABLED = True
GOOGLE_SORT_BY_DATE = False
GPT4FREE_SERVERS_LIST = None #[g4f.Provider.PROVIDERNAME1,g4f.Provider.PROVIDERNAME2] or None
GPT4FREE_SERVERS_STATUS = Active #Active or Unknown or All or None
GPT4FREE_SERVERS_AUTH = False #True or False or All
GPT4FREE_COOKIES_AUTO_SYNC = True # True or False - copy har/json captures before loading cookies
GPT4FREE_COOKIES_SYNC_DIR = tools/har_and_cookies
GPT4FREE_AUTO_REJECT_NOTWORKING = True
INTERPRETOR = True # True or False
PUSH_TO_TALK = False # True or False - press Enter instead of using wake word
PLAYBACK_INTERRUPT_ENABLED = False # True records during playback to listen for stop commands
PLAYBACK_INTERRUPT_TIMEOUT = 30 # seconds to keep listening during one playback
COMMAND_CLASSIFIER_ENABLED = False # True or False - use optional TensorFlow command classifier
COMMAND_CLASSIFIER_THRESHOLD = 0.65 # minimum classifier score to run command matching
COMMAND_CLASSIFIER_MODEL_PATH = datas/command_classifier.keras
CHECK_UPDATE = False #Check update for Trinitty or g4f
DEBUG = False #Print debug stuffs
CMD_DBG = False #Print commands results only for testing purpose
SYNTAX_DBG = False #Print output of Special syntax found in database at launch
SEARCH_DBG = False #Test output from Isolate_Search only .
XCB_ERROR_FIX = False #Fix Xcb error from popping due to DISPLAY env variable."""
            f.write(data)

        DEBUG = False
        CMD_DBG = False
        SYNTAX_DBG = False
        CHECK_UPDATE = False
        SEARCH_DBG = False
        INTERPRETOR = False
        PUSH_TO_TALK = False
        OPENAI_ENABLED = True
        OPENAI_API_KEY = ""
        OPENAI_API_KEY_FILE = "keys/openai.key"
        OPENAI_MODEL = "gpt-5.5"
        OPENAI_TIMEOUT = 30
        OPENAI_INSTRUCTIONS = "Reponds en francais de facon concise et naturelle."
        SPACY_MODEL = "fr_core_news_md"
        GOOGLE_STT_TIMEOUT = 20.0
        GOOGLE_LANGUAGE_TIMEOUT = 8.0
        HISTORY_CLASSIFICATION_ENABLED = True
        GOOGLE_SORT_BY_DATE = False
        GPT4FREE_SERVERS_LIST = None
        SEARCH_DBG = False
        SAVED_ANSWER = SCRIPT_PATH + "/local_sounds/saved_answer/"
        GPT4FREE_SERVERS_STATUS = "Active"
        GPT4FREE_SERVERS_AUTH = False
        GPT4FREE_AUTO_REJECT_NOTWORKING = True
        XCB_ERROR_FIX = False


def Xcb_Fix(mode):
    global DISPLAY

    if mode == "unset":
        DISPLAY = os.getenv("DISPLAY")
        try:
            del os.environ["DISPLAY"]
        except KeyError:
            DISPLAY = ""
    if mode == "set":
        if DISPLAY:
            try:
                os.environ["DISPLAY"] = DISPLAY
            except Exception as e:
                Log_Error("Xcb_Fix:set", e)


def Version_Key(version):
    parts = re.findall(r"\d+|[A-Za-z]+", str(version or ""))
    key = []
    for part in parts:
        if part.isdigit():
            key.append((1, int(part)))
        else:
            key.append((0, part.lower()))
    return key


def Version_Newer(latest_version, current_version):
    latest_key = Version_Key(latest_version)
    current_key = Version_Key(current_version)
    if not latest_key or not current_key:
        return False
    return latest_key > current_key


def Project_Version_From_Pyproject():
    pyproject_path = os.path.join(Default_Script_Path(), "pyproject.toml")
    try:
        with open(pyproject_path) as f:
            text = f.read()
    except OSError:
        return ""
    match = PYPROJECT_VERSION_RE.search(text)
    return match.group(1).strip() if match else ""


def Installed_Trinitty_Version():
    try:
        return importlib_metadata.version(PYPI_PACKAGE_NAME)
    except importlib_metadata.PackageNotFoundError:
        return Project_Version_From_Pyproject()


def Pypi_Latest_Version(package_name=PYPI_PACKAGE_NAME, timeout=5):
    url = "https://pypi.org/pypi/%s/json" % package_name
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - fixed PyPI JSON endpoint for update checks.
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("info", {}).get("version", "")).strip()


def Check_Update():
    PRINT("\n-Trinitty:Dans Check_Update().")

    to_update = []
    Gpt4free_Is_Up = False
    Gpt4free_current_version = ""
    Gpt4free_latest_version = ""
    if Ensure_Gpt4free_Runtime_Available():
        try:
            if hasattr(g4f, "version"):
                if hasattr(g4f.version, "utils"):
                    if hasattr(g4f.version.utils, "current_version"):
                        Gpt4free_current_version = g4f.version.utils.current_version
                    if hasattr(g4f.version.utils, "latest_version"):
                        Gpt4free_latest_version = g4f.version.utils.latest_version
            if Gpt4free_current_version == Gpt4free_latest_version:
                Gpt4free_Is_Up = True

        except Exception as e:
            print("\n-Trinitty:Error:Check_Update n'a pas pu déterminer la version de gpt4free:%s" % str(e))
            Gpt4free_Is_Up = True
    else:
        Gpt4free_Is_Up = True

    Trinitty_Is_Up = False
    Trinitty_current_version = ""
    Trinitty_latest_version = ""
    try:
        Trinitty_current_version = Installed_Trinitty_Version()
        Trinitty_latest_version = Pypi_Latest_Version()
        if Trinitty_current_version and Trinitty_latest_version:
            Trinitty_Is_Up = not Version_Newer(Trinitty_latest_version, Trinitty_current_version)
        else:
            Trinitty_Is_Up = True

    except Exception as e:
        print("\n-Trinitty:Error:Check_Update n'a pas pu déterminer la version PyPI de Trinitty:%s" % str(e))
        Trinitty_Is_Up = True

    PRINT("\n-Trinitty:Vérification de mise à jour pour Gpt4free:\n")
    if not Gpt4free_Is_Up:
        to_update.append("gpt4free")
        try:
            if hasattr(g4f.version.utils, "check_version"):
                g4f.version.utils.check_version()
                print()
        except Exception as e:
            Log_Error("Check_Update:g4f.version.utils.check_version", e)
    else:
        print("\n-Trinitty:La version de gpt4free est à jour .")

    PRINT("\n-Trinitty:Vérification de mise à jour pour Trinitty:")
    if Trinitty_current_version or Trinitty_latest_version:
        PRINT(
            "\n-Trinitty:Version installée:%s / Version PyPI:%s\n"
            % (Trinitty_current_version or "inconnue", Trinitty_latest_version or "inconnue")
        )
    if not Trinitty_Is_Up:
        to_update.append("Trinitty")
        PRINT(
            "\n-Trinitty:Version PyPI plus récente détectée:%s>%s\n"
            % (Trinitty_latest_version, Trinitty_current_version)
        )
    else:
        print("\n-Trinitty:La version de Trinitty est à jour .")

    if len(to_update) > 0:
        print(
            "\n-Trinitty:Warning:Une nouvelle version pour %s a été publiée.\n-Trinitty:Mettez à jour votre version quand possible.\n-Trinitty:CHECK_UPDATE reste un avertissement non bloquant."
            % " et ".join(to_update)
        )
        Log_Error("Check_Update", "update available for %s" % " et ".join(to_update))
        return False
    return True


def main():
    if Handle_Utility_Args():
        return
    runpy.run_path(os.path.abspath(__file__), run_name="__main__")


if __name__ == "__main__":
    if Handle_Utility_Args():
        sys.exit(0)

    SCRIPT_PATH = Default_Script_Path()
    SCRIPT_PATH = SCRIPT_PATH.removesuffix(".")

    LAST_SHA = "1240adc232e94171b840a519a79b437cf5524321"

    DISPLAY = ""
    Providers_To_Use = []
    Runtime_Errors = []
    LAST_DIALOG = ()
    REMEMBER_LAST_15M = False
    INTERPRETOR = False
    PUSH_TO_TALK = False
    PLAYBACK_INTERRUPT_ENABLED = False
    PLAYBACK_INTERRUPT_TIMEOUT = 30.0
    COMMAND_CLASSIFIER_ENABLED = False
    COMMAND_CLASSIFIER_THRESHOLD = 0.65
    COMMAND_CLASSIFIER_MODEL_PATH = "datas/command_classifier.keras"
    COMMAND_CLASSIFIER_MODEL = None
    Providers_To_Use = None
    GPT4FREE_SERVERS_LIST = None
    GPT4FREE_SERVERS_STATUS = "Active"
    GPT4FREE_SERVERS_AUTH = False
    GPT4FREE_COOKIES_AUTO_SYNC = True
    GPT4FREE_COOKIES_SYNC_DIR = "tools/har_and_cookies"
    GPT4FREE_COOKIES_LOADED = False
    GPT4FREE_RUNTIME_AVAILABLE = None
    GPT4FREE_AUTO_REJECT_NOTWORKING = True
    OPENAI_ENABLED = True
    OPENAI_API_KEY = ""
    OPENAI_API_KEY_FILE = "keys/openai.key"
    OPENAI_MODEL = "gpt-5.5"
    OPENAI_TIMEOUT = 30
    OPENAI_INSTRUCTIONS = "Reponds en francais de facon concise et naturelle."
    SPACY_MODEL = "fr_core_news_md"
    GOOGLE_STT_TIMEOUT = 20.0
    GOOGLE_LANGUAGE_TIMEOUT = 8.0
    HISTORY_CLASSIFICATION_ENABLED = True
    GOOGLE_SORT_BY_DATE = False
    CHECK_UPDATE = False
    DEBUG = False
    CMD_DBG = False
    SYNTAX_DBG = False
    SEARCH_DBG = False
    XCB_ERROR_FIX = False
    SAVED_ANSWER = SCRIPT_PATH + "/local_sounds/saved_answer/"

    user_data_root = Initialize_User_Data()
    if Auto_Dependency_Installer_Enabled():
        Auto_Run_Dependency_Installer(user_data_root)
    Configure_Default_Google_Credentials()
    GetConf()
    if DEBUG:
        print("-Trinitty:Journal debug: %s" % Debug_Log_File())


    if GPT4FREE_SERVERS_LIST:
       Providers_To_Use = GPT4FREE_SERVERS_LIST


    FRAME_DURATION = 480
    FRAME_RATE = 16000

    Loaded_History_List = []
    Current_Category = []
    Blacklisted = []

    Load_Runtime_Keys()
    record_on = Queue()
    chunks = Queue()
    last_sentence = Queue()
    No_Input = Queue()
    score_sentiment = Queue()
    audio_datas = Queue()
    wake_me_up = Queue()
    cancel_operation = Queue()
    awake = Queue()
    wake_me_up.put(True)
    Current_Provider_Id = 0
    Repeat_Last_One = ""
    Loaded_Trinitty_Name_Requests = []
    Loaded_Trinitty_Mean_Requests = []
    Loaded_Trinitty_Dev_Requests = []
    Loaded_Trinitty_Script_Requests = []
    Loaded_Trinitty_Help_Requests = []
    Loaded_Prompt_Requests = []
    Loaded_Rnd_Requests = []
    Loaded_Read_Results = []
    Loaded_Repeat_Requests = []
    Loaded_Show_History_Requests = []
    Loaded_Search_History_Requests = []
    Loaded_Delete_Last_History_Requests = []
    Loaded_Read_Link_Requests = []
    Loaded_Play_Audio_File_Requests = []
    Loaded_Search_Web_Requests = []
    Loaded_Wait_Words_Requests = []
    Loaded_Quit_Words_Requests = []
    Loaded_Sort_Results_Requests = []
    Loaded_Add_Triggers_Requests = []
    Loaded_Actions_Words_Requests = []
    Loaded_Mix_Actions_Functions = []
    Loaded_Alternatives_Triggers = []
    Loaded_Verbs_Words_List = []
    Loaded_Synonyms_Words_List = []
    Loaded_Mix_Functions_verbs = {}

    CMDFILE = SCRIPT_PATH + "/datas/cmd.trinity"
    ALTFILE = SCRIPT_PATH + "/datas/alt_cmd.trinity"
    TRIFILE = SCRIPT_PATH + "/datas/alt_trigger.trinity"
    ACTFILE = SCRIPT_PATH + "/datas/action.trinity"
    PREFILE = SCRIPT_PATH + "/datas/prefix.trinity"
    SYNFILE = SCRIPT_PATH + "/datas/synonym.trinity"

    if not Load_Csv():
        sys.exit(1)

    if XCB_ERROR_FIX:
        Xcb_Fix("unset")

    Play_Audio_File(SCRIPT_PATH + "/local_sounds/boot/psx.wav")
    signal.signal(signal.SIGINT, signal_ctrlc)
    PRINT("\n-Trinitty:Python Version:%s"% sys.version)
    PRINT("-Trinitty:CHECK_UPDATE:%s" % CHECK_UPDATE)
    PRINT("-Trinitty:DEBUG:%s" % DEBUG)
    PRINT("-Trinitty:CMD_DBG:%s" % CMD_DBG)
    PRINT("-Trinitty:SYNTAX_DBG:%s" % SYNTAX_DBG)
    PRINT("-Trinitty:SEARCH_DBG:%s" % SEARCH_DBG)
    PRINT("-Trinitty:INTERPRETOR:%s" % INTERPRETOR)
    PRINT("-Trinitty:PUSH_TO_TALK:%s" % PUSH_TO_TALK)
    PRINT("-Trinitty:OPENAI_ENABLED:%s" % OPENAI_ENABLED)
    PRINT("-Trinitty:OPENAI_MODEL:%s" % OPENAI_MODEL)
    PRINT("-Trinitty:OPENAI_API_KEY_SOURCE:%s" % Openai_Key_Source_For_Log())
    PRINT("-Trinitty:OPENAI_API_KEY_FILE:%s" % OPENAI_API_KEY_FILE)
    PRINT("-Trinitty:OPENAI_TIMEOUT:%s" % OPENAI_TIMEOUT)
    PRINT("-Trinitty:SPACY_MODEL:%s" % SPACY_MODEL)
    PRINT("-Trinitty:GOOGLE_STT_TIMEOUT:%s" % GOOGLE_STT_TIMEOUT)
    PRINT("-Trinitty:GOOGLE_LANGUAGE_TIMEOUT:%s" % GOOGLE_LANGUAGE_TIMEOUT)
    PRINT("-Trinitty:HISTORY_CLASSIFICATION_ENABLED:%s" % HISTORY_CLASSIFICATION_ENABLED)
    PRINT("-Trinitty:GOOGLE_SORT_BY_DATE:%s" % GOOGLE_SORT_BY_DATE)
    PRINT("-Trinitty:GPT4FREE_SERVERS_LIST:%s" % GPT4FREE_SERVERS_LIST)
    PRINT("-Trinitty:GPT4FREE_SERVERS_STATUS:%s" % GPT4FREE_SERVERS_STATUS)
    PRINT("-Trinitty:GPT4FREE_SERVERS_AUTH:%s" % GPT4FREE_SERVERS_AUTH)
    PRINT("-Trinitty:GPT4FREE_AUTO_REJECT_NOTWORKING:%s" % GPT4FREE_AUTO_REJECT_NOTWORKING)
    PRINT("-Trinitty:XCB_ERROR_FIX:%s" % XCB_ERROR_FIX)
    PRINT("-Trinitty:SAVED_ANSWER:%s" % SAVED_ANSWER)
    PRINT("-Trinitty:History categories loaded:%s" % len(Loaded_History_List))


    if Providers_To_Use:
        PRINT("-Trinitty:Free Gpt servers to use:")
        Providers_To_Use = Filter_Gpt4free_Providers_For_Runtime(Providers_To_Use)

    if CHECK_UPDATE:
        Check_Update()

    if SEARCH_DBG:
       Dbg_Search()

    if CMD_DBG:
        Dbg_Input()
    else:
#####
        Trinitty()
#####
