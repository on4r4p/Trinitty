#!/usr/bin/python3
import os,csv

from urlextract import URLExtract



def Write_csv(filename,hist_arg):

    for args in hist_arg:

         hist_file = args[0]
         hist_cats = args[1]
         hist_txt = args[2]
         hist_output = args[3]
         hist_urls = args[4]
         hist_epok = args[5]
         hist_tstamp = args[6]
         hist_output_wav = args[7]


         hist_file = hist_file.removeprefix(" ")
         hist_file = hist_file.removeprefix(".")

         filepath = os.path.join(new_folder,filename)

         with open(filepath, "a+", newline="") as csvfile:
             fieldnames = ["hist_file","hist_cats","hist_input_full","hist_input_short","hist_input_wav","hist_output","hist_output_wav","hist_urls","hist_epok","hist_tstamp"]
             writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

             if csvfile.tell() == 0:
                 writer.writeheader()

             writer.writerow({
             "hist_file": hist_file,
             "hist_cats": hist_cats,
             "hist_input_full": "",
             "hist_input_short": hist_txt,
             "hist_input_wav": "",
             "hist_output": hist_output,
             "hist_output_wav": hist_output_wav,
             "hist_urls": ",".join(hist_urls),
             "hist_epok": hist_epok,
             "hist_tstamp": hist_tstamp,

             })




def load_newcsv(file):
     filepath = os.path.join(new_folder,file)
     with open(filepath, newline="") as csvfile:
             reader = csv.DictReader(csvfile)

             for row in reader:
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

                 print("\n\nhist_file:\n",hist_file)
                 print("hist_cats:\n",hist_cats)
                 print("hist_input_full:\n",hist_input_full)
                 print("hist_input_short:\n",hist_input_short)
                 print("hist_input_wav:\n",hist_input_wav)
                 print("hist_output:\n",hist_output)
                 print("hist_output_wav:\n",hist_output_wav)
                 print("hist_urls:\n",hist_urls)
                 print("hist_epok:\n",hist_epok)
                 print("hist_tstamp:\n",hist_tstamp)


def loadcsv(file):
     histlst = []
     filepath = os.path.join(old_folder,file)
     with open(filepath, newline="") as csvfile:
             reader = csv.DictReader(csvfile)
             for row in reader:
                 bucket = []
                 hist_file = row["hist_file"]
                 hist_cats = row["hist_cats"]
                 hist_txt = row["hist_txt"]
                 hist_output = row["hist_answer"]
                 hist_epok = row["hist_epok"]
                 hist_tstamp = row["hist_tstamp"]
                 hist_wav = row["hist_wav"]
                 hist_url = URLExtract().find_urls(hist_output)

                 print("\nhist_file:\n",hist_file)
                 print("hist_cats:\n",hist_cats)
                 print("hist_txt:\n",hist_txt)
                 print("hist_output:\n",hist_output)
                 print("hist_url:\n",hist_url)
                 print("hist_epok:\n",hist_epok)
                 print("hist_tstamp:\n",hist_tstamp)
                 print("hist_wav:\n",hist_wav)

                 bucket.append(hist_file)
                 bucket.append(hist_cats)
                 bucket.append(hist_txt)
                 bucket.append(hist_output)
                 bucket.append(hist_url)
                 bucket.append(hist_epok)
                 bucket.append(hist_tstamp)
                 bucket.append(hist_wav)
                 histlst.append(bucket)
     Write_csv(file,histlst)


old_folder = "./old_history"
new_folder = "./history"

#hist_files = [f for f in os.listdir(old_folder)]
hist_files = [f for f in os.listdir(old_folder)]

for hf in hist_files:
    print("\n\n loading : %s\n\n"%hf)
    load_newcsv(hf)
#    loadcsv(hf)
#    input("\nstop")
