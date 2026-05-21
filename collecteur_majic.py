import csv
import json
import os
from datetime import datetime

# ============================================
# SENTINELLE IMMO — Collecteur MAJIC
# Fichiers DGFiP personnes morales dept 51
# Extrait les SCI propriétaires avec adresses
# ============================================

COMMUNES_CIBLES = {
    "REIMS", "TINQUEUX", "GUEUX", "MUIZON",
    "HERMONVILLE", "COURCY", "SAINT-THIERRY", "POUILLON"
}

OUTPUT_DIR     = "donnees"
CACHE_DIR      = "cache"
HISTORIQUE_DIR = "historique"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORIQUE_DIR, exist_ok=True)

FICHIERS = {
    "locaux":    os.path.join(CACHE_DIR, "PM_25_B_510.csv"),
    "parcelles": os.path.join(CACHE_DIR, "PM_25_NB_510.csv"),
}

# Mots clés SCI dans la forme juridique ou le groupe personne
MOTS_SCI = [
    "sci", "s.c.i", "societe civile immo", "société civile immo",
    "soci\u00e9t\u00e9 civile", "societe civile",
]

def est_sci(forme_juridique, groupe_personne, denomination):
    texte = (forme_juridique + " " + groupe_personne + " " + denomination).lower()
    return any(mot in texte for mot in MOTS_SCI)

def construire_adresse(row):
    num = row.get("N° voirie", "").strip()
    nature = row.get("Nature voie", "").strip()
    nom = row.get("Nom voie", "").strip()
    commune = row.get("Nom de la commune", "").strip()
    return f"{num} {nature} {nom} {commune}".strip()

def lire_fichier(chemin, type_bien):
    print(f"\n   📄 Lecture {chemin}...")
    resultats = []

    if not os.path.exists(chemin):
        print(f"   ❌ Fichier introuvable : {chemin}")
        return []

    # Détecte le séparateur et l'encodage
    encodages = ["utf-8", "latin-1", "cp1252"]
    separateurs = [";", ",", "\t"]

    contenu = None
    encodage_ok = None
    for enc in encodages:
        try:
            with open(chemin, encoding=enc) as f:
                contenu = f.read()
                encodage_ok = enc
                break
        except:
            continue

    if not contenu:
        print(f"   ❌ Impossible de lire le fichier")
        return []

    print(f"   ✅ Encodage : {encodage_ok}")

    # Détecte le séparateur
    premiere_ligne = contenu.split("\n")[0]
    sep = ";"
    for s in separateurs:
        if s in premiere_ligne:
            sep = s
            break
    print(f"   ✅ Séparateur : '{sep}'")

    # Parse le CSV
    import io
    reader = csv.DictReader(io.StringIO(contenu), delimiter=sep)
    colonnes = reader.fieldnames or []
    print(f"   ✅ Colonnes : {colonnes[:8]}...")

    nb_total = 0
    nb_sci = 0
    nb_communes = 0

    for row in reader:
        nb_total += 1

        # Filtre département 51
        dept = row.get("Département", row.get("departement", "")).strip()
        if dept != "51":
            continue

        commune = row.get("Nom de la commune", row.get("commune", "")).strip().upper()

        # Filtre nos communes
        if commune not in COMMUNES_CIBLES:
            continue
        nb_communes += 1

        # Filtre SCI
        forme = (row.get("Forme juridique abrégée - par") or row.get("Forme juridique abrégée") or "").strip()
        groupe = (row.get("Groupe personne - par") or row.get("Groupe personne") or "").strip()
        denomination = (row.get("Dénomination - par") or row.get("Dénomination") or "").strip()

        if not est_sci(forme, groupe, denomination):
            continue
        nb_sci += 1

        adresse = construire_adresse(row)
        siren = (row.get("N° SIREN - par") or row.get("N° SIREN") or "").strip()
        majic = (row.get("N° Majic - par") or row.get("N° Majic") or "").strip()
        contenance = row.get("Contenance", row.get("contenance", "")).strip()
        nature = row.get("Nature culture", row.get("nature_culture", "")).strip()

        resultats.append({
            "type_bien": type_bien,
            "commune": commune.title(),
            "adresse": adresse,
            "denomination": denomination,
            "forme_juridique": forme,
            "groupe_personne": groupe,
            "siren": siren,
            "majic": majic,
            "contenance": contenance,
            "nature": nature,
            "source": "MAJIC DGFiP 2025",
        })

    print(f"   → {nb_total} lignes · {nb_communes} sur nos communes · {nb_sci} SCI trouvées")
    return resultats

def collecter_majic():
    print("\n🏢 Collecte MAJIC — SCI propriétaires dept 51...")

    tous = []
    for type_bien, chemin in FICHIERS.items():
        resultats = lire_fichier(chemin, type_bien)
        tous.extend(resultats)

    # Dédoublonne par adresse + denomination
    vus = set()
    uniques = []
    for r in tous:
        cle = f"{r['denomination']}_{r['adresse']}"
        if cle not in vus:
            vus.add(cle)
            uniques.append(r)

    uniques.sort(key=lambda x: (x["commune"], x["denomination"]))

    print(f"\n   📊 Résumé par commune :")
    from collections import Counter
    communes = Counter([r["commune"] for r in uniques])
    for commune, nb in communes.most_common():
        print(f"   → {commune} : {nb} SCI propriétaires")

    # Détection nouveautés
    hist_path = os.path.join(HISTORIQUE_DIR, "majic_vus.json")
    historique = {}
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            historique = json.load(f)

    nouveaux = []
    for r in uniques:
        cle = f"{r['denomination']}_{r['adresse']}"
        if cle not in historique:
            nouveaux.append(r)
            historique[cle] = {
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                "commune": r["commune"],
            }

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "majic.json"), "w", encoding="utf-8") as f:
        json.dump(uniques, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "majic_nouveaux.json"), "w", encoding="utf-8") as f:
        json.dump(nouveaux, f, ensure_ascii=False, indent=2)

    print(f"\n   💾 {len(uniques)} SCI propriétaires · {len(nouveaux)} nouvelles")

    if uniques:
        print(f"\n   📋 Exemples :")
        for r in uniques[:8]:
            print(f"   → [{r['commune']}] {r['denomination']}")
            print(f"      📍 {r['adresse']}")
            if r.get("siren"):
                print(f"      SIREN : {r['siren']}")

    return uniques, nouveaux


if __name__ == "__main__":
    print("="*52)
    print("🏢 SENTINELLE IMMO — Collecteur MAJIC")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    collecter_majic()
