import requests
def Check_Free_Servers():

     active_with_auth = []
     active_no_auth = []
     unknown_with_auth = []
     unknown_no_auth = []
     all = []

     try:

         response = requests.get("https://raw.githubusercontent.com/xtekky/gpt4free/main/README.md", timeout=10)
         markdown = response.text.splitlines()
         print("\n\n")
         for line in markdown:
              if "g4f.Provider." in line:
                    if "https://img.shields.io/badge/Active-brightgreen" in line:
                        provider =  "g4f.Provider." + line.split("g4f.Provider.")[1].split("`")[0]
                        if "❌" in line:
                            active_no_auth.append(provider)
                        else:
                            active_with_auth.append(provider)
                    if "https://img.shields.io/badge/Unknown-grey" in line:
                        provider =  "g4f.Provider." + line.split("g4f.Provider.")[1].split("`")[0]
                        if "❌" in line:
                            unknown_no_auth.append(provider)
                        else:
                            unknown_with_auth.append(provider)
                    if "https://img" in line:
                         all.append(line.split("g4f.Provider.")[1].split("`")[0])

     except Exception as e:
         print("Error:",str(e))

     if active_with_auth:
           active_with_auth.sort()
           print("\nactive_with_auth:\n")
           for aa in active_with_auth:
                print(aa)
     if active_no_auth:
           active_no_auth.sort()
           print("\nactive_no_auth:\n")
           for an in active_no_auth:
                print(an)

     if unknown_with_auth:
           unknown_with_auth.sort()
           print("\nunknown_with_auth:\n")
           for ua in unknown_with_auth:
                print(ua)
     if unknown_no_auth:
           unknown_no_auth.sort()
           print("\nunknown_no_auth:\n")
           for un in unknown_no_auth:
                print(un)

     print("\nall:\n")
     all.sort()
     for a in all:
         print('"%s",'%a)
def main():
    Check_Free_Servers()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
