import requests

print("Vérification taille fichiers MAJIC 2025...")

URLS = {
    "Locaux 2025": "https://data.economie.gouv.fr/api/v2/catalog/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/fichier_des_locaux_situation_2025_zip",
    "Parcelles 2025 (01-56)": "https://data.economie.gouv.fr/api/v2/catalog/datasets/fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/fichier_des_parcelles_situation_2025_dpts_01_a_56_zip",
}

for nom, url in URLS.items():
    r = requests.head(url, timeout=15, allow_redirects=True)
    taille = int(r.headers.get("content-length", 0))
    print(f"\n{nom}")
    print(f"  Status : {r.status_code}")
    print(f"  URL finale : {r.url[:80]}")
    print(f"  Taille : {taille // 1024 // 1024 if taille else '?'} Mo")
    print(f"  Headers : {dict(list(r.headers.items())[:5])}")
