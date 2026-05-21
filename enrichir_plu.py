import requests
import json
import time
from shapely.geometry import shape, Point

COMMUNES = {
    "Reims":         "DU_51454",
    "Tinqueux":      "DU_51573",
    "Gueux":         "DU_51282",
    "Muizon":        "DU_51391",
    "Hermonville":   "DU_51291",
    "Courcy":        "DU_51183",
    "Saint-Thierry": "DU_51518",
    "Pouillon":      "DU_51444",
}

print("=== Enrichissement PLU toutes communes ===")

# 1. Télécharger toutes les zones
print("\n1. Téléchargement des zones PLU...")
zones = []
for commune, partition in COMMUNES.items():
    r = requests.get(
        "https://apicarto.ign.fr/api/gpu/zone-urba",
        params={"partition": partition},
        timeout=30
    )
    features = r.json().get("features", [])
    for f in features:
        try:
            geom = shape(f["geometry"])
            props = f.get("properties", {})
            zones.append({
                "geometry": geom,
                "libelle": props.get("libelle", "?"),
                "libelong": props.get("libelong", "?"),
                "typezone": props.get("typezone", "?"),
                "commune": commune,
            })
        except Exception:
            continue
    print(f"   {commune} : {len(features)} zones")
    time.sleep(0.3)

print(f"   Total : {len(zones)} zones")

# 2. Géocodage avec cache
geocode_cache = {}
def geocode(adresse):
    if adresse in geocode_cache:
        return geocode_cache[adresse]
    try:
        r = requests.get("https://api-adresse.data.gouv.fr/search/",
            params={"q": adresse, "limit": 1}, timeout=5)
        features = r.json().get("features", [])
        if features and features[0]["properties"].get("score", 0) > 0.5:
            coords = features[0]["geometry"]["coordinates"]
            result = (coords[1], coords[0])
        else:
            result = None
    except Exception:
        result = None
    geocode_cache[adresse] = result
    time.sleep(0.1)
    return result

# 3. Matching
def trouver_zone(lat, lon):
    point = Point(lon, lat)
    for z in zones:
        if z["geometry"].contains(point):
            return z["libelle"], z["libelong"], z["typezone"], z["commune"]
    return None, None, None, None

# 4. Charger et enrichir
print("\n2. Enrichissement des leads...")
with open("donnees/leads_triple.json", "r", encoding="utf-8") as f:
    leads = json.load(f)

enrichis = 0
for i, lead in enumerate(leads):
    if i % 100 == 0:
        print(f"   {i}/{len(leads)}...", end="\r")
    adresse = f"{lead.get('adresse','')} {lead.get('code_postal','')} {lead.get('commune','')}".strip()
    coords = geocode(adresse) if adresse else None
    if coords:
        libelle, libelong, typezone, commune = trouver_zone(*coords)
        lead["zone_plu"] = libelle
        lead["zone_plu_long"] = libelong
        lead["zone_plu_type"] = typezone
        if libelle:
            enrichis += 1
    else:
        lead["zone_plu"] = lead.get("zone_plu")  # garder existant

with open("donnees/leads_triple.json", "w", encoding="utf-8") as f:
    json.dump(leads, f, ensure_ascii=False, indent=2)

print(f"\n✅ {enrichis}/{len(leads)} leads avec zone PLU")
