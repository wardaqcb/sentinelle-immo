import requests
import json

print("Récupération des vraies URLs DVF depuis data.gouv.fr...")

r = requests.get(
    "https://www.data.gouv.fr/api/1/datasets/5c4ae55a634f4117716d5656/",
    timeout=15
)
print(f"Status : {r.status_code}")

if r.status_code == 200:
    data = r.json()
    print(f"Dataset : {data.get('title','')}")
    print(f"\nFichiers disponibles :")
    for res in data.get("resources", []):
        titre = res.get("title", "")
        url = res.get("url", "")
        if "valeursfoncieres" in url.lower() or "valeurs" in titre.lower():
            print(f"  → {titre}")
            print(f"     {url}")
else:
    # Essai avec un autre ID
    r2 = requests.get(
        "https://www.data.gouv.fr/api/1/datasets/?q=demandes+valeurs+foncieres+dgfip&page_size=3",
        timeout=15
    )
    for d in r2.json().get("data", []):
        print(f"\n→ {d.get('title','')[:60]} | ID: {d.get('id','')}")
