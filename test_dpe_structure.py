import json

DPE_PATH = "donnees/dpe.json"

with open(DPE_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Gérer les deux cas : liste directe ou dict avec clé
if isinstance(data, dict):
    print(f"Clés racine du fichier : {list(data.keys())}")
    # Chercher la liste des DPE
    for k, v in data.items():
        if isinstance(v, list) and v:
            dpe_list = v
            print(f"  → liste trouvée sous la clé '{k}' ({len(v)} éléments)")
            break
    else:
        dpe_list = []
else:
    dpe_list = data
    print(f"Fichier = liste directe de {len(data)} éléments")

if dpe_list:
    print(f"\n--- Champs disponibles dans un DPE ---")
    premier = dpe_list[0]
    for cle in sorted(premier.keys()):
        valeur = premier[cle]
        apercu = str(valeur)[:50]
        print(f"  {cle:40s} = {apercu}")

    # Repérer les champs susceptibles de contenir une parcelle ou un code commune
    print(f"\n--- Champs potentiellement utiles pour le croisement ---")
    mots_cles = ["parcelle", "cadastr", "commune", "insee", "ban", "section", "adresse", "code"]
    for cle in premier.keys():
        if any(mot in cle.lower() for mot in mots_cles):
            print(f"  {cle} = {str(premier[cle])[:60]}")