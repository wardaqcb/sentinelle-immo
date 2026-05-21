import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher

# ============================================
# SENTINELLE IMMO — Triple croisement
# DPE × DVF × MAJIC
# Lead béton : passoire thermique + non vendue + SCI identifiée
# ============================================

OUTPUT_DIR = "donnees"

def normaliser_adresse(adresse):
    if not adresse:
        return "", ""
    a = adresse.lower().strip()
    a = re.sub(r'\b5\d{4}\b', '', a)
    for ville in ["reims", "tinqueux", "gueux", "muizon", "hermonville", "courcy", "saint-thierry", "pouillon"]:
        a = re.sub(r'\b' + ville + r'\b', '', a)
    a = re.sub(r'\ball\b', 'allee', a)
    a = re.sub(r'\bav\b', 'avenue', a)
    a = re.sub(r'\bbd\b|\bbvd\b', 'boulevard', a)
    a = re.sub(r'\bpl\b', 'place', a)
    a = re.sub(r'\bimp\b', 'impasse', a)
    a = re.sub(r'\besp\b', 'esplanade', a)
    a = re.sub(r'\b0+(\d)', r'\1', a)
    a = re.sub(r'[^\w\s]', ' ', a)
    a = re.sub(r'\s+', ' ', a).strip()
    match = re.match(r'^(\d+)\s*(.*)', a)
    if match:
        return match.group(1), match.group(2).strip()
    return "", a

def croiser_triple():
    print("\n🔗 Triple croisement DPE × DVF × MAJIC...")

    # Charge les 3 sources
    for chemin in ["dpe_leads_propres.json", "leads_majic_dpe.json"]:
        if not os.path.exists(os.path.join(OUTPUT_DIR, chemin)):
            print(f"   ❌ {chemin} introuvable — lance d'abord les croisements précédents")
            return []

    with open(os.path.join(OUTPUT_DIR, "dpe_leads_propres.json"), encoding="utf-8") as f:
        dpe_dvf = json.load(f)
    with open(os.path.join(OUTPUT_DIR, "leads_majic_dpe.json"), encoding="utf-8") as f:
        majic_dpe = json.load(f)

    print(f"   → {len(dpe_dvf)} leads DPE × DVF (non vendus)")
    print(f"   → {len(majic_dpe)} leads MAJIC × DPE (SCI identifiées)")

    # Index des leads MAJIC × DPE par adresse normalisée
    print("   🔍 Indexation MAJIC × DPE...")
    majic_index = {}
    for m in majic_dpe:
        commune = m.get("commune", "").upper()
        adresse = m.get("adresse", "")
        num, rue = normaliser_adresse(adresse)
        cle = f"{commune}_{num}_{rue[:25]}"
        if cle not in majic_index:
            majic_index[cle] = []
        majic_index[cle].append(m)

    # Croisement
    leads_triple = []
    nb_croises = 0
    nb_non_croises = 0

    for d in dpe_dvf:
        commune = d.get("commune", "").upper()
        adresse = d.get("adresse", "")
        num, rue = normaliser_adresse(adresse)
        cle = f"{commune}_{num}_{rue[:25]}"

        candidats = majic_index.get(cle, [])

        if candidats:
            nb_croises += 1
            sirens_vus = set()
            for m in candidats:
                siren = m.get("sci_siren", "")
                if siren in sirens_vus:
                    continue
                if siren:
                    sirens_vus.add(siren)

                leads_triple.append({
                    "source": "DPE × DVF × MAJIC",
                    # Adresse
                    "adresse": adresse,
                    "commune": d.get("commune", ""),
                    # DPE
                    "etiquette_dpe": d.get("etiquette_dpe", ""),
                    "surface": d.get("surface", ""),
                    "type_batiment": d.get("type_batiment", ""),
                    "date_dpe": d.get("date_dpe", ""),
                    # DVF — confirmation non vendu
                    "statut_croisement": d.get("statut_croisement", "non_vendu"),
                    # MAJIC — propriétaire
                    "sci_denomination": m.get("sci_denomination", ""),
                    "sci_siren": siren,
                    "sci_forme_juridique": m.get("sci_forme_juridique", ""),
                    # Signal
                    "signal": f"Passoire {d.get('etiquette_dpe','')} · Non vendue · SCI propriétaire identifiée",
                    "pappers_url": f"https://pappers.fr/entreprise/{siren}" if siren else "",
                    "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                })
        else:
            nb_non_croises += 1

    leads_triple.sort(key=lambda x: (
        0 if x["etiquette_dpe"] == "G" else 1,
        x["date_dpe"]
    ))

    # Résumé
    print(f"\n   📊 Résultats :")
    print(f"   ✅ Leads triple croisement : {len(leads_triple)}")
    print(f"   ❌ DPE×DVF sans SCI MAJIC  : {nb_non_croises}")

    from collections import Counter
    communes = Counter([l["commune"] for l in leads_triple])
    print(f"\n   Par commune :")
    for c, nb in communes.most_common():
        print(f"   → {c} : {nb} leads")

    classes = Counter([l["etiquette_dpe"] for l in leads_triple])
    print(f"\n   Par classe DPE :")
    for c, nb in classes.most_common():
        print(f"   → Classe {c} : {nb} leads")

    # Sauvegarde
    with open(os.path.join(OUTPUT_DIR, "leads_triple.json"), "w", encoding="utf-8") as f:
        json.dump(leads_triple, f, ensure_ascii=False, indent=2)

    # Exemples top leads
    if leads_triple:
        print(f"\n   🎯 Top leads (G en priorité) :")
        for l in leads_triple[:8]:
            print(f"\n   → {l['adresse']}")
            print(f"      🏢 {l['sci_denomination']} · SIREN {l['sci_siren']}")
            print(f"      🔋 DPE {l['etiquette_dpe']} · {l['type_batiment']} · {l['surface']} m²")
            print(f"      🔗 {l['pappers_url']}")

    print(f"\n   💾 leads_triple.json → {len(leads_triple)} leads béton")
    return leads_triple


if __name__ == "__main__":
    print("="*52)
    print("🔗 SENTINELLE IMMO — Triple croisement DPE×DVF×MAJIC")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    croiser_triple()
