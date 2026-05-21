import requests
import json

BASE = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

# On regarde d'abord les valeurs possibles de familleavis_lib et typeavis_lib
print("=== Valeurs disponibles dans le BODACC ===")

# Récupère 5 annonces pour voir la structure complète
r = requests.get(BASE, params={
    "where": "tribunal like 'Reims'",
    "limit": 5,
    "order_by": "dateparution desc",
})
data = r.json()

print("\nStructure d'une annonce complète :")
if data.get("results"):
    print(json.dumps(data["results"][0], indent=2, ensure_ascii=False))

# Compte par type
print("\n=== Comptage par type (familleavis_lib) ===")
types = ["Vente", "Liquidation", "Redressement", "Modification", "Radiation", "Immatriculation", "Succession"]
for t in types:
    r2 = requests.get(BASE, params={
        "where": f"tribunal like 'Reims' and dateparution >= '2025-01-01' and familleavis_lib like '{t}'",
        "limit": 1,
    })
    total = r2.json().get("total_count", 0)
    if total > 0:
        print(f"  {t} : {total} annonces")
