import requests
import json
import os
import csv
import io
import zipfile
from datetime import datetime

# ============================================
# SENTINELLE IMMO — Collecteur de données v6
# ============================================

COMMUNES = {
    "Reims":    "51454",
    "Tinqueux": "51572",
    "Gueux":    "51287",
    "Muizon":   "51392",
    "Fismes":   "51249",
}

OUTPUT_DIR = "donnees"
CACHE_DIR = "cache"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)

DVF_URL = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002321/valeursfoncieres-2025.txt.zip"
DVF_CACHE = os.path.join(CACHE_DIR, "valeursfoncieres-2025.zip")

# ============================================
# 1. DVF
# ============================================

def collecter_dvf():
    print("\n📊 Collecte des transactions DVF...")

    codes = set(COMMUNES.values())
    noms = {v: k for k, v in COMMUNES.items()}
    resultats = []

    if os.path.exists(DVF_CACHE):
        print(f"   ✅ Fichier en cache ({os.path.getsize(DVF_CACHE) // 1024 // 1024} Mo) — pas de re-téléchargement")
    else:
        print("   ⏳ Téléchargement du fichier national (1-2 min)...")
        try:
            r = requests.get(DVF_URL, timeout=120, stream=True)
            if r.status_code != 200:
                print(f"   ❌ Erreur : {r.status_code}")
                return []
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(DVF_CACHE, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded / total * 100)
                        print(f"   ⬇️  {pct}% ({downloaded // 1024 // 1024} Mo)", end="\r")
            print(f"\n   ✅ Téléchargement terminé")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            return []

    try:
        print("   📦 Extraction...")
        with zipfile.ZipFile(DVF_CACHE) as z:
            with z.open(z.namelist()[0]) as f:
                contenu = f.read().decode("utf-8", errors="ignore")

        print("   🔍 Filtrage sur tes communes...")
        reader = csv.DictReader(io.StringIO(contenu), delimiter="|")

        for row in reader:
            dept = row.get("Code departement", "").strip().zfill(2)
            commune = row.get("Code commune", "").strip().zfill(3)
            code_complet = dept + commune

            if code_complet in codes:
                try:
                    valeur = float(row.get("Valeur fonciere", "0").replace(",", ".").replace(" ", "") or "0")
                    surface = float(row.get("Surface reelle bati", "0").replace(",", ".").replace(" ", "") or "0")
                    type_local = row.get("Type local", "").strip()
                    prix_m2 = round(valeur / surface, 0) if surface > 0 else 0

                    # Filtres : bon type, surface réaliste, prix au m² réaliste (500 à 15000)
                    if (valeur > 0
                            and surface >= 15
                            and type_local in ["Maison", "Appartement"]
                            and 500 <= prix_m2 <= 15000):
                        resultats.append({
                            "commune": noms.get(code_complet, code_complet),
                            "code_insee": code_complet,
                            "date_mutation": row.get("Date mutation", ""),
                            "valeur_fonciere": valeur,
                            "surface_bati": surface,
                            "prix_m2": prix_m2,
                            "type_local": type_local,
                            "nombre_pieces": row.get("Nombre pieces principales", ""),
                            "adresse": row.get("No voie", "") + " " + row.get("Voie", ""),
                            "nature_mutation": row.get("Nature mutation", ""),
                        })
                except Exception:
                    continue

        resultats.sort(key=lambda x: x["date_mutation"], reverse=True)

        for nom in COMMUNES.keys():
            tc = [t for t in resultats if t["commune"] == nom]
            prix_m2 = [t["prix_m2"] for t in tc]
            moy = round(sum(prix_m2) / len(prix_m2), 0) if prix_m2 else 0
            print(f"   → {nom} : {len(tc)} transactions · {moy} €/m² moyen")

    except Exception as e:
        print(f"   ❌ Erreur lecture : {e}")
        return []

    fichier = os.path.join(OUTPUT_DIR, "dvf.json")
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    print(f"\n   💾 {len(resultats)} transactions sauvegardées")
    return resultats

# ============================================
# 2. BODACC
# ============================================

def collecter_bodacc():
    print("\n⚰️  Collecte des annonces BODACC...")
    resultats = []

    try:
        url = (
            "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/"
            "catalog/datasets/annonces-commerciales/records"
            "?where=tribunal%20like%20%27Reims%27"
            "&limit=50"
            "&order_by=dateparution%20desc"
        )
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            annonces = r.json().get("results", [])
            for a in annonces:
                resultats.append({
                    "type": a.get("familleavis_lib", ""),
                    "date": a.get("dateparution", ""),
                    "description": a.get("commercant", ""),
                    "tribunal": a.get("tribunal", ""),
                    "numero": a.get("numerodannonce", ""),
                })
            print(f"   ✅ {len(annonces)} annonces trouvées")
        else:
            print(f"   ⚠️ Erreur {r.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur : {e}")

    fichier = os.path.join(OUTPUT_DIR, "bodacc.json")
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    print(f"   💾 {len(resultats)} annonces sauvegardées")
    return resultats

# ============================================
# 3. STATS DE MARCHÉ
# ============================================

def calculer_stats(dvf):
    print("\n📈 Calcul des statistiques de marché...")
    stats = {}

    for commune in COMMUNES.keys():
        tc = [t for t in dvf if t["commune"] == commune]
        prix_m2 = [t["prix_m2"] for t in tc]
        maisons = [t for t in tc if t["type_local"] == "Maison"]
        apparts = [t for t in tc if t["type_local"] == "Appartement"]

        stats[commune] = {
            "nb_transactions": len(tc),
            "nb_maisons": len(maisons),
            "nb_appartements": len(apparts),
            "prix_m2_moyen": round(sum(prix_m2) / len(prix_m2), 0) if prix_m2 else 0,
            "prix_median": sorted(prix_m2)[len(prix_m2)//2] if prix_m2 else 0,
            "prix_m2_maisons": round(sum(t["prix_m2"] for t in maisons) / len(maisons), 0) if maisons else 0,
            "prix_m2_apparts": round(sum(t["prix_m2"] for t in apparts) / len(apparts), 0) if apparts else 0,
        }
        print(f"   → {commune} : {len(tc)} transactions · {stats[commune]['prix_m2_moyen']} €/m² moyen")

    fichier = os.path.join(OUTPUT_DIR, "stats.json")
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    return stats

# ============================================
# 4. RAPPORT
# ============================================

def generer_rapport(dvf, bodacc, stats):
    rapport = {
        "date_collecte": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "communes": list(COMMUNES.keys()),
        "stats": {"transactions_dvf": len(dvf), "annonces_bodacc": len(bodacc)},
        "marche": stats,
        "transactions_recentes": dvf[:20],
        "annonces_recentes": bodacc[:20],
    }
    with open(os.path.join(OUTPUT_DIR, "rapport.json"), "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*50}")
    print(f"✅ COLLECTE TERMINÉE — {rapport['date_collecte']}")
    print(f"{'='*50}")
    print(f"   📊 Transactions DVF   : {len(dvf)}")
    print(f"   ⚰️  Annonces BODACC    : {len(bodacc)}")
    print(f"   📁 Fichiers dans      : {OUTPUT_DIR}/")
    print(f"{'='*50}\n")

# ============================================
# LANCEMENT
# ============================================

if __name__ == "__main__":
    print("="*50)
    print("🏠 SENTINELLE IMMO — Collecteur v6")
    print(f"   Zone : Reims & environs (Marne 51)")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*50)

    dvf    = collecter_dvf()
    bodacc = collecter_bodacc()
    stats  = calculer_stats(dvf)
    generer_rapport(dvf, bodacc, stats)
