import os
import json
from datetime import datetime

# ============================================
# SENTINELLE IMMO — Collecteur Décès INSEE v3
# Format réel analysé sur les fichiers 2026
#
# Format ligne INSEE décès :
# 000-079 : Nom*Prénom/         (80 chars)
# 080     : Sexe (1=H, 2=F)
# 081-088 : Date naissance AAAAMMJJ
# 089-093 : Code commune décès  (5 chars) ← DÉCÈS, pas naissance !
# 094-151 : Commune décès libellé
# 152-159 : Date décès AAAAMMJJ
# 160+    : Numéro acte
# ============================================

COMMUNES = {
    "51454": "Reims",
    "51573": "Tinqueux",
    "51282": "Gueux",
    "51391": "Muizon",
    "51291": "Hermonville",
    "51183": "Courcy",
    "51518": "Saint-Thierry",
    "51444": "Pouillon",
}

DECES_DIR = os.path.join("cache", "deces")
OUTPUT_DIR = "donnees"
HISTORIQUE_DIR = "historique"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORIQUE_DIR, exist_ok=True)

def formater_date(raw):
    try:
        if len(raw) == 8 and raw.isdigit():
            a, m, j = raw[:4], raw[4:6], raw[6:8]
            if m == "00": m = "01"
            if j == "00": j = "01"
            return f"{j}/{m}/{a}"
    except:
        pass
    return raw

def calculer_age(naiss_raw, deces_raw):
    try:
        if len(naiss_raw) >= 4 and len(deces_raw) >= 4:
            return int(deces_raw[:4]) - int(naiss_raw[:4])
    except:
        pass
    return None

def parser_ligne(ligne):
    try:
        if len(ligne) < 100:
            return None

        # Nom et prénom
        nom_prenom = ligne[0:80].strip()
        if "*" not in nom_prenom:
            return None
        parties = nom_prenom.split("*", 1)
        nom = parties[0].strip()
        prenom = parties[1].replace("/", "").strip()

        # Sexe
        sexe_code = ligne[80:81].strip()
        sexe = "M" if sexe_code == "1" else "F" if sexe_code == "2" else "?"

        # Date naissance
        naiss_raw = ligne[81:89].strip()

        # Code commune décès (position 89-93)
        code_deces = ligne[89:94].strip()

        # Commune décès libellé
        commune_lib = ligne[94:152].strip()

        # Date décès (position 152-159)
        deces_raw = ligne[152:160].strip()

        return {
            "nom": nom,
            "prenom": prenom,
            "sexe": sexe,
            "date_naissance": formater_date(naiss_raw),
            "naiss_raw": naiss_raw,
            "date_deces": formater_date(deces_raw),
            "date_deces_raw": deces_raw,
            "code_commune_deces": code_deces,
            "commune_deces_lib": commune_lib,
        }
    except:
        return None

def collecter_deces():
    print("\n⚰️  Collecte des décès INSEE...")

    fichiers = sorted([f for f in os.listdir(DECES_DIR) if f.endswith(".txt")])
    print(f"   📁 {len(fichiers)} fichiers trouvés")

    codes_cibles = set(COMMUNES.keys())
    tous_deces = []

    for fichier in fichiers:
        chemin = os.path.join(DECES_DIR, fichier)
        print(f"   📄 {fichier}...", end=" ")
        nb_total = 0
        nb_trouves = 0

        with open(chemin, encoding="utf-8", errors="ignore") as f:
            for ligne in f:
                nb_total += 1
                parsed = parser_ligne(ligne)
                if not parsed:
                    continue
                if parsed["code_commune_deces"] in codes_cibles:
                    parsed["commune"] = COMMUNES[parsed["code_commune_deces"]]
                    parsed["age_deces"] = calculer_age(parsed["naiss_raw"], parsed["date_deces_raw"])
                    parsed["fichier_source"] = fichier
                    tous_deces.append(parsed)
                    nb_trouves += 1

        print(f"{nb_total} lignes · {nb_trouves} décès trouvés")

    tous_deces.sort(key=lambda x: x.get("date_deces_raw", ""), reverse=True)

    # Détection nouveautés
    hist_path = os.path.join(HISTORIQUE_DIR, "deces_vus.json")
    historique = {}
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            historique = json.load(f)

    nouveaux = []
    for d in tous_deces:
        cle = f"{d['nom']}_{d['prenom']}_{d['date_deces_raw']}_{d['code_commune_deces']}"
        if cle not in historique:
            nouveaux.append(d)
            historique[cle] = {
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                "commune": d["commune"],
                "date_deces": d["date_deces"],
            }

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "deces.json"), "w", encoding="utf-8") as f:
        json.dump(tous_deces, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "deces_nouveaux.json"), "w", encoding="utf-8") as f:
        json.dump(nouveaux, f, ensure_ascii=False, indent=2)

    print(f"\n   📊 Résumé par commune :")
    for code, nom in COMMUNES.items():
        nb = len([d for d in tous_deces if d["code_commune_deces"] == code])
        nb_new = len([d for d in nouveaux if d["code_commune_deces"] == code])
        if nb > 0:
            print(f"   → {nom} : {nb} décès · {nb_new} nouveaux")

    print(f"\n   💾 {len(tous_deces)} décès totaux · {len(nouveaux)} nouveaux")

    if tous_deces:
        print(f"\n   📋 Exemples :")
        for d in tous_deces[:8]:
            age = f" · {d['age_deces']} ans" if d.get("age_deces") else ""
            print(f"   → {d['nom']} {d['prenom']}{age} — {d['date_deces']} à {d['commune']}")

    return tous_deces, nouveaux


if __name__ == "__main__":
    print("="*52)
    print("⚰️  SENTINELLE IMMO — Collecteur Décès INSEE v3")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    collecter_deces()
