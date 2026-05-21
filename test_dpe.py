import requests
import json

print("Test DPE passoires thermiques Reims...")

r = requests.get(
    "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines",
    params={
        "size": 5,
        "qs": "etiquette_dpe:(F OR G) AND code_insee_ban:51454",
        "select": "numero_dpe,adresse_ban,nom_commune_ban,etiquette_dpe,surface_habitable_immeuble,type_batiment,date_etablissement_dpe",
    },
    timeout=15
)
print(f"Status : {r.status_code}")
data = r.json()
print(f"Total passoires F/G à Reims : {data.get('total', 0)}")
for item in data.get("results", []):
    print(f"\n  → {item.get('adresse_ban','—')}")
    print(f"     DPE : {item.get('etiquette_dpe','—')} | Surface : {item.get('surface_habitable_immeuble','—')} m²")
    print(f"     Type : {item.get('type_batiment','—')} | Date : {item.get('date_etablissement_dpe','—')[:10]}")