import requests
import json

print("Recherche du fichier LOVAC sur data.gouv.fr...")

# Recherche datasets logements vacants
urls_a_tester = [
    "https://www.data.gouv.fr/api/1/datasets/?q=logements+vacants+lovac&page_size=5",
    "https://www.data.gouv.fr/api/1/datasets/?q=lovac+commune&page_size=5",
    "https://www.data.gouv.fr/api/1/datasets/?q=logements+vacants+commune&page_size=5",
]

for url in urls_a_tester:
    print(f"\nTest : {url[:60]}...")
    r = requests.get(url, timeout=15)
    print(f"Status : {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        datasets = data.get("data", [])
        print(f"Résultats : {len(datasets)}")
        for d in datasets:
            print(f"  → {d.get('title', '')[:80]}")
            print(f"     ID : {d.get('id', '')}")
            resources = d.get("resources", [])
            for res in resources[:2]:
                print(f"     Fichier : {res.get('title', '')[:60]}")
                print(f"     URL    : {res.get('url', '')[:80]}")
