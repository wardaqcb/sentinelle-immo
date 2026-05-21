import json
import os
import re
from datetime import datetime
from difflib import SequenceMatcher

# ============================================
# SENTINELLE IMMO — Croisement MAJIC × DPE
# SCI propriétaires de passoires thermiques F/G
# Clé de croisement : adresse normalisée
# ============================================

OUTPUT_DIR = "donnees"

def normaliser_adresse(adresse):
    """Normalise une adresse pour comparaison."""
    if not adresse:
        return "", ""
    a = adresse.lower().strip()
    # Supprime codes postaux
    a = re.sub(r'\b5\d{4}\b', '', a)
    # Supprime noms de communes
    for ville in ["reims", "tinqueux", "gueux", "muizon", "hermonville", "courcy", "saint-thierry", "pouillon"]:
        a = re.sub(r'\b' + ville + r'\b', '', a)
    # Normalise les abréviations de voies
    a = re.sub(r'\ball\b', 'allee', a)
    a = re.sub(r'\bav\b', 'avenue', a)
    a = re.sub(r'\bbd\b|\bbvd\b', 'boulevard', a)
    a = re.sub(r'\bpl\b', 'place', a)
    a = re.sub(r'\bimp\b', 'impasse', a)
    a = re.sub(r'\besp\b', 'esplanade', a)
    # Supprime les zéros de début (0015 -> 15)
    a = re.sub(r'\b0+(\d)', r'\1', a)
    # Supprime caractères spéciaux
    a = re.sub(r'[^\w\s]', ' ', a)
    a = re.sub(r'\s+', ' ', a).strip()

    # Extrait le numéro de rue
    match = re.match(r'^(\d+)\s*(.*)', a)
    if match:
        return match.group(1), match.group(2).strip()
    return "", a

def similarite(a, b):
    return SequenceMatcher(None, a, b).ratio()

def croiser_majic_dpe():
    print("\n🔗 Croisement MAJIC × DPE...")

    majic_path = os.path.join(OUTPUT_DIR, "majic.json")
    dpe_path   = os.path.join(OUTPUT_DIR, "dpe.json")

    if not os.path.exists(majic_path):
        print("   ❌ majic.json introuvable")
        return []
    if not os.path.exists(dpe_path):
        print("   ❌ dpe.json introuvable")
        return []

    with open(majic_path, encoding="utf-8") as f:
        majic = json.load(f)
    with open(dpe_path, encoding="utf-8") as f:
        dpe = json.load(f)

    print(f"   → {len(majic)} SCI MAJIC")
    print(f"   → {len(dpe)} passoires DPE F/G")

    # Index MAJIC par commune + numéro + rue normalisée
    print("   🔍 Indexation MAJIC...")
    majic_index = {}
    for m in majic:
        commune = m.get("commune", "").upper()
        adresse = m.get("adresse", "")
        num, rue = normaliser_adresse(adresse)
        if not rue:
            continue
        cle = f"{commune}_{num}_{rue[:20]}"
        if cle not in majic_index:
            majic_index[cle] = []
        majic_index[cle].append(m)

        # Index aussi sans numéro pour les cas sans numéro
        cle2 = f"{commune}_{rue[:20]}"
        if cle2 not in majic_index:
            majic_index[cle2] = []
        majic_index[cle2].append(m)

    print(f"   ✅ {len(majic_index)} entrées dans l'index MAJIC")

    # Croisement
    leads = []
    nb_croises = 0
    nb_non_croises = 0

    for d in dpe:
        commune_dpe = d.get("commune", "").upper()
        adresse_dpe = d.get("adresse", "")
        num_dpe, rue_dpe = normaliser_adresse(adresse_dpe)

        if not rue_dpe:
            nb_non_croises += 1
            continue

        # Cherche dans l'index MAJIC
        cle_exacte = f"{commune_dpe}_{num_dpe}_{rue_dpe[:20]}"
        candidats = majic_index.get(cle_exacte, [])

        # Si pas trouvé, essaie sans numéro
        if not candidats:
            cle_sans_num = f"{commune_dpe}_{rue_dpe[:20]}"
            candidats_sans_num = majic_index.get(cle_sans_num, [])
            # Filtre sur le numéro si disponible
            if num_dpe:
                candidats = [c for c in candidats_sans_num
                            if normaliser_adresse(c.get("adresse",""))[0] == num_dpe]
            else:
                candidats = candidats_sans_num

        # Dédoublonne les candidats par SIREN
        sirens_vus = set()
        candidats_uniques = []
        for c in candidats:
            siren = c.get("siren", "")
            if siren and siren not in sirens_vus:
                sirens_vus.add(siren)
                candidats_uniques.append(c)
            elif not siren:
                candidats_uniques.append(c)

        if candidats_uniques:
            nb_croises += 1
            for m in candidats_uniques:
                leads.append({
                    "source_croisement": "MAJIC × DPE",
                    # DPE
                    "adresse": adresse_dpe,
                    "commune": d.get("commune", ""),
                    "etiquette_dpe": d.get("etiquette_dpe", ""),
                    "etiquette_ges": d.get("etiquette_ges", ""),
                    "surface": d.get("surface", ""),
                    "type_batiment": d.get("type_batiment", ""),
                    "date_dpe": d.get("date_dpe", ""),
                    # MAJIC
                    "sci_denomination": m.get("denomination", ""),
                    "sci_siren": m.get("siren", ""),
                    "sci_forme_juridique": m.get("forme_juridique", ""),
                    "sci_type_bien": m.get("type_bien", ""),
                    "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                    # Signal
                    "signal": f"SCI propriétaire d'une passoire {d.get('etiquette_dpe','')} — sous pression légale",
                })
        else:
            nb_non_croises += 1

    print(f"\n   📊 Résultats :")
    print(f"   ✅ DPE avec SCI propriétaire identifiée : {nb_croises}")
    print(f"   ❌ DPE sans correspondance MAJIC        : {nb_non_croises}")
    print(f"   📦 Total leads générés                 : {len(leads)}")

    # Résumé par commune
    from collections import Counter
    communes = Counter([l["commune"] for l in leads])
    print(f"\n   Par commune :")
    for c, nb in communes.most_common():
        print(f"   → {c} : {nb} leads")

    # Sauvegarde
    with open(os.path.join(OUTPUT_DIR, "leads_majic_dpe.json"), "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)

    # Exemples
    if leads:
        print(f"\n   🎯 Exemples de leads :")
        # Priorise les G
        top = sorted(leads, key=lambda x: (0 if x["etiquette_dpe"] == "G" else 1, x["date_dpe"]))
        for l in top[:8]:
            print(f"\n   → {l['adresse']}")
            print(f"      🏢 SCI : {l['sci_denomination']} (SIREN : {l['sci_siren']})")
            print(f"      🔋 DPE : {l['etiquette_dpe']} | {l['type_batiment']} | {l['surface']} m²")
            print(f"      📅 DPE établi le : {l['date_dpe']}")

    print(f"\n   💾 leads_majic_dpe.json → {len(leads)} leads")
    return leads


if __name__ == "__main__":
    print("="*52)
    print("🔗 SENTINELLE IMMO — Croisement MAJIC × DPE")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    croiser_majic_dpe()
