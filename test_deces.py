import os

dossier = os.path.join("cache", "deces")
fichier = os.path.join(dossier, "deces-2026-m01.txt")

# On cherche une ligne où 51454 apparaît en fin de ligne
# car c'est le code commune de DECES
print("Recherche de lignes avec 51454 en position finale (décès à Reims)...")
print("="*70)

found = 0
with open(fichier, encoding="utf-8", errors="ignore") as f:
    for i, ligne in enumerate(f):
        ligne = ligne.rstrip()
        # Cherche 51454 n'importe où dans la ligne
        if "51454" in ligne:
            pos = ligne.find("51454")
            print(f"\nLigne {i+1} (pos {pos}) :")
            print(f"  {repr(ligne)}")
            # Affiche les 20 derniers caractères
            print(f"  Fin de ligne : {repr(ligne[-25:])}")
            found += 1
            if found >= 10:
                break

if found == 0:
    print("Aucune ligne avec 51454 trouvée dans les 10000 premières lignes")
    print("\nRecherche de 51573 (Tinqueux)...")
    with open(fichier, encoding="utf-8", errors="ignore") as f:
        for i, ligne in enumerate(f):
            ligne = ligne.rstrip()
            if "51573" in ligne or "51282" in ligne or "51391" in ligne:
                pos51 = -1
                for code in ["51573","51282","51391","51291","51183","51518","51444"]:
                    if code in ligne:
                        pos51 = ligne.find(code)
                        print(f"\nLigne {i+1} — code {code} à pos {pos51}:")
                        print(f"  {repr(ligne)}")
                        print(f"  Fin: {repr(ligne[-20:])}")
                        break
                found += 1
                if found >= 10:
                    break
