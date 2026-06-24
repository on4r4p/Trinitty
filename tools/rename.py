import os


this = "__"


def main():
    wav_files = [f for f in os.listdir(".") if f.endswith(".wav")]
    #to_rm = [" ","_","-","*","'"]

    for w in wav_files:
        newname = w.replace("__","_")
        while True:
    #        if newname[0] in to_rm:
    #            newname = newname[1:]
    #        else:
    #            break

             if "__" in newname:
                 newname = newname.replace("__","_")
             else:
                  break

        print("%s renaming to :%s"%(w,newname))
        os.rename(w,newname)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
