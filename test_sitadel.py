import requests
import json

BASE_URL = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1"
RID_DEMOLIR = "1a9a2f0c-56fe-4e69-84a7-fbbda2121f02"
MILLESIME = "2026-04"

url = f"{BASE_URL}/datafiles/{RID_DEMOLIR}/json"
# Test : plusieurs communes séparées par virgule après "in:"
params = {
    "millesime": MILLESIME,
    "COMM": "in:51454,51573",   # Reims + Tinqueux
}

print("Test filtre multi-communes (Reims + Tinqueux)...")
r = requests.get(url, params=params, timeout=120)
print(f"URL finale : {r.url}")
print(f"Statut HTTP : {r.status_code}\n")

if r.status_code != 200:
    print(r.text[:1500])
else:
    data = r.json()
    rows = data if isinstance(data, list) else (data.get('data') or data.get('rows') or [])
    print(f"Lignes retournées : {len(rows)}")
    # Compter par commune pour vérifier qu'on a bien les 2
    from collections import Counter
    communes = Counter(row.get('COMM') for row in rows)
    print(f"Répartition par commune : {dict(communes)}")