import zipfile, io, csv, requests

url = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002321/valeursfoncieres-2025.txt.zip"
print("Téléchargement...")
r = requests.get(url, timeout=120)
print("Extraction...")
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    with z.open(z.namelist()[0]) as f:
        contenu = f.read().decode("utf-8", errors="ignore")

reader = csv.DictReader(io.StringIO(contenu), delimiter="|")
row = next(reader)
print("\nColonnes trouvées :")
for k, v in row.items():
    print(f"  [{k}] = {v}")
