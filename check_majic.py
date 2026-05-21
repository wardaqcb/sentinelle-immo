import csv

with open('cache/PM_25_B_510.csv', encoding='utf-8') as f:
    reader = csv.DictReader(f, delimiter=';')
    print("Colonnes fichier LOCAUX :")
    for col in reader.fieldnames:
        print(f"  - {col}")
    print("\n3 premières lignes :")
    for i, row in enumerate(reader):
        if i >= 3:
            break
        print(dict(row))
