import json
import unicodedata
import re
import os
from collections import defaultdict, Counter
from datetime import datetime

TRIPLE_PATH      = "donnees/leads_triple.json"
SITADEL_DPE_PATH = "donnees/leads_sitadel_dpe.json"
OUTPUT_PATH      = "donnees/leads_triple_enrichi.json"

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

# === Index Sit@del×DPE par adresse normalisée ===
# Plusieurs leads Sit@del peuvent partager la même adresse (plusieurs unités)
# → on fusionne tous leurs permis sous la même clé
sitadel_index = defaultdict(list)
for lead in sitadel_leads:
    cle = normaliser(lead.get("adresse", ""))
    if cle:
        sitadel_index[cle].extend(lead.get("permis_sitadel", {}).get("details", []))

print(f"Adresses Sit@del indexées : {len(sitadel_index)}\n")

# === Enrichissement ===
enrichis = 0
leads_enrichis = []

for lead in triple:
    lead_enrichi = dict(lead)
    cle    = normaliser(lead.get("adresse", ""))
    permis = sitadel_index.get(cle, [])

    if permis:
        signaux = sorted(set(p["signal"] for p in permis))
        lead_enrichi["permis_sitadel"] = {
            "nb_permis"             : len(permis),
            "signaux"               : signaux,
            "a_siren_demandeur"     : any(p.get("siren") for p in permis),
            "demandeur_hors_commune": any(p.get("demandeur_hors_commune") for p in permis),
            "details"               : permis,
        }
        enrichis += 1

    leads_enrichis.append(lead_enrichi)

# === Stats ===
print("=" * 60)
print(f"LEADS TRIPLE AVEC PERMIS SITADEL : {enrichis} / {len(triple)}")
print("=" * 60)

signaux_count = Counter()
for lead in leads_enrichis:
    for s in lead.get("permis_sitadel", {}).get("signaux", []):
        signaux_count[s] += 1

if signaux_count:
    print("\n--- Répartition par signal (leads Triple enrichis) ---")
    for s, nb in signaux_count.most_common():
        print(f"  {s:20s} : {nb}")

# Leads Triple avec démolition = signal maximal
demol = [l for l in leads_enrichis if "demolition" in l.get("permis_sitadel", {}).get("signaux", [])]
print(f"\nLeads Triple avec DEMOLITION : {len(demol)}")

# === Sauvegarde ===
# Même structure liste directe que leads_triple.json — rétrocompatible
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(leads_enrichis, f, ensure_ascii=False, indent=2)

print(f"\n✓ {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)/1024:.0f} Ko)")