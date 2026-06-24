#!/usr/bin/python3
import csv,os,subprocess
from pathlib import Path
from shutil import which
from unidecode import unidecode


APLAY_BIN = which("aplay") or "aplay"


def Play_Audio_File(filepath):
    filepath = str(filepath or "").strip()
    if not filepath:
        return 1
    return subprocess.run([APLAY_BIN, filepath], check=False).returncode  # noqa: S603 - fixed argv, no shell.


def Isolate_Search_Request(txt,triggers):

    print("triggers:\n",triggers)

    print("web_request:\n",web_request)

    print("\n\ntxt before:",txt)


    def clean(to_clean):
         while True:
              if to_clean.endswith(" "):
                 to_clean = to_clean[:-1]
                 continue
              if to_clean.startswith(" "):
                 to_clean = to_clean[1:]
                 continue
              if "  " in to_clean:
                 to_clean = to_clean.replace("  "," ")
                 continue
              break
         return(to_clean)

    def remove(to_clean,remove_lst):

          for to_rm in remove_lst:
              pos = 0
              bucket = ""
              to_rm_lst = []
              while True:
                  if to_rm[pos] != "*":
                      bucket += to_rm[pos]
                  else:
                      if pos > 0:
                          if to_rm[pos-1] not in (" ","*"):
                             bucket += " "
                             to_rm_lst.append(bucket)
                             bucket = ""
                          else:
                             to_rm_lst.append(bucket)
                             bucket = ""
                      else:
                             bucket += " "
                             to_rm_lst.append(bucket)
                             bucket = ""
                  pos += 1
                  if pos >= len(to_rm):
                             to_rm_lst.append(bucket)
                             break
              to_rm_lst = [rm.replace("  "," ") for rm in to_rm_lst]

#              print("\nto_rm_lst:")

              for rm in to_rm_lst:
#                  print("'%s'"%rm)
#                  to_clean = to_clean.replace(rm," ")
#                  to_clean = " ".join([word for word in to_clean.split() if word != rm])
                  pos_rm = to_clean.find(rm)
                  while pos_rm != -1:
                        to_clean = to_clean[:pos_rm] + to_clean[pos_rm + len(rm):]
                        pos_rm = to_clean.find(rm)

          return(clean(to_clean))


    filter = ["s'il te plait","si te plait","sil te plait","merci"]

    txt = unidecode(txt.lower())

    for f in filter:
        txt = txt.replace(f," ")

    txt = clean(txt)

    txt = remove(txt,action_words)

    txt = remove(txt,web_request)

    txt = remove(txt,triggers)

    print("\n\ntxt:'%s'"%txt)
#    print("double space:"," " in txt)
    print("len(txt):",len(txt))
#    print(action_words)




def Write_csv(function_name, trigger_word,filename):

    #CMDFILE,
    with open(filename, "a+", newline="") as csvfile:
        fieldnames = ["function", "trigger"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if csvfile.tell() == 0:
            writer.writeheader()

        writer.writerow({"function": function_name, "trigger": trigger_word})

    return(Load_Csv())


def Missing_Runtime_File(filepath):
    print("-%s not found." % filepath)
    return False




def Load_Csv():

    global trinity_name
    global trinity_mean
    global trinity_creator
    global trinity_script
    global trinity_help
    global prompt_request
    global trinity_source_request
    global rnd_request
    global repeat_request
    global search_history_request
    global read_link_request
    global play_wav_request
    global web_request
    global wait_words
    global action_words
    global add_words
    global action_functions
    global alt_trigger
    global verb_lst
    global synonyms_list
    global fnc_verb


    trinity_name = []
    trinity_mean = []
    trinity_creator = []
    trinity_script = []
    trinity_help = []
    prompt_request = []
    trinity_source_request = []
    rnd_request = []
    repeat_request = []
    search_history_request = []
    read_link_request = []
    play_wav_request = []
    web_request = []
    wait_words = []
    action_words = []
    add_words = []
    action_functions = []
    alt_trigger = []
    verb_lst = []
    synonyms_list = []
    fnc_verb = {}




    if os.path.exists(SYNFILE):
         with open(SYNFILE, newline="") as f:
              data = f.readlines()

              for raw_line in data:
                  tmplst = []
                  parts = raw_line.strip().split(",")
                  for l in parts:
                      if l != "":
                          tmplst.append(l)
                  synonyms_list.append(tmplst)


    else:

          return Missing_Runtime_File(SYNFILE)

    if os.path.exists(TRIFILE):
         with open(TRIFILE, newline="") as csvfile:
             reader = csv.DictReader(csvfile)
             for row in reader:
                 if "trigger" in row:
                      trigger= row["trigger"]
                 else:
                     continue
                 if trigger not in alt_trigger:
                      alt_trigger.append(trigger)

    else:

          return Missing_Runtime_File(TRIFILE)


    if os.path.exists(CMDFILE):
         with open(CMDFILE, newline="") as csvfile:
             reader = csv.DictReader(csvfile)
             for row in reader:
                 if "function" in row:
                      function = row["function"]
                      if "trigger" in row:
                           trigger = row["trigger"]
                      else:
                          continue
                      if function == "trinity_name":
                           trinity_name.append(trigger)
                      elif function == "trinity_mean":
                           trinity_mean.append(trigger)
                      elif function == "trinity_creator":
                           trinity_creator.append(trigger)
                      elif function == "trinity_script":
                           trinity_script.append(trigger)
                      elif function == "trinity_help":
                           trinity_help.append(trigger)
                      elif function == "prompt_request":
                           prompt_request.append(trigger)
                      elif function == "trinity_source_request":
                           trinity_source_request.append(trigger)
                      elif function == "rnd_request":
                           rnd_request.append(trigger)
                      elif function == "repeat_request":
                           repeat_request.append(trigger)
                      elif function == "search_history_request":
                           search_history_request.append(trigger)
                      elif function == "read_link_request":
                           read_link_request.append(trigger)
                      elif function == "play_wav_request":
                           play_wav_request.append(trigger)
                      elif function == "web_request":
                           web_request.append(trigger)
                      elif function == "add_words":
                           add_words.append(trigger)
                      elif function == "wait_words":
                           wait_words.append(trigger)
    else:

          return Missing_Runtime_File(CMDFILE)



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


                 if verb not in action_words:
                         action_words.append(verb)
                         verb_lst.append(verb)
                         if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((verb,alf))
                                    if alf not in fnc_verb:
                                        fnc_verb[alf] = []
                                    if verb not in fnc_verb[alf]:
                                        fnc_verb[alf].append(verb)

                         else:
                               action_functions.append((verb,functions))
                               if functions not in fnc_verb:
                                     fnc_verb[functions] = []
                               if verb not in fnc_verb[functions]:
                                     fnc_verb[functions].append(verb)

                 if ind1 not in action_words:
                         action_words.append(ind1)
                         if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((ind1,alf))
                         else:
                               action_functions.append((ind1,functions))

                 if ind2 not in action_words:
                          action_words.append(ind2)

                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((ind2,alf))
                          else:
                               action_functions.append((ind2,functions))

                 if cond1 not in action_words:
                         action_words.append(cond1)
                         if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond1,alf))
                         else:
                               action_functions.append((cond1,functions))


                 if cond2 not in action_words:
                          action_words.append(cond2)

                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond2,alf))
                          else:
                               action_functions.append((cond2,functions))


                 if sub1 not in action_words:
                         action_words.append(sub1)
                         if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((sub1,alf))
                         else:
                               action_functions.append((sub1,functions))

                 if sub2 not in action_words:
                          action_words.append(sub2)

                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((sub2,alf))
                          else:
                               action_functions.append((sub2,functions))

                 if participe not in action_words:
                         action_words.append(participe)
                         if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((participe,alf))
                         else:
                               action_functions.append((participe,functions))

                 if ind1+suffix1 not in action_words:
                          action_words.append(ind1+suffix1)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((ind1+suffix1,alf))
                          else:
                               action_functions.append((ind1+suffix1,functions))

                 if ind2+suffix1 not in action_words:
                          action_words.append(ind2+suffix1)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((ind2+suffix1,alf))
                          else:
                               action_functions.append((ind2+suffix1,functions))



                 if cond1+suffix2 not in action_words:
                          action_words.append(cond1+suffix2)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond1+suffix2,alf))
                          else:
                               action_functions.append((cond1+suffix2,functions))

                 if cond2+suffix3 not in action_words:
                          action_words.append(cond2+suffix3)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond2+suffix3,alf))
                          else:
                               action_functions.append((cond2+suffix3,functions))

                 if cond1+suffix2 not in action_words:
                          action_words.append(cond1+suffix2)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond1+suffix2,alf))
                          else:
                               action_functions.append((cond1+suffix2,functions))

                 if cond2+suffix3 not in action_words:
                          action_words.append(cond2+suffix3)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond2+suffix3,alf))
                          else:
                               action_functions.append((sub2+suffix3,functions))


                 if cond1+suffix2 not in action_words:
                          action_words.append(cond1+suffix2)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond1+suffix2,alf))
                          else:
                               action_functions.append((cond1+suffix2,functions))

                 if cond2+suffix3 not in action_words:
                          action_words.append(cond2+suffix3)
                          if "***" in functions:
                              allowed_fonctions = functions.split("***")
                              for alf in allowed_fonctions:
                                    action_functions.append((cond2+suffix3,alf))
                          else:
                               action_functions.append((cond2+suffix3,functions))

                 with open(PREFILE, newline="") as csvfile2:
                      reader2 = csv.DictReader(csvfile2)

                      for pref_row in reader2:
                           if "present1" in pref_row:
                                present1= pref_row["present1"]
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

                           if not any("que" in var for var in [present1,present2,cond1,cond2]):
                               pre1 =present1+"*"+verb
                               if pre1 not in action_words:
#                                    print(pres1)
                                    action_words.append(pre1)
                                    if "***" in functions:
                                        allowed_fonctions = functions.split("***")
                                        for alf in allowed_fonctions:
                                              action_functions.append((pre1,alf))
                                    else:
                                         action_functions.append((pre1,functions))

                               pre2 =present2+"*"+verb
                               if pre2 not in action_words:
#                                    print(pres2)
                                    action_words.append(pre2)
                                    if "***" in functions:
                                        allowed_fonctions = functions.split("***")
                                        for alf in allowed_fonctions:
                                              action_functions.append((pre2,alf))
                                    else:
                                         action_functions.append((pre2,functions))


                               pre3 =cond1+"*"+verb
                               if pre3 not in action_words:
#                                    print(pre3)
                                    action_words.append(pre3)
                                    if "***" in functions:
                                        allowed_fonctions = functions.split("***")
                                        for alf in allowed_fonctions:
                                              action_functions.append((pre3,alf))
                                    else:
                                         action_functions.append((pre3,functions))

                               pre4 =cond2+"*"+verb
                               if pre4 not in action_words:
#                                    print(pre4)
                                    action_words.append(pre4)
                                    if "***" in functions:
                                        allowed_fonctions = functions.split("***")
                                        for alf in allowed_fonctions:
                                              action_functions.append((pre4,alf))
                                    else:
                                         action_functions.append((pre4,functions))



                           else:
                               pre1 =present1+"*"+sub1
                               if pre1 not in action_words:
#                                    print(pres1)
                                    action_words.append(pre1)
                                    if "***" in functions:
                                        allowed_fonctions = functions.split("***")
                                        for alf in allowed_fonctions:
                                              action_functions.append((pre1,alf))
                                    else:
                                         action_functions.append((pre1,functions))

                               pre2 =present2+"*"+sub2
                               if pre2 not in action_words:
#                                    print(pres2)
                                    action_words.append(pre2)
                                    if "***" in functions:
                                        allowed_fonctions = functions.split("***")
                                        for alf in allowed_fonctions:
                                              action_functions.append((pre2,alf))
                                    else:
                                         action_functions.append((pre2,functions))




         for k in fnc_verb:
             fnc_verb[k].append("pouvoir")
             fnc_verb[k].append("vouloir")
             fnc_verb[k].append("être")
             fnc_verb[k].append("falloir")
             fnc_verb[k].append("devoir")
    else:

          missing_files = [path for path in [ACTFILE, PREFILE] if not os.path.exists(path)]
          return Missing_Runtime_File(", ".join(missing_files))


    if os.path.exists(ALTFILE):
         with open(ALTFILE, newline="") as csvfile:
             reader = csv.DictReader(csvfile)
             for row in reader:

                 if "function" in row:
                      function = row["function"]
                 else:
                     continue

                 if "trigger" in row:
                      trigger = row["trigger"]


                      if function == "ask_for_name":
                           trinity_name.append(trigger)
                      elif function == "ask_for_mean":
                           trinity_mean.append(trigger)
                      elif function == "ask_for_creator":
                           trinity_creator.append(trigger)
                      elif function == "trinity_script":
                           trinity_script.append(trigger)
                      elif function == "ask_for_help":
                           trinity_help.append(trigger)
                      elif function == "ask_for_prompt":
                           prompt_request.append(trigger)
                      elif function == "trinity_source_request":
                           trinity_source_request.append(trigger)
                      elif function == "ask_for_rnd":
                           rnd_request.append(trigger)
                      elif function == "ask_for_repeat":
                           repeat_request.append(trigger)
                      elif function == "ask_for_history":
                           search_history_request.append(trigger)
                      elif function == "ask_to_read_link":
                           read_link_request.append(trigger)
                      elif function == "ask_to_play_wav":
                           play_wav_request.append(trigger)
                      elif function == "ask_for_web":
                           web_request.append(trigger)
                      elif function == "ask_to_wait":
                           wait_words.append(trigger)
                      elif function == "ask_to_add":
                           add_words.append(trigger)
    else:

          return Missing_Runtime_File(ALTFILE)

    return True

#    print("result:\n\n")
#    print("trinity_name",trinity_name)
#    print("trinity_mean",trinity_mean)
#    print("trinity_creator",trinity_creator)
#    print("trinity_script",trinity_script)
#    print("trinity_help",trinity_help)
#    print("prompt_request",prompt_request)
#    print("trinity_source_request",trinity_source_request)
#    print("rnd_request",rnd_request)
#    print("repeat_request",repeat_request)
#    print("search_history_request",search_history_request)
#    print("read_link_request",read_link_request)
#    print("play_wav_request",play_wav_request)
#    print("web_request",web_request)
#    print("wikipedia_full_request",wikipedia_full_request)
#    print("wait_words",wait_words)
#    print("\naction_words",action_words)
#    print("\n\n")
#    for i in action_words:
#        print(i)
#    print("\n\naction_functions:\n",action_functions)
#    print("prompt_request",prompt_request)
#    print("action_functions:",action_functions)
#    for item in search_history_request:
#             print("item:",item)
#    input("\n")
#    for i in synonyms_list:
#        print(i)




def Add_Trigger():

    print("\n-Trinitty:Dans la fonction Add_Trigger.\n")

    def seeknreturn(var_to_check,list_elements):
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
          return(found_lst)



    def checktrigger(trigger,funcname):





              def getwav(f,trigparts):

                   if f == "ask_to_wait":
                             trigcat = "wait_words"
                   if f == "ask_for_name":
                             trigcat = "trinity_name"
                   if f == "ask_for_mean":
                             trigcat = "trinity_mean"
                   if f == "ask_for_creator":
                             trigcat = "trinity_creator"
                   if f == "ask_for_rnd":
                             trigcat = "rnd_request"
                   if f == "ask_for_repeat":
                             trigcat = "repeat_request"
                   if f == "ask_for_prompt":
                             trigcat = "prompt_request"
                   if f == "ask_for_help":
                             trigcat = "trinity_help"
                   if f == "ask_to_play_wav":
                             trigcat = "play_wav_request"
                   if f == "ask_for_history":
                             trigcat = "search_history_request"
                   if f == "ask_to_read_link":
                             trigcat = "read_link_request"
                   if f == "ask_for_web":
                             trigcat = "web_request"

                   Play_Audio_File("%s/local_sounds/cmd/triggers/%s.wav" % (script_path,trigcat))

                   for trigpart in trigparts:
                        normalized_trigpart = unidecode(trigpart.replace(" ","_").replace("-","_").replace("*","_").replace("'","_"))
                        wavname = trigcat + "_" + normalized_trigpart + ".wav"
                        Play_Audio_File("%s/local_sounds/cmd/triggers/%s" % (script_path,wavname))
                        return()
                   return None


              new_ambiguity = {}

              trigger = unidecode(trigger.lower().replace(","," ").replace("!"," ").replace("?"," ").replace("  "," "))


              ask_to_action = seeknreturn(trigger,action_words)

              ask_to_add = seeknreturn(trigger,add_words)

              ask_for_name = seeknreturn(trigger,trinity_name)

              ask_for_mean = seeknreturn(trigger,trinity_mean)

              ask_for_creator = seeknreturn(trigger,trinity_creator)

              ask_for_help = seeknreturn(trigger,trinity_help)

              ask_for_prompt = seeknreturn(trigger,prompt_request)

              ask_for_rnd = seeknreturn(trigger,rnd_request)

              ask_for_repeat = seeknreturn(trigger,repeat_request)

              ask_for_history = seeknreturn(trigger,search_history_request)

              ask_for_web = seeknreturn(trigger,web_request)

              ask_to_read_link = seeknreturn(trigger,read_link_request)

              ask_to_play_wav = seeknreturn(trigger,play_wav_request)

              ask_to_wait = seeknreturn(trigger,wait_words)


              if ask_to_action :
                   if ask_to_wait and funcname != "ask_to_wait":
                             new_ambiguity["ask_to_wait"] = ask_to_wait
                   if ask_for_name and funcname != "ask_for_name":
                             new_ambiguity["ask_for_name"] = ask_for_name
                   if ask_for_mean and funcname != "ask_for_mean":
                             new_ambiguity["ask_for_mean"] = ask_for_mean
                   if ask_for_creator and funcname != "ask_for_creator":
                             new_ambiguity["ask_for_creator"] = ask_for_creator
                   if ask_for_rnd and funcname != "ask_for_rnd":
                             new_ambiguity["ask_for_rnd"] = ask_for_rnd
                   if ask_for_repeat and funcname != "ask_for_repeat":
                             new_ambiguity["ask_for_repeat"] = ask_for_repeat
                   if ask_for_prompt and funcname != "ask_for_prompt":
                             new_ambiguity["ask_for_prompt"] =ask_for_prompt
                   if ask_for_help and funcname != "ask_for_help":
                             new_ambiguity["ask_for_help"] = ask_for_help
                   if ask_to_play_wav and funcname != "ask_to_play_wav":
                             new_ambiguity["ask_to_play_wav"] = ask_to_play_wav
                   if ask_for_history and funcname != "ask_for_history":
                             new_ambiguity["ask_for_history"] =  ask_for_history
                   if ask_to_read_link and funcname != "ask_to_read_link":
                              new_ambiguity["ask_to_read_link"] = ask_to_read_link
                   if ask_for_web and funcname != "ask_for_web":
                             new_ambiguity["ask_for_web"] = ask_for_web
                   if ask_to_add and funcname != "ask_to_add":
                             new_ambiguity["ask_for_web"] = ask_to_add
              if len(new_ambiguity) == 0:

                    print("\n-Parfait,cette phrase semble déclencher la fonction:",funcname)
                    Play_Audio_File("%s/local_sounds/cmd/valid.wav" % script_path)
                    Play_Audio_File("%s/local_sounds/cmd/save.wav" % script_path)
                    while True:
                       rusure =input("\n-Sauvegarde cette phrase dans la base de données ?:\n\n%s\n\n-Votre choix:(oui/non/abandonner)"%trigger).lower()
                       if rusure in ["oui","non","abandonner"]:
                          if rusure == "oui":
                               Write_csv(trigger,funcname,ALTFILE)
                               return(True)
                          if rusure == "non":
                               return(False)
                          if rusure =="abandonner":
                               return(True)

              else:

                    Play_Audio_File("%s/local_sounds/cmd/new_ambiguity.wav" % script_path)
                    for fnc,trigged in new_ambiguity.items():
                             print("\n\n-La fonction %s est déclenchée par cette partie: %s"%(fnc,trigged))
                             getwav(fnc,trigged)

                    Play_Audio_File("%s/local_sounds/cmd/new_ambiguity2.wav" % script_path)

#              print("\n\n-mini touchdown\n\n")
              return None




    functions = [
         ('trinity_name', 'pour avoir le nom du script de Trinitty',"Salut ça va ?Comment tu t'appelle?","comment * t'appelle","trinity_name"),
         ('trinity_mean', 'pour avoir le sens du nom du script de Trinitty',"Pourquoi on a décidé de t'appeler comme ça?","pourquoi *t'appeler comme ça","trinity_mean"),
         ('trinity_creator', 'pour connaitre le nom du créateur du script de Trinitty',"Qui est-ce qui t'a créé ?","qui * t'a créé","trinity_creator"),
         ('trinity_help', "pour avoir l'aide du script Trinitty","Affiche moi l'aide de ton script.","affiche*moi *aide * ton script","ask_for_help"),
         ('prompt_request', 'pour pouvoir écrire à Trinitty',"J'ai besoin de t'écrire un truc.","ai * de t'écrire","ask_for_prompt"),
         ('trinity_source_request', 'pour afficher la source du script Trinitty',"tu peux me montrer ton code source?","peux* montrer * ton code","ask_for_src"),
         ('rnd_request', 'pour effectuer un choix aléatoire',"Peux-tu faire un choix entre 1 et 2?","peux*tu * choix entre * et ","ask_for_rnd"),
         ('repeat_request', 'pour demander à Trinitty de répéter',"J'ai rien compris tu peux me redire ça ?","tu*peux* redire ça","ask_to_repeat"),
         ('search_history_request', "pour faire une recherche dans l'historique","Regarde dans l'historique si tu trouve Albert Einstein","regarde * l'historique * si * trouve","ask_for_history"),
         ('read_link_request', "pour lire une page web","Tu peux me lire ce qu'il y a dans cette page web?","tu*peux* lire * dans * page web","ask_to_read_link"),
         ('play_wav_request', 'Pour lire un fichier audio',"Tu peux me jouer ce fichier audio s'il te plaît?","tu*peux* jouer * fichier audio","ask_to_play_wav"),
         ('web_request', 'Pour faire une recherche sur internet',"Fais-moi une recherche sur google a propos du big bang","fais*moi recherche * google * a propos","ask_for_web"),
         ('wait_words', "Pour demander à Trinitty d'attendre","Minute papillon je ne suis pas près!","Minute * je * suis pas près","ask_to_wait"),
         ('add_words', 'Pour ajouter un nouveau déclencheur de fonction',"j'aimerai ajouter un nouveau trigger.","ajouter * nouveau * trigger","ask_to_add"),
   ]


    for index, (function_name, function_description,_,_,_) in enumerate(functions, start=1):
         print(f"({index}) {function_name} :  {function_description}")

    while True:
         try:
             user_choice = int(input(f"\nChoisissez une fonction (1 à {len(functions)}): "))
             if user_choice in range(1,len(functions)+1):
                selected_function = functions[user_choice - 1][0]
                selected_description = functions[user_choice - 1][1]
                exemple1 = functions[user_choice - 1][2]
                exemple2 = functions[user_choice - 1][3]
                seekname = functions[user_choice - 1][4]
                break
         except Exception as e:
             print("\n-Invalid function choice:%s" % str(e))
             continue
    print(f"Vous avez choisi {selected_function}: {selected_description}")




    while True:
             print("\n\n===============\n\n")

#             os.system("aplay %s/local_sounds/cmd/instruction.wav"%script_path)
             print("\n\n===============\n\n==Ajouter un nouveau déclencheur pour la fonction: %s ==\n\n-Gardez la partie qui identifie l'action %s dans votre phrase."%(selected_function,selected_description))
             print("\n-Par example si votre phrase complète ressemble à ceci:\n\n\t-",exemple1)
             print("\n-J'aimerais que vous ne gardiez que cela:\n\n\t-",exemple2)
             print("\n-Le symbole * est utilisé içi afin de ne pas tenir compte des mots qu'il peut y avoir à cette position.\n\n")
             print("\n\n-Voici les déclencheurs déjà enregistrés pour cette fonction:\n")
             for n,i in enumerate(globals()[selected_function]):print("\t%s-:%s"%(n,i))

             if seekname in fnc_verb:
                 print("\n\n-Voici la liste de verbes déjà associés à cette fonction:\n")
                 for n,f in enumerate(fnc_verb[seekname]):print("\t%s-:%s"%(n,f))
             else:
                 for k in fnc_verb:
                    print(k)
             print("\n-Si votre phrase utilise l'un de ces verbes meme sous une forme conjugué il n'est pas nécessaire de l'écrire.\n-Vous pouvez néanmoins le faire si vous souhaitez que votre déclencheur soit plus précis.\n\n-Les accents et caractére spéciaux et ponctuation sont automatiquement enlevés.\n")
             new_trigger = input("\n-Nouveau déclencheur pour la fonction %s :"%selected_function)
             valid = checktrigger(new_trigger,seekname)
             if valid:
                  return(selected_function)















def Commandes(txt):




    def postprod(txt,funcname,specific_trigger=None,main_trigger=None):
        asked = False

        def has_syn(function_name,sentence,altlst = None):
            synlst = []
            syntoprint = []
            found = []

            if altlst:
                 for act in altlst:
                         synlst.append(act)
            else:
                 for syn in action_functions:
                     act = syn[0]
                     fn = syn[1]
                     if fn == function_name:
                         #print("adding:",act)
                         synlst.append(act)
                         for v in verb_lst:
                             if v in act and v not in syntoprint:
                                syntoprint.append(v)

            for syn in synlst:
                if syn in sentence:
                   found.append(syn)
            if len(found) == 0:
                 if not altlst:
                      print("\n-Your sentence have to contain at least one of those verbs:\n\n%s\n\n"%(syntoprint))
                      return(False)
                 print("\n-Your sentence have to contain at least one of those triggers:\n\n%s\n\n"%(altlst))
                 return(False)
            return(True)


        def checktrigger(trigger,funcname,spec_trigger,main_action=None):


              def getwav(f,trigparts):

                   if f == "ask_to_wait":
                             trigcat = "wait_words"
                   if f == "ask_for_name":
                             trigcat = "trinity_name"
                   if f == "ask_for_mean":
                             trigcat = "trinity_mean"
                   if f == "ask_for_creator":
                             trigcat = "trinity_creator"
                   if f == "ask_for_rnd":
                             trigcat = "rnd_request"
                   if f == "ask_for_repeat":
                             trigcat = "repeat_request"
                   if f == "ask_for_prompt":
                             trigcat = "prompt_request"
                   if f == "ask_for_help":
                             trigcat = "trinity_help"
                   if f == "ask_to_play_wav":
                             trigcat = "play_wav_request"
                   if f == "ask_for_history":
                             trigcat = "search_history_request"
                   if f == "ask_to_read_link":
                             trigcat = "read_link_request"
                   if f == "ask_for_web":
                             trigcat = "web_request"

                   Play_Audio_File("%s/local_sounds/cmd/triggers/%s.wav" % (script_path,trigcat))

                   for trigpart in trigparts:
                        normalized_trigpart = unidecode(trigpart.replace(" ","_").replace("-","_").replace("*","_").replace("'","_"))
                        wavname = trigcat + "_" + normalized_trigpart + ".wav"
                        Play_Audio_File("%s/local_sounds/cmd/triggers/%s" % (script_path,wavname))
                        return()
                   return None


              new_ambiguity = {}

              trigger = unidecode(trigger.lower().replace(","," ").replace("!"," ").replace("?"," ").replace("  "," "))

              print("main_action=None:",main_action)
              print("spec_trigger:",spec_trigger)
              print("funcname:",funcname)
              print("trigger:",trigger)

              main_trigger = has_syn(funcname,trigger)
              func_trigger = has_syn(funcname,trigger,altlst=spec_trigger)

              if not main_trigger:
                  return(False)
              if not func_trigger:
                  return(False)


              ask_to_action = seeknreturn(trigger,action_words)

              ask_for_name = seeknreturn(trigger,trinity_name)

              ask_for_mean = seeknreturn(trigger,trinity_mean)

              ask_for_creator = seeknreturn(trigger,trinity_creator)

              ask_for_help = seeknreturn(trigger,trinity_help)

              ask_for_prompt = seeknreturn(trigger,prompt_request)

              ask_for_rnd = seeknreturn(trigger,rnd_request)

              ask_for_repeat = seeknreturn(trigger,repeat_request)

              ask_for_history = seeknreturn(trigger,search_history_request)

              ask_for_web = seeknreturn(trigger,web_request)

              ask_to_read_link = seeknreturn(trigger,read_link_request)

              ask_to_play_wav = seeknreturn(trigger,play_wav_request)

              ask_to_wait = seeknreturn(trigger,wait_words)


              if ask_to_action :
                   if ask_to_wait and funcname != "ask_to_wait":
                             new_ambiguity["ask_to_wait"] = ask_to_wait
                   if ask_for_name and funcname != "ask_for_name":
                             new_ambiguity["ask_for_name"] = ask_for_name
                   if ask_for_mean and funcname != "ask_for_mean":
                             new_ambiguity["ask_for_mean"] = ask_for_mean
                   if ask_for_creator and funcname != "ask_for_creator":
                             new_ambiguity["ask_for_creator"] = ask_for_creator
                   if ask_for_rnd and funcname != "ask_for_rnd":
                             new_ambiguity["ask_for_rnd"] = ask_for_rnd
                   if ask_for_repeat and funcname != "ask_for_repeat":
                             new_ambiguity["ask_for_repeat"] = ask_for_repeat
                   if ask_for_prompt and funcname != "ask_for_prompt":
                             new_ambiguity["ask_for_prompt"] =ask_for_prompt
                   if ask_for_help and funcname != "ask_for_help":
                             new_ambiguity["ask_for_help"] = ask_for_help
                   if ask_to_play_wav and funcname != "ask_to_play_wav":
                             new_ambiguity["ask_to_play_wav"] = ask_to_play_wav
                   if ask_for_history and funcname != "ask_for_history":
                             new_ambiguity["ask_for_history"] =  ask_for_history
                   if ask_to_read_link and funcname != "ask_to_read_link":
                              new_ambiguity["ask_to_read_link"] = ask_to_read_link
                   if ask_for_web and funcname != "ask_for_web":
                             new_ambiguity["ask_for_web"] = ask_for_web

              if len(new_ambiguity) == 0:

                    print("\n-Parfait,cette phrase semble déclencher la fonction:",funcname)
                    Play_Audio_File("%s/local_sounds/cmd/valid.wav" % script_path)
                    Play_Audio_File("%s/local_sounds/cmd/save.wav" % script_path)
                    while True:
                       rusure =input("\n-Sauvegarde cette phrase dans la base de données ?:\n\n%s\n\n-Votre choix:(oui/non/abandonner)"%trigger).lower()
                       if rusure in ["oui","non","abandonner"]:
                          if rusure == "oui":
                               Write_csv(trigger,funcname,ALTFILE)
                               return(True)
                          if rusure == "non":
                               return(False)
                          if rusure =="abandonner":
                               return(True)

              else:

                    Play_Audio_File("%s/local_sounds/cmd/new_ambiguity.wav" % script_path)
                    for fnc,trigged in new_ambiguity.items():
                             print("\n\n-La fonction %s est déclenchée par cette partie: %s"%(fnc,trigged))
                             getwav(fnc,trigged)

                    Play_Audio_File("%s/local_sounds/cmd/new_ambiguity2.wav" % script_path)

#              print("\n\n-mini touchdown\n\n")
              return None


        while True:
          print("\n\n===============\n\n")

          if not asked:
               Play_Audio_File("%s/local_sounds/cmd/question_trigger.wav" % script_path)
               while True:
                   helpme = input("-Pouvez-vous m'aider à mieux intégrer cette phrase dans ma base de données?\n-Cela ne prendra pas longtemps.\n\nVotre Choix (oui/non):").lower()
                   if helpme in  ["oui","non"]:
                           if "oui" in helpme:
                                  helpme = True
                                  asked = True
                           else:
                                  helpme = False
                           break
          else:
               helpme = True

          if helpme:
             Play_Audio_File("%s/local_sounds/cmd/instruction.wav" % script_path)
             print("\n\n===============\n\n==Ajouter un nouveau declencheur pour la fonction: %s ==\n\n-Pouvez-vous garder uniquement la partie qui identifie l'action dans votre phrase?"%funcname)
             print("\n-Par example si vous auriez dis:\n\n\t-Peux-tu s'il te plaît chercher un truc sur Albert Einstein in wikipedia ce serait super cool!")
             print("\n-J'aurais voulue que vous ne gardiez que cela:\n\n\t-Peux-tu * chercher * dans wikipedia")
             print("\n-Le symbole * est utilisé içi afin de ne pas tenir compte des mots qu'il peut y avoir à cette position.")
             print("\n-Voici votre phrase:\n%s\n"%txt)
             new_trigger = input("\nNouvelle déclencheur pour la fonction %s :"%funcname)
             valid = checktrigger(new_trigger,funcname,spec_trigger=specific_trigger,main_action=main_trigger)
             if valid:
                  return(funcname)
          else:
               Play_Audio_File("%s/local_sounds/cmd/sorry.wav" % script_path)
               Write_csv(new_trigger,funcname,ALTFILE)
               return(funcname)
    def disambiguify(_actions,function_names,txt,action_trigger= None):


       func_name_toadd = None
       trigger_words_toadd = None
       must_contain = None
       trigger_function = {}
       triggered_parts = {}
       score_function = {}

       for fnc in function_names:
               if fnc == "ask_to_action":
                      continue
               if fnc == "ask_for_web":
                   trigger_function[fnc] = web_request
               if fnc == "ask_to_play_wav":
                   trigger_function[fnc] = play_wav_request
               if fnc == "ask_for_history":
                   trigger_function[fnc] = search_history_request
               if fnc == "ask_to_read_link":
                   trigger_function[fnc] = read_link_request
               if fnc == "ask_to_wait":
                   trigger_function[fnc] = wait_words
               if fnc == "ask_for_name":
                   trigger_function[fnc] = trinity_name
               if fnc == "ask_for_mean":
                   trigger_function[fnc] = trinity_mean
               if fnc == "ask_for_creator":
                   trigger_function[fnc] = trinity_creator
               if fnc == "ask_for_help":
                   trigger_function[fnc] = trinity_help
               if fnc == "ask_for_prompt":
                   trigger_function[fnc] = prompt_request
               if fnc == "ask_for_rnd":
                   trigger_function[fnc] = rnd_request
               if fnc == "ask_for_repeat":
                   trigger_function[fnc] = repeat_request
               if fnc == "ask_to_add":
                   trigger_function[fnc] = add_words
               if fnc == "ask_to_wait":
                   trigger_function[fnc] = wait_words


               triggered_parts[fnc] = seeknreturn(txt,trigger_function[fnc])
#               bonus = bonuspoint(txt,action_functions,fnc)
               bonus = 0
               score_function[fnc] = len(triggered_parts[fnc]) + bonus



       sorted_score = dict(sorted(score_function.items(), key=lambda item: item[1], reverse=True))

       ordered_list = list(dict(sorted(score_function.items(), key=lambda item: item[1], reverse=True)).keys())


       winner = bestvalue(sorted_score,ordered_list)

       if winner:

           print("\n-%s has the higher confidence score.\n"%winner)
           for _n,(fnc) in enumerate(ordered_list):
                print("\n-Commande name:%s\n-Triggered by %s parts:%s\n-Confidence score:%s"%(fnc,len(triggered_parts[fnc]),triggered_parts[fnc],score_function[fnc]))

           return(winner)
       print("\n\n===============\n\n-Cette phrase à déclenchée plusieurs commandes en même temps:")
       print("-Your sentence :",txt)


       Play_Audio_File(script_path+"/local_sounds/cmd/ambiguty.wav")
       while True:
           for n,(fnc) in enumerate(ordered_list):
                print("\n-Commande:%s\n-Déclenchée par %s parties:%s\n-Score de Confiance:%s"%(fnc,len(triggered_parts[fnc]),triggered_parts[fnc],score_function[fnc]))
                print("-Pour choisir cette commande tapez:",n)

                if n+1 == 1:
                    Play_Audio_File("%s/local_sounds/cmd/intro_%s.wav" % (script_path,fnc))
                elif n+1 > 1 and n+1 < len(ordered_list):
                    Play_Audio_File("%s/local_sounds/cmd/%s.wav" % (script_path,fnc))
                elif n+1 == len(ordered_list):
                    Play_Audio_File("%s/local_sounds/cmd/outro_%s.wav" % (script_path,fnc))


           print("\n-Si ce n'était pas une commande tapez:%s\n"%len(sorted_score))

           Play_Audio_File("%s/local_sounds/cmd/hit%s.wav" % (script_path,len(sorted_score)))


           response = input("\n-Choisissez la bonne réaction pour cette phrase:")
           try:
#           if 1 == 1 :
              response = int(response.strip())
              if response > len(sorted_score):
                   continue
              if response == len(sorted_score):
                   return("not a commande")
              func_name_toadd = ordered_list[response]
#                    print("\nfunc_name_toadd:",func_name_toadd)
              trigger_words_toadd = sorted_score[func_name_toadd]
#                    print("\ntrigger_words_toadd:",txt)
              must_contain = triggered_parts[ordered_list[response]]
              break
           except Exception as e:
                   print("\nerror:",e)
                   continue

       if func_name_toadd and trigger_words_toadd and must_contain:

            print("\n-La fonction %s à été choisie pour cette phrase.\n"%func_name_toadd)
            if action_trigger:
                 goto = postprod(txt,func_name_toadd,specific_trigger=must_contain,main_trigger=action_trigger)
            else:
                 goto = postprod(txt,func_name_toadd,specific_trigger=must_contain)
            if goto:
                   return(goto)
            return None
       if not func_name_toadd:
            print("-func_name_toadd is missing")
       if not trigger_words_toadd:
            print("-trigger_words_toadd is missing")
       if not must_contain:
            print("-must_contain is missing")
       return()

    def bonuspoint(txt,aflist,function_tomatch):

          bonus = 0
          bonusyn = 0
#          print("\n\n\n")
#          print("synlist:",synlist)
#          print()
#          print("fnlist:",fnlist)
#          print("function_tomatch:",function_tomatch)
#          print("\n\n\n")
          for af in aflist:
               act = af[0]
               fn = af[1]

               if act in txt and fn == function_tomatch:
#                    print("Bonus point +1 %s in txt and %s is matching %s"%(act,fn,function_tomatch))
                    bonus += 1

                    for syn in synonyms_list:
          #              print(syn)
                        for s in syn:
                            if s in txt:
                               for newsyn in syn:

                                   newtxt = txt.replace(s,newsyn)

                                   if function_tomatch == "ask_for_web":
                                       bonusyn = len(seeknreturn(newtxt,web_request))
                                   if function_tomatch == "ask_to_play_wav":
                                       bonusyn = len(seeknreturn(newtxt,play_wav_request))
                                   if function_tomatch == "ask_for_history":
                                       bonusyn = len(seeknreturn(newtxt,search_history_request))
                                   if function_tomatch == "ask_to_read_link":
                                       bonusyn = len(seeknreturn(newtxt,read_link_request))
                                   if function_tomatch == "ask_to_wait":
                                       bonusyn = len(seeknreturn(newtxt,wait_words))
                                   if function_tomatch == "ask_for_name":
                                       bonusyn = len(seeknreturn(newtxt,trinity_name))
                                   if function_tomatch == "ask_for_mean":
                                       bonusyn = len(seeknreturn(newtxt,trinity_mean))
                                   if function_tomatch == "ask_for_creator":
                                       bonusyn = len(seeknreturn(newtxt,trinity_creator))
                                   if function_tomatch == "ask_for_help":
                                       bonusyn = len(seeknreturn(newtxt,trinity_help))
                                   if function_tomatch == "ask_for_prompt":
                                       bonusyn = len(seeknreturn(newtxt,prompt_request))
                                   if function_tomatch == "ask_for_rnd":
                                       bonusyn = len(seeknreturn(newtxt,rnd_request))
                                   if function_tomatch == "ask_for_repeat":
                                       bonusyn = len(seeknreturn(newtxt,repeat_request))

                                   bonusyn += len(seeknreturn(newtxt,alt_trigger))

#                                   print("Replace Bonus point +1 %s in txt"%(newsyn))
                                   bonus += bonusyn

          return(bonus)


    def bestvalue(dictionary,ordered):
	         if not dictionary:
	             return(False)
	         values = [dictionary[key] for key in ordered]
	         max_value = max(values)
	         count_max_value = values.count(max_value)
	         if count_max_value == 1:
	             return(ordered[values.index(max_value)])
	         return(False)



    def seeknreturn2(var_to_check,list_elements):
          found_lst = []
          for element in list_elements:
               if "*" in element:
                   splited = element.split("*")
                   print("splited:",splited)
                   good = True
                   for item in splited:
                      print("item:",item)
                      if item in var_to_check:
                           print("item %s in var_to_check"%item)
                      else:
                           good = False

                   all_inside = good
                   if all_inside:
                       print("splitted in history:",element)
#                      for s in splited:
#                          found_lst.append(s
                       found_lst.append(element)
                   else:
                        print("nul\n\n\n")
                        continue
               if element in var_to_check:
                    print("element in history,",element)
                    found_lst.append(element)
          return(found_lst)



    def seeknreturn(var_to_check,list_elements):
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
          return(found_lst)


    def seekndestroy(list_elements, var_to_check):

          for element in list_elements:
              if element in var_to_check:
                  print("-Detroying :",element)
                  var_to_check = var_to_check.replace(element," ")
          return(var_to_check.replace("  "," "))

    decoded = unidecode(txt.lower())

    ambiguity = []

    filter = ["s'il te plait","si te plait","sil te plait","merci"]





    ask_to_action = seeknreturn(decoded,action_words)

    ask_to_add = seeknreturn(decoded,add_words)

    ask_for_name = seeknreturn(decoded,trinity_name)

    ask_for_mean = seeknreturn(decoded,trinity_mean)

    ask_for_creator = seeknreturn(decoded,trinity_creator)

    ask_for_help = seeknreturn(decoded,trinity_help)

    ask_for_prompt = seeknreturn(decoded,prompt_request)

    ask_for_rnd = seeknreturn(decoded,rnd_request)

    ask_for_repeat = seeknreturn(decoded,repeat_request)

    ask_for_history = seeknreturn(decoded,search_history_request)

    ask_for_web = seeknreturn(decoded,web_request)

    ask_to_read_link = seeknreturn(decoded,read_link_request)

    ask_to_play_wav = seeknreturn(decoded,play_wav_request)


    ask_to_wait = seeknreturn(decoded,wait_words)


    found_alt_trigger = seeknreturn(decoded,alt_trigger)


    decoded = seekndestroy(filter, decoded)

#    print("Cmd After filter:",decoded)


    if ask_to_action or found_alt_trigger:
#         print("Found ask_to_action match cmd :",ask_to_action)
#         print()
         ambiguity.append("ask_to_action")


         if ask_to_wait:
              ambiguity.append("ask_to_wait")
         if ask_for_name:
              ambiguity.append("ask_for_name")
#              print("Found ask_for_name cmd :",ask_for_name)
         if ask_for_mean:
              ambiguity.append("ask_for_mean")
#              print("Found ask_for_mean match cmd :",ask_for_mean)
         if ask_for_creator:
              ambiguity.append("ask_for_creator")
#              print("Found ask_for_mean match cmd :",ask_for_creator)
         if ask_for_rnd:
              ambiguity.append("ask_for_rnd")
         if ask_for_repeat:
              ambiguity.append("ask_for_repeat")
#              print("Found ask_for_repeat match cmd :",ask_for_repeat)
         if ask_for_prompt:
             ambiguity.append("ask_for_prompt")
#             print("Found ask_for_prompt match cmd :",ask_for_prompt)
         if ask_for_help:
             ambiguity.append("ask_for_help")
#             print("Found ask_for_help match cmd :",ask_for_help)
         if ask_to_play_wav:
             ambiguity.append("ask_to_play_wav")
#             print("Found ask_to_play_wav match cmd :",ask_to_play_wav)
         if ask_for_history:
                 ambiguity.append("ask_for_history")
#                 print("Found ask_for_history match cmd :",ask_for_history)
         if ask_to_read_link:
                 ambiguity.append("ask_to_read_link")
#                 print("Found ask_to_read_link match cmd :",ask_to_read_link)
         if ask_for_web:
                 ambiguity.append("ask_for_web")
#                 print("Found ask_for_web match cmd :",ask_for_web)

         if ask_to_add:
                 ambiguity.append("ask_to_add")
#                 print("Found ask_to_add match cmd :",ask_to_add)



    if len(ambiguity) > 1:
        goto = None
        #print("disambiguify:",ambiguity)
        if ask_to_action:
             goto = disambiguify(ask_to_action,ambiguity,decoded,ask_to_action)
        else:
             goto = disambiguify(ask_to_action,ambiguity,decoded)

        if goto:
            print("Going to function :",goto)
            print()
            if goto == "ask_to_add":
                Add_Trigger()
            if goto == "ask_for_web":
                Isolate_Search_Request(txt,ask_for_web)
            return(True)
    elif len(ambiguity) == 1:
        print("Ambiguity:",ambiguity)
        print("\n-No ambiguity")
        return(False)
    else:
        print("\n-No commande has been found.")
        return(False)
    return None



trinity_name = []
trinity_mean = []
trinity_creator = []
trinity_script = []
trinity_help = []
prompt_request = []
trinity_source_request = []
rnd_request = []
repeat_request = []
search_history_request = []
read_link_request = []
play_wav_request = []
web_request = []
wait_words = []
add_words = []
action_words = []
action_functions = []
alt_trigger = []
verb_lst = []
synonyms_list = []
fnc_verb = {}

ROOT_DIR = Path(__file__).resolve().parents[1]
script_path = str(ROOT_DIR)

CMDFILE = str(ROOT_DIR / "datas" / "cmd.trinity")
ALTFILE = str(ROOT_DIR / "datas" / "alt_cmd.trinity")
TRIFILE = str(ROOT_DIR / "datas" / "alt_trigger.trinity")
ACTFILE = str(ROOT_DIR / "datas" / "action.trinity")
PREFILE = str(ROOT_DIR / "datas" / "prefix.trinity")
SYNFILE = str(ROOT_DIR / "datas" / "synonym.trinity")


def main():
    if not Load_Csv():
        return 1
    print(script_path)
    #Commandes("Tu peux chercher surrender sur google s'il te plait merci")
    Commandes("Tu peux chercher sur google un truc sur surgoldorak s'il te plait merci")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
