import requests
from collections import Counter

BASE = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

# Récupère toutes les valeurs distinctes de familleavis_lib pour Reims
r = requests.get(BASE, params={
    "where": "tribunal like 'Reims' and dateparution >= '2024-01-01'",
    "limit": 100,
    "group_by": "familleavis_lib",
    "select": "familleavis_lib, count(*) as nb",
}, timeout=15)

print(f"Status : {r.status_code}")
data = r.json()
print(f"\nValeurs distinctes de familleavis_lib :")
for item in data.get("results", []):
    print(f"  → '{item.get('familleavis_lib','?')}' : {item.get('nb', 0)} annonces")
