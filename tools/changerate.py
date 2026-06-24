#!/usr/bin/python3

import os
import re

import sox

def Resample(file):
   try:
       to_rename = "./wav/resampled.wav"
       sample = sox.Transformer()
       sample.set_output_format(rate=24000)
       sample.build(file,to_rename)
       print("\n-Trinitty:%s resampled to 24000."%file)
       os.rename(to_rename,file)
       print("\n-Trinitty:%s saved."%file)
       return(True)
   except Exception as e:
       print("\n-Trinitty:Error:Resample:",str(e))
       return(False)

def extraire_numero(fichier):
    resultat = re.search(r'\d+', fichier)
    return int(resultat.group()) if resultat else None

def main():
   dossier = os.path.dirname(os.path.abspath(__file__))

   if not dossier.endswith("/"):
         dossier += "/"

   print("dossier:",dossier)
   fichiers = [f for f in os.listdir(dossier) if os.path.isfile(os.path.join(dossier, f)) and f.endswith(".wav")]

   fichier_sort = sorted(fichiers, key=extraire_numero)

   print("sorted fichier:")
   for f in fichier_sort:
       print(f)

   return 0


if __name__ == "__main__":
   raise SystemExit(main())
