import os

dossier = os.path.join("cache", "deces")
fichier = os.path.join(dossier, "deces-2026-m01.txt")

print("Recherche de lignes contenant 51454...")
found = 0
with open(fichier, encoding="utf-8", errors="ignore") as f:
    for i, ligne in enumerate(f):
        if "51454" in ligne:
            ligne = ligne.rstrip()
            pos = ligne.find("51454")
            print(f"\nLigne {i+1} — '51454' trouvé à position {pos}")
            print(f"Contenu : {repr(ligne)}")
            print(f"Positions autour :")
            for p in range(max(0,pos-10), min(len(ligne), pos+20)):
                print(f"  [{p}] = {repr(ligne[p])}")
            found += 1
            if found >= 5:
                break

if found == 0:
    print("51454 pas trouvé dans m01 — essai sur t1...")
    fichier2 = os.path.join(dossier, "deces-2026-t1.txt")
    with open(fichier2, encoding="utf-8", errors="ignore") as f:
        for i, ligne in enumerate(f):
            if "51454" in ligne:
                ligne = ligne.rstrip()
                pos = ligne.find("51454")
                print(f"\nLigne {i+1} — '51454' à position {pos}")
                print(f"Contenu : {repr(ligne)}")
                found += 1
                if found >= 3:
                    break
