#!/usr/bin/python3

import locale
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import which

APLAY_BIN = which("aplay") or "aplay"
ROOT_DIR = Path(__file__).resolve().parents[1]


def Set_French_Locale():
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
    except locale.Error:
        return False
    return True

nombres = [
    "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
    "onze", "douze", "treize", "quatorze", "quinze", "seize", "dix-sept", "dix-huit", "dix-neuf",
    "vingt", "vingt et un", "vingt-deux", "vingt-trois", "vingt-quatre", "vingt-cinq", "vingt-six", "vingt-sept", "vingt-huit", "vingt-neuf",
    "trente", "trente et un", "trente-deux", "trente-trois", "trente-quatre", "trente-cinq", "trente-six", "trente-sept", "trente-huit", "trente-neuf",
    "quarante", "quarante et un", "quarante-deux", "quarante-trois", "quarante-quatre", "quarante-cinq", "quarante-six", "quarante-sept", "quarante-huit", "quarante-neuf",
    "cinquante", "cinquante et un", "cinquante-deux", "cinquante-trois", "cinquante-quatre", "cinquante-cinq", "cinquante-six", "cinquante-sept", "cinquante-huit", "cinquante-neuf",
    "soixante", "soixante et un", "soixante-deux", "soixante-trois", "soixante-quatre", "soixante-cinq", "soixante-six", "soixante-sept", "soixante-huit", "soixante-neuf",
    "soixante-dix", "soixante et onze", "soixante-douze", "soixante-treize", "soixante-quatorze", "soixante-quinze", "soixante-seize", "soixante-dix-sept", "soixante-dix-huit", "soixante-dix-neuf",
    "quatre-vingts", "quatre-vingt-un", "quatre-vingt-deux", "quatre-vingt-trois", "quatre-vingt-quatre", "quatre-vingt-cinq", "quatre-vingt-six", "quatre-vingt-sept", "quatre-vingt-huit", "quatre-vingt-neuf",
    "quatre-vingt-dix", "quatre-vingt-onze", "quatre-vingt-douze", "quatre-vingt-treize", "quatre-vingt-quatorze", "quatre-vingt-quinze", "quatre-vingt-seize", "quatre-vingt-dix-sept", "quatre-vingt-dix-huit", "quatre-vingt-dix-neuf"
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


def NbrToTts(number=None,timestamp=None):
    def datewav(*parts):
         return str(ROOT_DIR.joinpath("local_sounds", "dates", *parts))

    def nbrtowav(n):
         pathwav = []
         if n >= 1000:
             milliers_part = n // 1000
             n = n % 1000
             pathwav.append(datewav("milliers", milliers[milliers_part - 1].replace(" ","_")+".wav"))
         if n >= 100:
             centaines_part = n // 100
             n = n % 100
             pathwav.append(datewav("centaines", centaines[centaines_part - 1].replace(" ","_")+".wav"))
         if n > 0:
             pathwav.append(datewav("nombres", nombres[n - 1].replace(" ","_")+".wav"))
         return pathwav

    wavs = []
    if number is not None and timestamp is None:
        return " ".join(nbrtowav(number))
    if timestamp is not None and number is None:
         Set_French_Locale()
         dobject = datetime.fromtimestamp(timestamp)
         fdate = dobject.strftime("%A %d %B %Y")
         print("fdate:",fdate)

         daystr = dobject.strftime("%A")
         daynbr = dobject.day
         wavday = nbrtowav(daynbr)
         mnthstr = dobject.strftime("%B")
         yearnbr = dobject.year
         wavyear = nbrtowav(yearnbr)

         wavs.append(datewav("jours", daystr+".wav"))
         wavs.extend(wavday)
         wavs.append(datewav("mois", mnthstr+".wav"))
         wavs.extend(wavyear)

         print("wavs:",wavs)

         aplay_cmd = [APLAY_BIN, "-q"] + wavs
         print("aplay_cmd:", " ".join(aplay_cmd))
         return subprocess.run(aplay_cmd, check=False).returncode  # noqa: S603 - fixed argv, no shell.
    return None

#    aplay_cmd = " ".join(path)
#    os.system("aplay -q %s" % aplay_cmd)
#    print("path:",path)
#    return tostr

#
#while True:
#
#    nbr_input = input("enter nbr:")

#    try:
#        nbr_input = int(nbr_input)
#    except:
#      continue
#    print(NbrToTts(nbr_input))

def main():
    # timestamp = 1712345729.623188
    timestamp = 1703159794.0
    print(NbrToTts(timestamp=timestamp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#Vdatetime.fromtimestamp(
