import json

with open("donnees/bodacc.json", encoding="utf-8") as f:
    bodacc = json.load(f)

print(f"Total annonces : {len(bodacc)}")
print(f"\nStructure complète des 3 premières annonces :")
for i, a in enumerate(bodacc[:3]):
    print(f"\n--- Annonce {i+1} ---")
    for k, v in a.items():
        print(f"  {k} : {v}")
