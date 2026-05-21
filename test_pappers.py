import requests
import json

print("Test API Pappers Immobilier — recherche endpoints...")
print("="*50)

# Endpoints possibles d'après la doc
TESTS = [
    "https://api.pappers.fr/v2/immobilier/parcelles?code_commune=51454&nombre_resultats=3",
    "https://immobilier.pappers.fr/api/parcelles?code_commune=51454",
    "https://immobilier.pappers.fr/api/ventes?code_commune=51454",
    "https://immobilier.pappers.fr/api/search?q=reims&type=parcelle",
    "https://api.pappers.fr/v2/immobilier?code_commune=51454",
]

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

for url in TESTS:
    print(f"\n→ {url[:70]}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"  Status : {r.status_code}")
        if r.status_code == 200:
            print(f"  ✅ Réponse : {r.text[:200]}")
        elif r.status_code == 401:
            print(f"  🔑 Authentification requise — API payante")
        elif r.status_code == 403:
            print(f"  🔒 Accès refusé — clé API nécessaire")
        else:
            print(f"  Réponse : {r.text[:100]}")
    except Exception as e:
        print(f"  ❌ {e}")
