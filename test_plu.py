import requests

ADRESSE = "3 Rue Macquart 51100 Reims"

# 1. Géocodage
r = requests.get("https://api-adresse.data.gouv.fr/search/", params={"q": ADRESSE, "limit": 1}, timeout=10)
geo = r.json()["features"][0]
lon = geo["geometry"]["coordinates"][0]
lat = geo["geometry"]["coordinates"][1]
print(f"Coordonnées : {lat}, {lon}")

# 2. Zone PLU avec partition directe
for code in ["DU_51454", "DU_200057026"]:
    r2 = requests.get("https://apicarto.ign.fr/api/gpu/zone-urba", params={"partition": code}, timeout=15)
    features = r2.json().get("features", [])
    print(f"\nPartition {code} : {len(features)} zones")
    if features:
        p = features[0].get("properties", {})
        print(f"  Exemple : {p.get('libelle')} ({p.get('typezone')}) — {p.get('libelong','')[:60]}")
        break
