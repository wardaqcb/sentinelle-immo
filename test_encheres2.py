import requests, csv, io

# Télécharge et analyse le fichier résultats
url = "https://static.data.gouv.fr/resources/distribution-des-prix-de-vente-des-biens-immobiliers-des-tribu/20241016-094910/resultats-vente-2006-2024.csv"
r = requests.get(url, timeout=30)
contenu = r.content.decode("utf-8", errors="ignore")
reader = csv.DictReader(io.StringIO(contenu))

# Affiche les colonnes
colonnes = reader.fieldnames
print(f"Colonnes : {colonnes}")

# Cherche les ventes de la Marne
print("\nVentes Marne (51) :")
for i, row in enumerate(reader):
    val = str(row)
    if "51" in val and ("Reims" in val or "Marne" in val or "51100" in val):
        print(f"  → {dict(row)}")
        if i > 50000:
            break