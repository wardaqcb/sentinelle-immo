import json
import os
from datetime import datetime

# ============================================
# SENTINELLE IMMO — Croisement BODACC × MAJIC
# BODACC (SCI en procédure) × MAJIC (adresse du bien)
# Clé de croisement : N° SIREN
# ============================================

OUTPUT_DIR = "donnees"

def croiser_bodacc_majic():
    print("\n🔗 Croisement BODACC × MAJIC...")

    # Charge BODACC
    bodacc_path = os.path.join(OUTPUT_DIR, "bodacc.json")
    majic_path  = os.path.join(OUTPUT_DIR, "majic.json")

    if not os.path.exists(bodacc_path):
        print("   ❌ bodacc.json introuvable")
        return []
    if not os.path.exists(majic_path):
        print("   ❌ majic.json introuvable")
        return []

    with open(bodacc_path, encoding="utf-8") as f:
        bodacc = json.load(f)
    with open(majic_path, encoding="utf-8") as f:
        majic = json.load(f)

    print(f"   → {len(bodacc)} annonces BODACC")
    print(f"   → {len(majic)} SCI propriétaires MAJIC")

    # Index MAJIC par SIREN
    majic_par_siren = {}
    for m in majic:
        siren = m.get("siren", "").strip()
        if siren:
            if siren not in majic_par_siren:
                majic_par_siren[siren] = []
            majic_par_siren[siren].append(m)

    print(f"   → {len(majic_par_siren)} SIREN uniques dans MAJIC")

    # Croisement par SIREN uniquement — fiable à 100%
    leads = []
    non_croises = []

    for a in bodacc:
        siren_bodacc = (a.get("siren", "") or "").strip()

        if not siren_bodacc:
            non_croises.append(a)
            continue

        biens_trouves = majic_par_siren.get(siren_bodacc, [])

        if biens_trouves:
            for bien in biens_trouves:
                leads.append({
                    "source_croisement": "BODACC × MAJIC",
                    "score": "exact_siren",
                    # BODACC
                    "bodacc_description": a.get("description", ""),
                    "bodacc_famille": a.get("famille", ""),
                    "bodacc_date": a.get("date", ""),
                    "bodacc_tribunal": a.get("tribunal", ""),
                    "bodacc_url": a.get("url", ""),
                    # MAJIC
                    "adresse": bien.get("adresse", ""),
                    "commune": bien.get("commune", ""),
                    "denomination_sci": bien.get("denomination", ""),
                    "siren": siren_bodacc,
                    "forme_juridique": bien.get("forme_juridique", ""),
                    "type_bien": bien.get("type_bien", ""),
                    "nature": bien.get("nature", ""),
                    "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                })
        else:
            non_croises.append(a)

    # Dédoublonne
    vus = set()
    leads_uniques = []
    for l in leads:
        cle = f"{l['bodacc_description']}_{l['adresse']}"
        if cle not in vus:
            vus.add(cle)
            leads_uniques.append(l)

    leads_uniques.sort(key=lambda x: (x["score"], x["commune"]))

    print(f"\n   📊 Résultats :")
    print(f"   ✅ Leads croisés BODACC × MAJIC : {len(leads_uniques)}")
    print(f"   ❌ BODACC sans correspondance MAJIC : {len(non_croises)}")

    # Sauvegarde
    with open(os.path.join(OUTPUT_DIR, "leads_bodacc_majic.json"), "w", encoding="utf-8") as f:
        json.dump(leads_uniques, f, ensure_ascii=False, indent=2)

    # Affiche les leads
    if leads_uniques:
        print(f"\n   🎯 Leads détectés :")
        for l in leads_uniques[:10]:
            print(f"\n   → [{l['score'].upper()}] {l['denomination_sci']}")
            print(f"      📍 {l['adresse']}")
            print(f"      ⚖️  BODACC : {l['bodacc_famille']} | {l['bodacc_date']}")
            print(f"      🏠 Type : {l['type_bien']} | {l['nature']}")
            if l.get("siren"):
                print(f"      SIREN : {l['siren']}")

    print(f"\n   💾 leads_bodacc_majic.json → {len(leads_uniques)} leads")

    # Affiche aussi ce qu'on n'a pas croisé
    if non_croises:
        print(f"\n   📋 BODACC non croisés (pas dans MAJIC) :")
        for a in non_croises:
            print(f"   → {a.get('description','')} | {a.get('famille','')} | {a.get('date','')}")

    return leads_uniques


if __name__ == "__main__":
    print("="*52)
    print("🔗 SENTINELLE IMMO — Croisement BODACC × MAJIC")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    croiser_bodacc_majic()
