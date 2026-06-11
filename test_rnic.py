import pandas as pd
import json
from pathlib import Path

# === Configuration ===
CSV_PATH = 'cache/rnic_full.csv'
OUTPUT_PATH = 'donnees/rnc_communes_surveillees.json'

CODES_INSEE_COMMUNES = {
    '51183': 'Courcy',
    '51282': 'Gueux',
    '51291': 'Hermonville',
    '51391': 'Muizon',
    '51444': 'Pouillon',
    '51454': 'Reims',
    '51573': 'Tinqueux',
}

# === Lecture du fichier complet ===
print(f"Lecture du fichier {CSV_PATH}...")
print("(cela peut prendre 30-60 secondes)\n")

df = pd.read_csv(
    CSV_PATH,
    sep=',',
    dtype=str,
    encoding='utf-8',
    low_memory=False
)

print(f"Total copropriétés en France : {len(df):,}")
print(f"Colonnes : {len(df.columns)}\n")

# === Filtre sur nos communes — via colonne 'commune' (col 2), fiable ===
codes = list(CODES_INSEE_COMMUNES.keys())
df_local = df[df['commune'].isin(codes)].copy()

print("=" * 60)
print(f"COPROS DANS NOTRE PÉRIMÈTRE : {len(df_local)}")
print("=" * 60)

# Répartition par commune
print("\nRépartition par commune :")
repartition = df_local['commune'].value_counts()
for code, nb in repartition.items():
    nom = CODES_INSEE_COMMUNES.get(code, '?')
    print(f"  {code} - {nom:15s} : {nb:4d} copros")

# Si une commune attendue a 0 copro, on le signale
print("\nCommunes attendues sans aucune copro :")
trouvees = set(repartition.index)
for code, nom in CODES_INSEE_COMMUNES.items():
    if code not in trouvees:
        print(f"  {code} - {nom} : 0 copro")

# Si aucun résultat, on arrête là
if len(df_local) == 0:
    print("\n⚠️ Aucune copro trouvée, vérification nécessaire")
    exit()

# === Signaux exploitables ===
print("\n" + "=" * 60)
print("SIGNAUX EXPLOITABLES (open data)")
print("=" * 60)

# Mandat expiré sans successeur = copro sans syndic
mandat_pb = df_local[
    df_local['mandat_en_cours'].str.contains('expir', case=False, na=False)
]
print(f"\nMandat expiré (sans ou avec successeur) : {len(mandat_pb)}")

pas_de_mandat = df_local[df_local['mandat_en_cours'] == 'Pas de mandat en cours']
print(f"Pas de mandat en cours : {len(pas_de_mandat)}")

# Copro aidée par ANAH (signe historique de fragilité)
aidees = df_local[df_local['copro_aidee'].str.lower() == 'oui']
print(f"\nCopros aidées par l'ANAH : {len(aidees)}")

# Copro en QPV, ACV, PVD, PDP
in_qpv = df_local[df_local['code_qp_2024'].notna() & (df_local['code_qp_2024'] != '')]
print(f"Copros en QPV (Quartier Prioritaire) 2024 : {len(in_qpv)}")

in_acv = df_local[df_local['copro_dans_acv'].str.lower() == 'oui']
print(f"Copros en ACV (Action Cœur de Ville) : {len(in_acv)}")

in_pvd = df_local[df_local['copro_dans_pvd'].str.lower() == 'oui']
print(f"Copros en PVD (Petites Villes de Demain) : {len(in_pvd)}")

# Copros anciennes
print("\n" + "=" * 60)
print("RÉPARTITION PAR PÉRIODE DE CONSTRUCTION")
print("=" * 60)
print(df_local['periode_construction'].value_counts())

# === Sauvegarde ===
Path('donnees').mkdir(exist_ok=True)

records = df_local.to_dict(orient='records')
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"\n✓ Données sauvegardées dans {OUTPUT_PATH}")
print(f"  ({len(records)} copropriétés, {Path(OUTPUT_PATH).stat().st_size / 1024:.1f} Ko)")