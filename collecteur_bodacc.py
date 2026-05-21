import requests
import json
import re
import os
from datetime import datetime
from collections import Counter

OUTPUT_DIR     = "donnees"
HISTORIQUE_DIR = "historique"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORIQUE_DIR, exist_ok=True)

BASE = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

# Familles exclues — pas actionnables pour l'immobilier
FAMILLES_EXCLUES = ["modif", "creation", "radiation", "immatricul"]

# Familles incluses — actionnables
FAMILLES_INCLUSES = ["liquid", "redress", "proc", "collectif", "vente", "cession", "success"]

def extraire_adresse(a):
    try:
        etabs = a.get("listeetablissements", "")
        if isinstance(etabs, str) and etabs:
            etabs = json.loads(etabs)
        if isinstance(etabs, dict):
            etab = etabs.get("etablissement", etabs)
            if isinstance(etab, list):
                etab = etab[0]
            adr = etab.get("adresse", {})
            if adr:
                num = adr.get("numeroVoie", "")
                type_voie = adr.get("typeVoie", "")
                nom_voie = adr.get("nomVoie", "")
                cp = adr.get("codePostal", "")
                ville = adr.get("ville", "")
                return f"{num} {type_voie} {nom_voie} {cp} {ville}".strip()
    except:
        pass
    return ""

def extraire_activite(a):
    try:
        etabs = a.get("listeetablissements", "")
        if isinstance(etabs, str) and etabs:
            etabs = json.loads(etabs)
        if isinstance(etabs, dict):
            etab = etabs.get("etablissement", etabs)
            if isinstance(etab, list):
                etab = etab[0]
            return etab.get("activite", "")
    except:
        pass
    return ""

def extraire_prix(a):
    try:
        etabs = a.get("listeetablissements", "")
        if isinstance(etabs, str) and etabs:
            etabs = json.loads(etabs)
        if isinstance(etabs, dict):
            etab = etabs.get("etablissement", etabs)
            if isinstance(etab, list):
                etab = etab[0]
            origine = etab.get("origineFonds", "")
            match = re.search(r'(\d[\d\s]*)\s*EUR', origine)
            if match:
                return int(match.group(1).replace(" ", ""))
    except:
        pass
    return None

def est_sci(desc):
    desc = desc.lower().strip()
    return (
        desc.startswith("sci ") or
        desc.startswith("s.c.i") or
        " sci " in desc or
        "societe civile immo" in desc or
        "société civile immo" in desc
    )

def collecter_bodacc():
    print("\n⚖️  Collecte BODACC v2...")
    toutes = []

    # Requêtes filtrées directement dans l'API — pas de téléchargement inutile
    REQUETES = [
        {
            "label": "Procédures collectives",
            "where": "tribunal like 'Reims' and dateparution >= '2024-01-01' and familleavis_lib like 'Procédures collectives'",
        },
        {
            "label": "Ventes et cessions SCI",
            "where": "tribunal like 'Reims' and dateparution >= '2024-01-01' and familleavis_lib like 'Ventes et cessions' and (commercant like 'SCI' or commercant like 'societe civile' or commercant like 'société civile')",
        },
    ]

    for req in REQUETES:
        print(f"\n   📋 {req['label']}...")
        offset = 0
        while True:
            try:
                r = requests.get(BASE, params={
                    "where": req["where"],
                    "limit": 100,
                    "offset": offset,
                    "order_by": "dateparution desc",
                }, timeout=15)

                if r.status_code != 200:
                    print(f"   ⚠️ Erreur {r.status_code}")
                    break

                data = r.json()
                annonces = data.get("results", [])
                total = data.get("total_count", 0)

                if offset == 0:
                    print(f"   → {total} annonces trouvées")

                for a in annonces:
                    registre = a.get("registre", [])
                    siren = ""
                    if isinstance(registre, list):
                        for reg in registre:
                            reg = str(reg).replace(" ", "").strip()
                            if len(reg) == 9 and reg.isdigit():
                                siren = reg
                                break
                    elif isinstance(registre, str):
                        siren = registre.replace(" ", "").strip()[:9]

                    toutes.append({
                        "id": a.get("id", ""),
                        "numero": a.get("numeroannonce", ""),
                        "famille": a.get("familleavis_lib", ""),
                        "type": a.get("typeavis_lib", ""),
                        "date": a.get("dateparution", ""),
                        "description": a.get("commercant", ""),
                        "tribunal": a.get("tribunal", ""),
                        "ville": a.get("ville", ""),
                        "cp": a.get("cp", ""),
                        "adresse": extraire_adresse(a),
                        "activite": extraire_activite(a),
                        "prix_cession": extraire_prix(a),
                        "siren": siren,
                        "url": a.get("url_complete", ""),
                    })

                offset += 100
                print(f"   ⏳ {min(offset, total)}/{total}", end="\r")

                if offset >= total or not annonces:
                    break

            except Exception as e:
                print(f"   ❌ {e}")
                break

    print(f"\n   → {len(toutes)} annonces récupérées au total")

    # Filtre strict et final
    resultats = []
    for a in toutes:
        famille = (a.get("famille", "") or "").lower()
        desc = (a.get("description", "") or "")
        prix = a.get("prix_cession") or 0
        sci = est_sci(desc)

        # Exclut toujours ces familles
        if any(mot in famille for mot in ["modif", "créat", "creat", "radiation", "immatricul"]):
            continue

        # Liquidations et redressements → tout garder
        if any(mot in famille for mot in ["liquid", "redress"]):
            resultats.append(a)
            continue

        # Procédures collectives → uniquement si SCI
        if "proc" in famille or "collectif" in famille:
            if sci:
                resultats.append(a)
            continue

        # Ventes et cessions → uniquement si SCI ou prix > 10 000 €
        if "vente" in famille or "cession" in famille:
            if sci or prix > 10000:
                resultats.append(a)
            continue

    resultats.sort(key=lambda x: x.get("date", ""), reverse=True)

    print(f"   ✅ {len(resultats)} annonces actionnables")

    # Résumé par famille
    familles = Counter([a.get("famille", "?") for a in resultats])
    for f, nb in familles.most_common():
        print(f"   → {f} : {nb}")

    # Détection nouveautés
    hist_path = os.path.join(HISTORIQUE_DIR, "bodacc_vus.json")
    historique = {}
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            historique = json.load(f)

    nouveaux = []
    for a in resultats:
        cle = a.get("id", "") or str(a.get("numero", ""))
        if cle and cle not in historique:
            nouveaux.append(a)
            historique[cle] = {
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                "description": a.get("description", ""),
                "famille": a.get("famille", ""),
            }

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "bodacc.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "bodacc_nouveaux.json"), "w", encoding="utf-8") as f:
        json.dump(nouveaux, f, ensure_ascii=False, indent=2)

    # Exemples
    print(f"\n   📋 Exemples :")
    for a in resultats[:8]:
        print(f"   → [{a['famille']}] {a['description']} | {a['date']}")
        if a.get("adresse"):
            print(f"      📍 {a['adresse']}")
        if a.get("prix_cession"):
            print(f"      💰 {a['prix_cession']:,} €")

    print(f"\n   💾 {len(resultats)} annonces · {len(nouveaux)} nouvelles")
    return resultats, nouveaux


if __name__ == "__main__":
    print("="*52)
    print("⚖️  SENTINELLE IMMO — Collecteur BODACC v2")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    collecter_bodacc()
