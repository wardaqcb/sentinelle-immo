import json
import re
import unicodedata
from collections import defaultdict, Counter
from datetime import datetime

DPE_PATH = "donnees/dpe.json"
SITADEL_PATH = "donnees/sitadel.json"
OUTPUT_PATH = "donnees/leads_sitadel_dpe.json"

ABBREV = {
    r"\bR\b": "RUE", r"\bAV\b": "AVENUE", r"\bAVE\b": "AVENUE",
    r"\bBD\b": "BOULEVARD", r"\bBLD\b": "BOULEVARD",
    r"\bPL\b": "PLACE", r"\bIMP\b": "IMPASSE", r"\bALL\b": "ALLEE",
    r"\bCHE\b": "CHEMIN", r"\bCH\b": "CHEMIN", r"\bRTE\b": "ROUTE",
    r"\bSQ\b": "SQUARE", r"\bQU\b": "QUAI", r"\bPAS\b": "PASSAGE",
    r"\bST\b": "SAINT", r"\bSTE\b": "SAINTE",
}

def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")

def normaliser_voie(texte):
    if not texte:
        return ""
    t = sans_accents(str(texte)).upper()
    t = re.sub(r"[^A-Z0-9 ]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    for pattern, remplacement in ABBREV.items():
        t = re.sub(pattern, remplacement, t)
    return re.sub(r"\s+", " ", t).strip()

def extraire_num_et_voie_dpe(adresse):
    if not adresse:
        return None, ""
    a = re.sub(r"\b\d{5}\b.*$", "", adresse).strip()
    m = re.match(r"^(\d+)\s+(.*)$", a)
    if m:
        return m.group(1), normaliser_voie(m.group(2))
    return None, normaliser_voie(a)

# Sous-type de signal selon le type de permis
def signal_depuis_permis(p):
    fichier = p.get("_SOURCE_FICHIER")
    if fichier == "demolir":
        return "demolition"        # le bien va disparaître → terrain qui se libère
    if fichier == "amenager":
        return "division"          # division parcellaire / lotissement
    if fichier == "logements":
        # transformation ou extension = rénovation lourde
        return "renovation"
    if fichier == "locaux":
        return "locaux_non_resid"
    return "autre"

# === Chargement ===
with open(DPE_PATH, encoding="utf-8") as f:
    dpe_list = json.load(f)
with open(SITADEL_PATH, encoding="utf-8") as f:
    permis_list = json.load(f)["permis"]

print(f"DPE chargés    : {len(dpe_list)}")
print(f"Permis chargés : {len(permis_list)}\n")

# === Index DPE strict : (insee, num, voie_normalisee) ===
dpe_index = defaultdict(list)
for d in dpe_list:
    insee = str(d.get("code_insee", "")).strip()
    num, voie = extraire_num_et_voie_dpe(d.get("adresse", ""))
    if insee and num:
        dpe_index[(insee, num, voie)].append(d)

# === Croisement strict ===
# Une passoire peut matcher plusieurs permis → on regroupe les permis par DPE
permis_par_dpe = defaultdict(list)

for p in permis_list:
    insee = str(p.get("COMM", "")).strip()
    num = str(p.get("ADR_NUM_TER", "")).strip()
    voie = normaliser_voie(p.get("ADR_LIBVOIE_TER", ""))
    if not insee or not num:
        continue
    cle = (insee, num, voie)
    if cle in dpe_index:
        for d in dpe_index[cle]:
            permis_par_dpe[d["numero_dpe"]].append(p)

# === Construction des leads enrichis ===
leads = []
for d in dpe_list:
    permis = permis_par_dpe.get(d.get("numero_dpe"), [])
    if not permis:
        continue  # on ne garde que les passoires AVEC permis dans ce fichier dérivé

    # Résumé des permis liés à cette passoire
    permis_resume = []
    for p in permis:
        permis_resume.append({
            "type_fichier": p.get("_SOURCE_FICHIER"),
            "signal": signal_depuis_permis(p),
            "date_autorisation": p.get("DATE_REELLE_AUTORISATION"),
            "date_depot": p.get("DR_DEPOT"),
            "demandeur": p.get("DENOM_DEM"),
            "siren": p.get("SIREN_DEM"),
            "localite_demandeur": p.get("LOCALITE_DEM"),
            "demandeur_hors_commune": bool(
                p.get("LOCALITE_DEM") and p.get("ADR_LOCALITE_TER")
                and p["LOCALITE_DEM"].strip().upper() != p["ADR_LOCALITE_TER"].strip().upper()
            ),
            "num_dau": p.get("NUM_DAU") or p.get("NUM_PD") or p.get("NUM_PA"),
        })

    # Signaux agrégés au niveau du lead
    signaux = set(pr["signal"] for pr in permis_resume)
    a_siren = any(pr["siren"] for pr in permis_resume)
    hors_commune = any(pr["demandeur_hors_commune"] for pr in permis_resume)

    lead = dict(d)  # on copie toute la donnée DPE d'origine
    lead["permis_sitadel"] = {
        "nb_permis": len(permis_resume),
        "signaux": sorted(signaux),
        "a_siren_demandeur": a_siren,
        "demandeur_hors_commune": hors_commune,
        "details": permis_resume,
    }
    leads.append(lead)

# === Statistiques ===
print("=" * 60)
print(f"PASSOIRES AVEC PERMIS SITADEL : {len(leads)}")
print("=" * 60)

print("\n--- Répartition par signal (une passoire peut en avoir plusieurs) ---")
compte_signaux = Counter()
for l in leads:
    for s in l["permis_sitadel"]["signaux"]:
        compte_signaux[s] += 1
for s, nb in compte_signaux.most_common():
    print(f"  {s:18s} : {nb}")

print("\n--- Croisements à fort potentiel ---")
demol = [l for l in leads if "demolition" in l["permis_sitadel"]["signaux"]]
print(f"  Passoires avec permis de DÉMOLIR (terrain se libère) : {len(demol)}")
divis = [l for l in leads if "division" in l["permis_sitadel"]["signaux"]]
print(f"  Passoires avec permis d'AMÉNAGER (division)          : {len(divis)}")
avec_siren = [l for l in leads if l["permis_sitadel"]["a_siren_demandeur"]]
print(f"  Passoires dont le demandeur a un SIREN (→ MAJIC)      : {len(avec_siren)}")
hors = [l for l in leads if l["permis_sitadel"]["demandeur_hors_commune"]]
print(f"  Passoires dont le demandeur est hors commune          : {len(hors)}")

print("\n--- Répartition par étiquette DPE ---")
for et, nb in Counter(l.get("etiquette_dpe") for l in leads).most_common():
    print(f"  {et} : {nb}")

# === Sauvegarde ===
sortie = {
    "_meta": {
        "description": "Passoires DPE (F/G) croisées avec un permis Sitadel sur la même adresse (matching strict)",
        "date_croisement": datetime.now().isoformat(timespec="seconds"),
        "nb_leads": len(leads),
        "methode": "matching strict adresse (code_insee + numero + voie normalisee)",
    },
    "leads": leads,
}
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(sortie, f, ensure_ascii=False, indent=2)

import os
print(f"\n✓ Sauvegardé dans {OUTPUT_PATH} ({os.path.getsize(OUTPUT_PATH)/1024:.0f} Ko)")