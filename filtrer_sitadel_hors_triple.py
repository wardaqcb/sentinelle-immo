import json
import unicodedata
import re
import os
from datetime import datetime

TRIPLE_PATH      = "donnees/leads_triple.json"
SITADEL_DPE_PATH = "donnees/leads_sitadel_dpe.json"
OUTPUT_PATH      = "donnees/leads_sitadel_dpe_hors_triple.json"

def normaliser(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.upper().strip())

# === Chargement ===
triple        = json.load(open(TRIPLE_PATH,      encoding="utf-8"))
sitadel_leads = json.load(open(SITADEL_DPE_PATH, encoding="utf-8"))["leads"]

print(f"Triple chargés       : {len(triple)}")
print(f"Sit@del×DPE chargés  : {len(sitadel_leads)}\n")

# === Index des adresses Triple ===
triple_adresses = set(normaliser(l.get("adresse", "")) for l in triple)
print(f"Adresses uniques Triple : {len(triple_adresses)}")

# === Filtrage : on garde uniquement les Sit@del hors Triple ===
hors_triple = [
    l for l in sitadel_leads
    if normaliser(l.get("adresse", "")) not in triple_adresses
]

print(f"Sit@del×DPE hors Triple : {len(hors_triple)} / {len(sitadel_leads)}\n")

# === Stats sur le résultat ===
from collections import Counter
signaux = Counter()
for l in hors_triple:
    for s in l.get("permis_sitadel", {}).get("signaux", []):
        signaux[s] += 1

print("--- Répartition par signal ---")
for s, nb in signaux.most_common():
    print(f"  {s:20s} : {nb}")

print("\n--- Répartition par étiquette DPE ---")
for et, nb in Counter(l.get("etiquette_dpe") for l in hors_triple).most_common():
    print(f"  {et} : {nb}")

# === Sauvegarde ===
sortie = {
    "_meta": {
        "description": "Passoires DPE avec permis Sit@del, hors leads Triple (pas de SCI identifiée)",
        "date_filtrage": datetime.now().isoformat(timespec="seconds"),
        "nb_leads": len(hors_triple),
    },
    "leads": hors_triple,
}
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(sortie, f, ensure_ascii=False, indent=2)

print(f"\n✓ {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)/1024:.0f} Ko)")