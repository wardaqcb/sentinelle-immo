import requests
import json
import os
import csv
import io

# ============================================
# SENTINELLE IMMO — Collecteur LOVAC v3
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

LOVAC_CACHE = os.path.join(CACHE_DIR, "lovac_communes.csv")

def collecter_lovac():
    print("\n🏚️  Collecte des biens vacants (LOVAC)...")

    if not os.path.exists(LOVAC_CACHE):
        print("   🔍 Récupération du fichier Communes...")
        try:
            r = requests.get(
                "https://www.data.gouv.fr/api/1/datasets/61816c6e23197bb34835228e/",
                timeout=15
            )
            data = r.json()
            url_csv = None
            for res in data.get("resources", []):
                if "Communes" in res.get("title", "") and ".csv" in res.get("url", "").lower():
                    url_csv = res.get("url", "")
                    break

            print(f"   ⬇️  Téléchargement...")
            r2 = requests.get(url_csv, timeout=120, stream=True)
            total = int(r2.headers.get("content-length", 0))
            downloaded = 0
            with open(LOVAC_CACHE, "wb") as f:
                for chunk in r2.iter_content(chunk_size=512*1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded / total * 100)
                        print(f"   ⬇️  {pct}%", end="\r")
            print(f"\n   ✅ Téléchargement terminé ({downloaded // 1024} Ko)")
        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            return []
    else:
        print(f"   ✅ Fichier en cache ({os.path.getsize(LOVAC_CACHE) // 1024} Ko)")

    # Lecture et filtrage
    print("   🔍 Filtrage sur tes communes...")
    codes = set(COMMUNES.values())
    noms = {v: k for k, v in COMMUNES.items()}
    resultats = []

    try:
        with open(LOVAC_CACHE, encoding="utf-8", errors="ignore") as f:
            contenu = f.read()

        reader = csv.DictReader(io.StringIO(contenu), delimiter=";")

        for row in reader:
            # La colonne code commune s'appelle CODGEO_25
            code = row.get("CODGEO_25", "").strip()

            if code in codes:
                resultats.append({
                    "commune": noms.get(code, code),
                    "code_insee": code,
                    "libelle": row.get("LIBGEO_25", ""),
                    # Données 2025
                    "vacants_2025": row.get("pp_vacant_25", ""),
                    "vacants_plus_2ans_2025": row.get("pp_vacant_plus_2ans_25", ""),
                    # Données 2024
                    "total_logements_2024": row.get("pp_total_24", ""),
                    "vacants_2024": row.get("pp_vacant_24", ""),
                    "vacants_plus_2ans_2024": row.get("pp_vacant_plus_2ans_24", ""),
                    # Données 2023
                    "vacants_2023": row.get("pp_vacant_23", ""),
                    "vacants_plus_2ans_2023": row.get("pp_vacant_plus_2ans_23", ""),
                    # Département / Région
                    "departement": row.get("LIB_DEP", ""),
                    "region": row.get("LIB_REG", ""),
                    "epci": row.get("LIB_EPCI_25", ""),
                })

        print(f"\n   Résultats :")
        for nom, code in COMMUNES.items():
            entrees = [r for r in resultats if r["commune"] == nom]
            if entrees:
                e = entrees[0]
                print(f"   → {nom} : {e['vacants_2025']} vacants 2025 · {e['vacants_plus_2ans_2025']} vacants +2ans")
            else:
                print(f"   → {nom} : 0 entrées")

    except Exception as e:
        print(f"   ❌ Erreur lecture : {e}")
        return []

    fichier = os.path.join(OUTPUT_DIR, "lovac.json")
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    print(f"\n   💾 {len(resultats)} entrées sauvegardées dans {fichier}")
    return resultats


if __name__ == "__main__":
    print("="*50)
    print("🏚️  SENTINELLE IMMO — Collecteur LOVAC v3")
    print("="*50)
    collecter_lovac()
