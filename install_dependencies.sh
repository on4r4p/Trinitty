#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
DEFAULT_VENV_DIR=".venv"
FALLBACK_VENV_DIR=".venv-trinitty"
VENV_DIR="${VENV_DIR:-$DEFAULT_VENV_DIR}"

USE_VENV=1
INSTALL_SYSTEM=0
INSTALL_NLTK_DATA=1
INSTALL_SPACY_MODEL=1
INSTALL_COMMAND_CLASSIFIER=0
INSTALL_DEV_TOOLS=1
VERIFY_IMPORTS=1
VENV_DIR_EXPLICIT=0

usage() {
  cat <<'EOF'
Usage: ./install_dependencies.sh [options]

Options:
  --venv                 Create/use .venv before installing Python packages. Default.
  --no-venv              Install into the current Python environment.
  --venv-dir DIR         Use a custom virtualenv directory. Default: .venv
                         If default .venv is not writable, .venv-trinitty is used.
  --system               Install Debian/Ubuntu system packages with apt-get.
  --no-nltk-data         Skip NLTK data downloads.
  --no-spacy-model       Skip the fr_core_news_md spaCy model download.
  --with-command-classifier
                         Install optional TensorFlow command-classifier dependencies.
  --no-dev-tools         Skip packaging/lint tools: build, twine, ruff.
  --no-verify            Skip import and command checks at the end.
  -h, --help             Show this help.

Examples:
  ./install_dependencies.sh
  ./install_dependencies.sh --system --venv
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --venv)
      USE_VENV=1
      ;;
    --no-venv)
      USE_VENV=0
      ;;
    --venv-dir)
      shift
      VENV_DIR="${1:-}"
      VENV_DIR_EXPLICIT=1
      if [[ -z "$VENV_DIR" ]]; then
        echo "Missing value for --venv-dir" >&2
        exit 2
      fi
      ;;
    --system)
      INSTALL_SYSTEM=1
      ;;
    --no-nltk-data)
      INSTALL_NLTK_DATA=0
      ;;
    --no-spacy-model)
      INSTALL_SPACY_MODEL=0
      ;;
    --with-command-classifier)
      INSTALL_COMMAND_CLASSIFIER=1
      ;;
    --no-dev-tools)
      INSTALL_DEV_TOOLS=0
      ;;
    --no-verify)
      VERIFY_IMPORTS=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
  shift
done

install_system_dependencies() {
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "apt-get was not found; skipping system package installation." >&2
    return
  fi

  local sudo_cmd=()
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    if ! command -v sudo >/dev/null 2>&1; then
      echo "sudo is required for --system when not running as root." >&2
      exit 1
    fi
    sudo_cmd=(sudo)
  fi

  "${sudo_cmd[@]}" apt-get update
  "${sudo_cmd[@]}" apt-get install -y \
    alsa-utils \
    build-essential \
    flac \
    libasound2-dev \
    libsox-fmt-all \
    libttspico-utils \
    portaudio19-dev \
    python3-dev \
    python3-pyaudio \
    python3-venv \
    sox
}

platform_machine() {
  "$PYTHON_BIN" - <<'PY'
import platform

print(platform.machine().lower())
PY
}

is_linux_arm() {
  case "$(platform_machine)" in
    aarch64|armv6l|armv7l)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

check_python_build_dependencies() {
  local missing=()

  if ! command -v gcc >/dev/null 2>&1; then
    missing+=("build-essential")
  fi

  if ! "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import sysconfig
from pathlib import Path

include = Path(sysconfig.get_paths()["include"])
raise SystemExit(0 if (include / "Python.h").exists() else 1)
PY
  then
    missing+=("python3-dev")
  fi

  if [[ ! -f /usr/include/portaudio.h ]]; then
    missing+=("portaudio19-dev")
  fi

  if is_linux_arm && ! /usr/bin/python3 - <<'PY' >/dev/null 2>&1
import pyaudio
PY
  then
    missing+=("python3-pyaudio")
  fi

  if ! command -v sox >/dev/null 2>&1; then
    missing+=("sox")
  fi

  if ! command -v aplay >/dev/null 2>&1; then
    missing+=("alsa-utils")
  fi

  if [[ "${#missing[@]}" -gt 0 ]]; then
    cat >&2 <<EOF
Missing system dependencies for Trinitty: ${missing[*]}

Install them automatically with:
  ./install_dependencies.sh --system

Or manually on Debian/Ubuntu:
  sudo apt-get install -y ${missing[*]}
EOF
    exit 1
  fi

  if ! command -v pico2wave >/dev/null 2>&1; then
    cat >&2 <<'EOF'
Optional dependency missing: pico2wave

Trinitty can run without pico2wave, but this fallback TTS command is available on Debian/Ubuntu with:
  sudo apt-get install -y libttspico-utils
EOF
  fi
}

venv_is_writable() {
  local venv_path="$ROOT_DIR/$VENV_DIR"
  local test_file="$venv_path/.trinitty-write-test"

  if [[ ! -e "$venv_path" ]]; then
    return 0
  fi

  if ! touch "$test_file" >/dev/null 2>&1; then
    return 1
  fi

  rm -f "$test_file"
}

explain_unwritable_venv() {
  local venv_path="$ROOT_DIR/$VENV_DIR"

  cat >&2 <<EOF
The virtualenv directory is not writable: $venv_path

It may have been created with sudo or another user. Fix ownership with:
  sudo chown -R $(id -u):$(id -g) "$venv_path"

Or choose a different virtualenv:
  ./install_dependencies.sh --venv-dir .venv-trinitty
EOF
}

select_venv_dir() {
  if venv_is_writable; then
    return
  fi

  if [[ "$VENV_DIR" == "$DEFAULT_VENV_DIR" && "$VENV_DIR_EXPLICIT" -eq 0 ]]; then
    echo "Default virtualenv is not writable: $ROOT_DIR/$VENV_DIR" >&2
    echo "Using fallback virtualenv: $ROOT_DIR/$FALLBACK_VENV_DIR" >&2
    VENV_DIR="$FALLBACK_VENV_DIR"

    if venv_is_writable; then
      return
    fi
  fi

  explain_unwritable_venv
  exit 1
}

link_system_pyaudio_on_arm() {
  if ! is_linux_arm; then
    return
  fi

  if "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import pyaudio
PY
  then
    return
  fi

  local target_site
  target_site="$("$PYTHON_BIN" - <<'PY'
import sysconfig

print(sysconfig.get_paths()["purelib"])
PY
)"

  /usr/bin/python3 - <<PY
import glob
import pathlib
import pyaudio

target_site = pathlib.Path("$target_site")
source_pkg = pathlib.Path(pyaudio.__file__).resolve().parent

links = [source_pkg]
links.extend(pathlib.Path(path) for path in glob.glob(str(source_pkg.parent / "_portaudio*.so")))

for source in links:
    target = target_site / source.name
    if target.exists() or target.is_symlink():
        target.unlink()
    target.symlink_to(source)
    print(f"Linked system PyAudio: {target} -> {source}")
PY
}

if [[ "$INSTALL_SYSTEM" -eq 1 ]]; then
  install_system_dependencies
fi

check_python_build_dependencies

if [[ "$USE_VENV" -eq 1 ]]; then
  select_venv_dir
  "$PYTHON_BIN" -m venv "$ROOT_DIR/$VENV_DIR"
  # shellcheck source=/dev/null
  source "$ROOT_DIR/$VENV_DIR/bin/activate"
  export PYTHONNOUSERSITE=1
  PYTHON_BIN="$ROOT_DIR/$VENV_DIR/bin/python"
  link_system_pyaudio_on_arm
fi

"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install -r "$ROOT_DIR/requirements.txt"

if [[ "$INSTALL_DEV_TOOLS" -eq 1 ]]; then
  "$PYTHON_BIN" -m pip install "build>=1.2" "twine>=5.1" "ruff>=0.5"
fi

if [[ "$INSTALL_COMMAND_CLASSIFIER" -eq 1 ]]; then
  "$PYTHON_BIN" -m pip install "$ROOT_DIR[command-classifier]"
fi

if [[ "$INSTALL_NLTK_DATA" -eq 1 ]]; then
  "$PYTHON_BIN" - <<'PY'
import nltk

packages = [
    "stopwords",
    "wordnet",
    "omw-1.4",
    "punkt",
    "punkt_tab",
    "averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng",
]

for package in packages:
    nltk.download(package)
PY
fi

if [[ "$INSTALL_SPACY_MODEL" -eq 1 ]]; then
  "$PYTHON_BIN" -m spacy download fr_core_news_md
fi

if [[ "$VERIFY_IMPORTS" -eq 1 ]]; then
  TRINITTY_INSTALL_DEV_TOOLS="$INSTALL_DEV_TOOLS" "$PYTHON_BIN" - <<'PY'
import importlib.util
import os
import shutil
import sys

modules = [
    "g4f",
    "openai",
    "pyaudio",
    "pvporcupine",
    "webrtcvad",
    "sox",
    "spacy",
    "detectlanguage",
    "google.cloud.texttospeech",
    "deep_translator",
    "nltk",
    "urlextract",
    "bs4",
    "github",
    "google.cloud.speech_v1p1beta1",
    "google.cloud.language_v1",
    "google.cloud.translate_v2",
    "unidecode",
    "googlesearch",
    "wikipedia",
]

if os.getenv("TRINITTY_INSTALL_DEV_TOOLS") == "1":
    modules.extend(["build", "twine", "ruff"])

missing = []
for module in modules:
    try:
        ok = importlib.util.find_spec(module) is not None
    except Exception as exc:
        ok = False
        print(f"{module}: MISSING ({type(exc).__name__}: {exc})")
    else:
        print(f"{module}: {'OK' if ok else 'MISSING'}")
    if not ok:
        missing.append(module)

for command in ["aplay", "sox"]:
    if shutil.which(command):
        print(f"{command}: OK")
    else:
        print(f"{command}: MISSING")
        missing.append(command)

if shutil.which("pico2wave"):
    print("pico2wave: OK")
else:
    print("pico2wave: MISSING (optional fallback)")

try:
    import spacy
    spacy.load("fr_core_news_md")
except Exception as exc:
    print(f"fr_core_news_md: MISSING ({type(exc).__name__}: {exc})")
    missing.append("fr_core_news_md")
else:
    print("fr_core_news_md: OK")

if missing:
    print("\nMissing dependencies:", ", ".join(missing), file=sys.stderr)
    sys.exit(1)
PY

  if [[ "$INSTALL_COMMAND_CLASSIFIER" -eq 1 ]]; then
    "$PYTHON_BIN" - <<'PY'
import tensorflow

print("Optional command classifier dependency OK: tensorflow")
PY
  fi
fi

echo "Dependency installation finished."
