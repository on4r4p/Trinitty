# Trinitty

Trinitty est un assistant vocal personnel pour Linux. Il utilise OpenAI en priorité pour répondre aux questions, puis bascule sur `gpt4free` si aucune clé OpenAI n'est configurée ou si l'appel OpenAI échoue.

Le projet combine reconnaissance vocale, synthèse vocale, commandes locales, historique de conversation, recherche web et fournisseurs LLM de secours.

## Fonctionnalités

- Assistant vocal avec mot-clé Porcupine ou mode push-to-talk si la clé Picovoice manque.
- Réponses LLM via l'API OpenAI avec clé dans `keys/openai.key` ou variable `OPENAI_API_KEY`.
- Fallback `gpt4free` avec filtrage automatique des providers utilisables pour une conversation texte.
- Synthèse vocale avec Google Cloud Text-to-Speech, puis fallback local optionnel `pico2wave`.
- Reconnaissance vocale avec Google Cloud Speech.
- Historique des questions/réponses par catégories, avec relecture audio des réponses connues.
- Commandes vocales locales: répéter la dernière réponse, afficher ou chercher dans l'historique, lire un fichier audio, lire un lien, attendre, quitter.
- Recherche Google/Wikipedia et lecture de liens web selon les commandes disponibles dans les fichiers `datas/*.trinity`.
- Déclencheurs et synonymes configurables via les fichiers CSV du dossier `datas/`.
- Sons locaux packagés dans `local_sounds/` pour les retours audio, erreurs, dates, providers, commandes et prompts.

## Installation depuis PyPI

```bash
pip install trinitty
```

Sur Debian/Ubuntu, Trinitty a aussi besoin de dépendances système pour l'audio, PyAudio, sox et les fallbacks locaux:

```bash
sudo apt-get install -y alsa-utils build-essential flac libasound2-dev libsox-fmt-all libttspico-utils portaudio19-dev python3-dev python3-venv sox
```

Lancer ensuite:

```bash
trinitty
```

Pour une installation dans un virtualenv comme `~/venvs/trinitty`, il est possible d'installer un lanceur utilisateur une seule fois:

```bash
~/venvs/trinitty/bin/trinitty --install-launcher
```

Le lanceur est créé dans `~/.local/bin/trinitty`. Il active automatiquement l'environnement propre nécessaire (`PYTHONNOUSERSITE=1`, `PYTHONPATH` vidé), ce qui permet ensuite de lancer simplement:

```bash
trinitty
```

### Installation conseillée sur Raspberry Pi

Sur Raspberry Pi, il est préférable d'utiliser un virtualenv dédié pour éviter les conflits avec les paquets Python installés globalement ou dans `~/.local`.

```bash
sudo apt-get install -y python3-venv python3-pyaudio alsa-utils sox

rm -rf ~/venvs/trinitty
python3 -m venv --system-site-packages ~/venvs/trinitty

~/venvs/trinitty/bin/python -m pip install -U pip setuptools wheel
PYTHONNOUSERSITE=1 ~/venvs/trinitty/bin/python -m pip install --no-cache-dir -U trinitty

PYTHONNOUSERSITE=1 ~/venvs/trinitty/bin/trinitty --install-launcher
```

Après cette installation, l'utilisation normale reste:

```bash
trinitty
```

Le lanceur `~/.local/bin/trinitty` force automatiquement l'environnement propre nécessaire. Il utilise le Python du virtualenv, active `PYTHONNOUSERSITE=1` et vide `PYTHONPATH`.

Le virtualenv Raspberry doit être créé avec `--system-site-packages` pour permettre à Trinitty d'utiliser `python3-pyaudio`, fourni par Debian/Raspberry Pi OS. Cela évite de compiler PyAudio sur la machine.

## Aide et commandes

L'aide générale est disponible sans lancer l'assistant:

```bash
trinitty -h
trinitty --help
trinitty --list-commands
trinitty --explain-command "affiche l'historique"
trinitty doctor
```

Dans l'assistant, les commandes vocales comme `affiche l'aide`, `affiche les commandes` ou `quelles sont les fonctions` affichent cette aide et jouent l'aide audio.

Après une recherche web, Wikipedia ou historique, les résultats restent pilotables par la voix: `lis le résultat numéro 3`, `ouvre le résultat numéro 3`, `lis les trois premiers`, `choisis au hasard`, `attends` ou `quitte`.

`trinitty doctor` vérifie l'état de l'installation sans modification. `trinitty doctor --fix` prépare les fichiers utilisateur puis lance l'installateur local si une réparation est possible.

## Installation depuis le dépôt

Depuis un checkout local, l'installateur crée ou réutilise un virtualenv, installe les dépendances Python, télécharge les données NLTK, installe le modèle spaCy français et peut installer les paquets système avec `--system`.

```bash
./install_dependencies.sh --system --venv
```

Si `.venv` n'est pas inscriptible, le script utilise automatiquement `.venv-trinitty`. L'installateur crée aussi un lanceur `~/.local/bin/trinitty`, afin de lancer Trinitty sans activer le virtualenv à la main.

Options utiles:

```bash
./install_dependencies.sh --no-spacy-model
./install_dependencies.sh --no-nltk-data
./install_dependencies.sh --no-dev-tools
./install_dependencies.sh --no-launcher
./install_dependencies.sh --venv-dir .venv-trinitty
```

## Configuration OpenAI

Le plus simple est de créer un fichier contenant uniquement la clé API:

```bash
mkdir -p keys
printf '%s\n' 'sk-...' > keys/openai.key
```

Ne pas mettre de guillemets autour de la clé. Les lignes vides et les commentaires commençant par `#` sont ignorés.

Pour une installation PyPI, Trinitty vérifie aussi:

```bash
~/.local/share/Trinitty/keys/openai.key
```

Il est également possible d'utiliser une variable d'environnement:

```bash
export OPENAI_API_KEY='sk-...'
```

Au premier lancement depuis une installation PyPI, Trinitty prépare automatiquement le dossier utilisateur:

```bash
~/.local/share/Trinitty/
```

Les fichiers les plus utiles y sont créés sans écraser l'existant:

- `datas/conf.trinity`: overrides locaux lus après la configuration fournie avec le package.
- `install_dependencies.sh`: installateur local, copié sans écraser l'existant.
- `requirements.txt`: dépendances Python utilisées par l'installateur local.
- `keys/openai.key`: clé OpenAI, une seule ligne, sans guillemets.
- `keys/README.txt`: rappel des fichiers de clés reconnus.
- `history/`, `tmp/`, `saved_answer/`, `g4f_cookies/`: dossiers runtime.

La configuration par défaut fournie avec le package est dans `datas/conf.trinity`. Pour éviter de publier des chemins ou préférences locales, placer les overrides dans `~/.local/share/Trinitty/datas/conf.trinity`.

Pour vérifier ou réparer les dépendances après une installation ou une mise à jour:

```bash
trinitty --check-install
```

L'ancien comportement peut être réactivé si nécessaire:

```bash
export TRINITTY_AUTO_INSTALL_DEPENDENCIES=1
```

Exemple:

```text
SAVED_ANSWER = default
OPENAI_API_KEY_FILE = keys/openai.key
OPENAI_MODEL = gpt-5.5
OPENAI_TIMEOUT = 30
GOOGLE_STT_TIMEOUT = 20
GOOGLE_LANGUAGE_TIMEOUT = 8
WEB_SEARCH_TIMEOUT = 10
READ_LINK_TIMEOUT = 10
STT_TRANSCRIPT_CONFIDENCE_MIN = 0.7
STT_WORD_CONFIDENCE_MIN = 0.6
STT_AVG_WORD_CONFIDENCE_MIN = 0.65
STT_BAD_WORD_RATIO_MAX = 0.25
STT_BAD_WORD_COUNT_MAX = 2
STT_DEBUG = False
STT_LOCAL_FALLBACK_ENABLED = False
TTS_CACHE_ENABLED = True
RESPONSE_STREAMING_ENABLED = True
RESPONSE_STREAM_MIN_CHARS = 120
RESPONSE_STREAM_MAX_CHARS = 450
HISTORY_INDEX_ENABLED = True
HISTORY_INDEX_PATH = cache/history_index.json
HISTORY_CLASSIFICATION_ENABLED = True
PLAYBACK_INTERRUPT_ENABLED = False
GPT4FREE_SERVERS_STATUS = Active
```

`RESPONSE_STREAMING_ENABLED = True` permet de commencer la synthèse vocale par segments dès qu'OpenAI fournit assez de texte, au lieu d'attendre toute la réponse. Si le streaming échoue avant le premier segment, Trinitty revient au mode OpenAI classique.

`HISTORY_INDEX_ENABLED = True` crée un index dans `~/.local/share/Trinitty/cache/history_index.json` pour accélérer `Check_History`, l'affichage et la recherche dans l'historique. L'index est reconstruit uniquement quand les fichiers d'historique changent.

`HISTORY_CLASSIFICATION_ENABLED = True` garde la catégorisation de l'historique active, mais elle est lancée en arrière-plan pour ne pas retarder l'envoi de la question à OpenAI ou au fallback gpt4free. `Check_History` reste exécuté sur l'historique local avant la requête principale.

`PLAYBACK_INTERRUPT_ENABLED = True` réactive l'écoute micro pendant la lecture d'une réponse afin de permettre une interruption vocale. La valeur par défaut est `False` pour éviter que Trinitty enregistre pendant qu'elle parle.

`STT_DEBUG = True` écrit, pour chaque reconnaissance vocale, un fichier audio brut `.raw` et un fichier `.json` contenant transcript, confiances, durée, provider utilisé et erreur éventuelle. Le dossier par défaut est `~/.local/share/Trinitty/logs/stt/`.

`STT_LOCAL_FALLBACK_ENABLED = True` active le fallback local Vosk si Google Speech-to-Text échoue. Le modèle doit être disponible au chemin `STT_LOCAL_MODEL_PATH`, par exemple dans `~/.local/share/Trinitty/models/vosk-model-small-fr-0.22`.

`TTS_CACHE_ENABLED = True` évite de régénérer plusieurs fois le même WAV pour le même texte et la même voix. Le cache par défaut est `~/.local/share/Trinitty/cache/tts/`.

`PLAYBACK_INTERRUPT_ENABLED = True` fonctionne aussi en push-to-talk. Pendant la lecture d'une réponse, une commande comme `stop`, `arrête` ou `pause` peut interrompre l'audio.

## gpt4free

Au démarrage, Trinitty peut vérifier les providers `gpt4free` disponibles et garder seulement ceux qui sont marqués comme fonctionnels et compatibles avec une réponse texte.

OpenAI reste le chemin principal. `gpt4free` sert de secours:

- si aucune clé OpenAI n'est disponible;
- si OpenAI renvoie une erreur;
- si OpenAI est désactivé avec `OPENAI_ENABLED = False`.

Certains providers nécessitent des cookies ou des jetons. Les captures locales peuvent être placées dans:

```bash
~/.local/share/Trinitty/g4f_cookies/import/
```

Trinitty synchronise ensuite ces captures vers son dossier de cookies runtime sans versionner de secrets.

## Dépannage

### La commande `trinitty` n'est pas trouvée

Vérifier que `~/.local/bin` est dans le `PATH`:

```bash
echo "$PATH"
```

Si le dossier manque, l'ajouter dans `~/.bashrc`:

```bash
printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> ~/.bashrc
source ~/.bashrc
```

Le lanceur peut être recréé avec:

```bash
~/venvs/trinitty/bin/trinitty --install-launcher
```

### Segmentation fault avec `gpt4free`

Si `g4f` plante à l'import, Trinitty désactive le fallback `gpt4free` au lieu de faire tomber le programme principal. Pour vérifier l'état de `g4f` dans le virtualenv:

```bash
source ~/venvs/trinitty/bin/activate
export PYTHONNOUSERSITE=1
unset PYTHONPATH

python -X faulthandler -c "import g4f; print('g4f import OK')"
python -X faulthandler -c "import g4f.cookies; print('g4f cookies OK')"
```

Si ces commandes échouent, recréer un environnement propre:

```bash
rm -rf ~/venvs/trinitty
python3 -m venv --system-site-packages ~/venvs/trinitty
~/venvs/trinitty/bin/python -m pip install -U pip setuptools wheel
PYTHONNOUSERSITE=1 ~/venvs/trinitty/bin/python -m pip install --no-cache-dir -U trinitty
PYTHONNOUSERSITE=1 ~/venvs/trinitty/bin/trinitty --install-launcher
```

### Google Speech-to-Text ne répond pas

La reconnaissance vocale utilise Google Cloud Speech-to-Text avec des credentials ADC. Les fichiers `google_search.key` et `google_translate.key` ne servent pas à la reconnaissance vocale.

Placer de préférence un fichier de service account dans:

```bash
~/.local/share/Trinitty/keys/google_adc.json
```

Vérifier aussi dans Google Cloud que:

- la validation en deux étapes est activée si Google l'impose au compte;
- l'API Speech-to-Text est activée sur le projet;
- la facturation du projet est active si l'API le demande;
- le service account possède les droits nécessaires.

Si `DEBUG = True` dans `~/.local/share/Trinitty/datas/conf.trinity`, Trinitty écrit un journal dans:

```bash
~/.local/share/Trinitty/logs/
```

Ce journal indique notamment le chemin `GOOGLE_APPLICATION_CREDENTIALS`, les timeouts Google et les erreurs détaillées.

### Trouver les fichiers utilisés

Afficher le module installé, les assets du package et le dossier utilisateur:

```bash
~/venvs/trinitty/bin/python - <<'PY'
import trinitty
print("module :", trinitty.__file__)
print("configuration package :", trinitty.Packaged_Config_File())
print("dossier utilisateur :", trinitty.User_Data_Root())
PY
```

## Fichiers de configuration

Les fichiers principaux sont:

- `datas/conf.trinity`: configuration par défaut.
- `datas/cmd.trinity`: commandes principales.
- `datas/alt_cmd.trinity`: variantes de commandes.
- `datas/alt_trigger.trinity`: variantes de déclencheurs.
- `datas/action.trinity`: verbes/actions reliés aux fonctions.
- `datas/synonym.trinity`: synonymes utilisés par l'analyse.
- `datas/prefix.trinity`: préfixes de commandes.

## Historique et fichiers runtime

Trinitty écrit les réponses audio sauvegardées, l'historique, les erreurs et les fichiers temporaires dans des dossiers.

Dans un checkout local, les chemins par défaut restent proches du dépôt. En installation PyPI ou si le dossier installé n'est pas inscriptible, Trinitty bascule vers:

```bash
~/.local/share/Trinitty/
```

Cela évite d'écrire dans le dossier du package installé.

## Build local

L'installateur installe les outils de packaging par défaut. Après activation du virtualenv:

```bash
python -m build
python -m twine check --strict dist/*
```

Sans virtualenv:

```bash
python -m pip install --upgrade build twine
python -m build
```
