#!/usr/bin/python3


import os
import subprocess
import time
from shutil import move, which


SOX_BIN = which("sox") or "sox"






def Resample(filepath):
   samplerate = 24000
   tmpfile = filepath.replace(".wav","") + ".tmp.wav"
   print("-Resample:\n%s\nTo 24000 with new tmp filename:\n%s\n"%(filepath,tmpfile))
   subprocess.run([SOX_BIN, "-t", "wav", "-r", str(samplerate), filepath, tmpfile], check=True)  # noqa: S603 - fixed argv, no shell.

   while True:
      if os.path.exists(tmpfile):
          break
      time.sleep(0.5)
   print("-Checking new tmp file:")
   IsGood = CheckSample(tmpfile)
   if IsGood:
         print("-File has good sample rate :",tmpfile)
         print("-Overwriting original : mv %s %s"%(tmpfile,filepath))
         move(tmpfile, filepath)
         print("-Done")
   else:
         print("File has bad sample rate :",tmpfile)



def CheckSample(filepath):

         samplerate = 24000
#         print("cmd:sox --i '%s'"%filepath)
         subproc = subprocess.run([SOX_BIN, "--i", filepath], check=True, stdout=subprocess.PIPE, text=True)  # noqa: S603 - fixed argv, no shell.
         output = subproc.stdout.splitlines()
         for line in output:
             if "Sample Rate    : " in line:
                 sample_rate = line.split("Sample Rate    : ")[1]
                 if samplerate != int(sample_rate):
                      return(False)
         return(True)




samplerate = 24000

def main():
   dossier = os.path.dirname(os.path.abspath(__file__))

   if not dossier.endswith("/"):
         dossier += "/"

   print("dossier:",dossier)
   fichiers = [f for f in os.listdir(dossier) if os.path.isfile(os.path.join(dossier, f))]
   Badsample = []

   for filename in fichiers:
       if filename.endswith(".wav"):
            filepath = dossier+filename
            IsGood = CheckSample(filepath)
            if not IsGood:
                Badsample.append(filepath)

   for badfile in Badsample:
        print("This file has to be resampled:",badfile)
        Resample(badfile)

   return 0


if __name__ == "__main__":
     raise SystemExit(main())



#                                        print("overwriting traitor : mv %s %s"%(tmpfile,file))
#                                        os.system("mv %s %s"%(tmpfile,file))
