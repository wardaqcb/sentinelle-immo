import requests
import json
from pathlib import Path
from collections import Counter
from datetime import datetime

BASE_URL = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1"
MILLESIME = "2026-04"
OUTPUT_PATH = "donnees/sitadel.json"

from config_communes import CODE_TO_NOM as COMMUNES, CODES_INSEE_STR

# Les 4 fichiers de données Sitadel
FICHIERS = {
    "logements":  "8b35affb-55fc-4c1f-915b-7750f974446a",
    "locaux":     "f8f0700f-806c-40a7-83b1-f21cf507e7c4",
    "amenager":   "96883f50-538b-41f9-a059-c6eb97e6a23a",
    "demolir":    "1a9a2f0c-56fe-4e69-84a7-fbbda2121f02",
}

def recuperer_fichier(nom, rid):
    """Récupère tous les permis d'un fichier pour nos communes."""
    params = {"millesime": MILLESIME, "COMM": f"in:{CODES_INSEE_STR}"}

    print(f"  Interrogation du fichier '{nom}'...", end=" ", flush=True)
    r = requests.get(url, params=params, timeout=180)

    if r.status_code != 200:
        print(f"ERREUR {r.status_code}")
        print(f"    {r.text[:300]}")
        return []

    data = r.json()
    rows = data if isinstance(data, list) else (data.get("data") or data.get("rows") or [])
    print(f"{len(rows)} permis")

    # On ajoute le type de fichier + nom commune à chaque ligne
    for row in rows:
        row["_SOURCE_FICHIER"] = nom
        row["_COMMUNE_NOM"] = COMMUNES.get(row.get("COMM"), "?")
    return rows

def main():
    print("=" * 60)
    print("COLLECTEUR SITADEL — autorisations d'urbanisme")
    print(f"Millésime {MILLESIME} | {len(COMMUNES)} communes")
    print("=" * 60)

    tous_permis = []
    for nom, rid in FICHIERS.items():
        tous_permis.extend(recuperer_fichier(nom, rid))

    print(f"\nTotal permis récupérés : {len(tous_permis)}")

    # === Statistiques rapides ===
    print("\n--- Répartition par type de fichier ---")
    for typ, nb in Counter(p["_SOURCE_FICHIER"] for p in tous_permis).items():
        print(f"  {typ:12s} : {nb}")

    print("\n--- Répartition par commune ---")
    for code, nb in Counter(p["COMM"] for p in tous_permis).most_common():
        print(f"  {COMMUNES.get(code, code):15s} : {nb}")

    # Signaux exploitables
    avec_siren = [p for p in tous_permis if p.get("SIREN_DEM")]
    print(f"\nPermis avec SIREN demandeur (= personne morale, croisable MAJIC/Pappers) : {len(avec_siren)}")

    # Demandeur domicilié hors de la commune du terrain (profil investisseur)
    hors_commune = [
        p for p in tous_permis
        if p.get("LOCALITE_DEM") and p.get("ADR_LOCALITE_TER")
        and p["LOCALITE_DEM"].strip().upper() != p["ADR_LOCALITE_TER"].strip().upper()
    ]
    print(f"Demandeur domicilié hors commune du bien (profil investisseur) : {len(hors_commune)}")

    # === Sauvegarde ===
    Path("donnees").mkdir(exist_ok=True)
    sortie = {
        "_meta": {
            "source": "Sitadel (SDES) via API DiDo",
            "millesime": MILLESIME,
            "date_collecte": datetime.now().isoformat(timespec="seconds"),
            "nb_permis": len(tous_permis),
            "communes": COMMUNES,
        },
        "permis": tous_permis,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sortie, f, ensure_ascii=False, indent=2)

    taille_ko = Path(OUTPUT_PATH).stat().st_size / 1024
    print(f"\n✓ Sauvegardé dans {OUTPUT_PATH} ({taille_ko:.0f} Ko)")

if __name__ == "__main__":
    main()