#!/usr/bin/python3

import os
import google.cloud.texttospeech as tts

DEFAULT_GOOGLE_CREDENTIALS = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "keys", "google_adc.json")
)


def ensure_google_credentials():
    env_name = "GOOGLE_APPLICATION_CREDENTIALS"
    if not os.environ.get(env_name) and os.path.exists(DEFAULT_GOOGLE_CREDENTIALS):
        os.environ[env_name] = DEFAULT_GOOGLE_CREDENTIALS


def name(fnc, trig):

    trigger = (
        trig.replace(" ", "_")
        .replace("-", "_")
        .replace("*", "_")
        .replace("'", "_")
        .replace("__", "_")
    )

    return fnc + "_" + trigger


def text_to_wav(voice_name, text, filename=None):
    ensure_google_credentials()
    language_code = "-".join(voice_name.split("-")[:2])
    text_input = tts.SynthesisInput(text=text)
    voice_params = tts.VoiceSelectionParams(
        language_code=language_code, name=voice_name
    )
    audio_config = tts.AudioConfig(audio_encoding=tts.AudioEncoding.LINEAR16)

    client = tts.TextToSpeechClient()
    response = client.synthesize_speech(
        input=text_input,
        voice=voice_params,
        audio_config=audio_config,
    )

    if not filename:
        filename = "fr-FR-Neural2-A.wav"

    with open(filename, "wb") as out:
        out.write(response.audio_content)
        print(f'Generated speech saved to "{filename}"')


nombres = [
    "un",
    "deux",
    "trois",
    "quatre",
    "cinq",
    "six",
    "sept",
    "huit",
    "neuf",
    "dix",
    "onze",
    "douze",
    "treize",
    "quatorze",
    "quinze",
    "seize",
    "dix-sept",
    "dix-huit",
    "dix-neuf",
    "vingt",
    "vingt et un",
    "vingt-deux",
    "vingt-trois",
    "vingt-quatre",
    "vingt-cinq",
    "vingt-six",
    "vingt-sept",
    "vingt-huit",
    "vingt-neuf",
    "trente",
    "trente et un",
    "trente-deux",
    "trente-trois",
    "trente-quatre",
    "trente-cinq",
    "trente-six",
    "trente-sept",
    "trente-huit",
    "trente-neuf",
    "quarante",
    "quarante et un",
    "quarante-deux",
    "quarante-trois",
    "quarante-quatre",
    "quarante-cinq",
    "quarante-six",
    "quarante-sept",
    "quarante-huit",
    "quarante-neuf",
    "cinquante",
    "cinquante et un",
    "cinquante-deux",
    "cinquante-trois",
    "cinquante-quatre",
    "cinquante-cinq",
    "cinquante-six",
    "cinquante-sept",
    "cinquante-huit",
    "cinquante-neuf",
    "soixante",
    "soixante et un",
    "soixante-deux",
    "soixante-trois",
    "soixante-quatre",
    "soixante-cinq",
    "soixante-six",
    "soixante-sept",
    "soixante-huit",
    "soixante-neuf",
    "soixante-dix",
    "soixante et onze",
    "soixante-douze",
    "soixante-treize",
    "soixante-quatorze",
    "soixante-quinze",
    "soixante-seize",
    "soixante-dix-sept",
    "soixante-dix-huit",
    "soixante-dix-neuf",
    "quatre-vingts",
    "quatre-vingt-un",
    "quatre-vingt-deux",
    "quatre-vingt-trois",
    "quatre-vingt-quatre",
    "quatre-vingt-cinq",
    "quatre-vingt-six",
    "quatre-vingt-sept",
    "quatre-vingt-huit",
    "quatre-vingt-neuf",
    "quatre-vingt-dix",
    "quatre-vingt-onze",
    "quatre-vingt-douze",
    "quatre-vingt-treize",
    "quatre-vingt-quatorze",
    "quatre-vingt-quinze",
    "quatre-vingt-seize",
    "quatre-vingt-dix-sept",
    "quatre-vingt-dix-huit",
    "quatre-vingt-dix-neuf",
]


centaines = [
    "cent", "deux cents", "trois cents", "quatre cents", "cinq cents",
    "six cents", "sept cents", "huit cents", "neuf cents"
]

milliers = [
    "mille", "deux mille", "trois mille", "quatre mille", "cinq mille",
    "six mille", "sept mille", "huit mille", "neuf mille", "dix mille",
    "onze mille", "douze mille", "treize mille", "quatorze mille", "quinze mille",
    "seize mille", "dix-sept mille", "dix-huit mille", "dix-neuf mille",
    "vingt mille", "vingt-et-un mille", "vingt-deux mille", "vingt-trois mille"
]

jours = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]


mois = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]


def main():
    text_to_wav(
        "fr-FR-Neural2-A",
        "On ma dit que c'était le dernier jour des vaccance . Alors je voulais te dire aurevoir Alice tu vas beaucoup me manquer....Nulos",
        "traduction.wav",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


#text_to_wav("fr-FR-Neural2-A","premier","premier.wav")

#for n,nbr in enumerate(milliers,start=1):
#   if n < 35:
#     continue
#   time.sleep(1.5)
#   txt = nbr
#   name = nbr.replace(" ","_")
#   text_to_wav("fr-FR-Neural2-A",txt,name+".wav")


# AiAsk.wav  AItianhu.wav  Bing.wav  GPTalk.wav  GptGo.wav  Llama2.wav  Phind.wav  Vercel.wav  You.wav
# text_to_wav("fr-FR-Neural2-A", "J'ai trouvé plusieurs données correspondant à votre recherche dans l'historique.Voici tout les résultats.")


# reponses_remerciement = [
#   "De rien.",
#   "Il n'y a pas de quoi.",
#  "Avec plaisir.",
#  "C'est un plaisir d'aider.",
#  "Pas de problème.",
#  "Je t'en prie.",
#  "Je suis là pour ça.",
# "Aucun souci.",
# "Ce fut un plaisir.",
# "C'est normal.",
# "Ça a été un plaisir de vous aider.",
# "N'hésitez pas si vous avez d'autres questions.",
# "Tout le plaisir est pour moi.",

# ]
# n = 1
# for r in reponses_remerciement:

#    text_to_wav("fr-FR-Neural2-A",r,str(n))
#    n+= 1
#   time.sleep(1)
# CMDFILE = "./datas/cmd.trinity"
# with open(CMDFILE, newline="") as csvfile:
#      reader = csv.DictReader(csvfile)
#      for row in reader:
#          if "function" in row:
#              function = row["function"]
#          else:
#              continue

#          if "trigger" in row:
#              trigger = row["trigger"]
#          else:
#              continue

#          filename = name(function,trigger)
#          print("file to save : ./local_sounds/cmd/triggers/%s.wav"%filename)
#          text_to_wav("fr-FR-Neural2-A",trigger,filename)
#          time.sleep(2)
