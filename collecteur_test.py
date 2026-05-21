import requests
import json
import os
from datetime import datetime

# ============================================
# SENTINELLE IMMO — Collecteur TEST v2
# BODACC + Décès INSEE uniquement
# Sans DVF pour aller vite
# ============================================

COMMUNES = {
    "Reims":         "51454",
    "Tinqueux":      "51573",
    "Gueux":         "51282",
    "Muizon":        "51391",
    "Hermonville":   "51291",
    "Courcy":        "51183",
    "Saint-Thierry": "51518",
    "Pouillon":      "51444",
}

OUTPUT_DIR     = "donnees"
CACHE_DIR      = "cache"
DECES_DIR      = os.path.join("cache", "deces")
HISTORIQUE_DIR = "historique"

# ============================================
# BODACC
# ============================================

def tester_bodacc():
    print("\n⚖️  Test BODACC — SCI + Liquidations...")
    toutes_annonces = []
    BASE = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"

    offset = 0
    while True:
        try:
            r = requests.get(BASE, params={
                "where": "tribunal like 'Reims'",
                "limit": 100,
                "offset": offset,
                "order_by": "dateparution desc",
            }, timeout=15)

            if r.status_code != 200:
                print(f"   ⚠️ Erreur {r.status_code}")
                break

            data = r.json()
            annonces = data.get("results", [])
            total = data.get("total_count", 0)

            for a in annonces:
                toutes_annonces.append({
                    "id": a.get("numerodannonce", ""),
                    "type": a.get("familleavis_lib", ""),
                    "date": a.get("dateparution", ""),
                    "description": a.get("commercant", ""),
                    "tribunal": a.get("tribunal", ""),
                    "numero": a.get("numerodannonce", ""),
                    "jugement": a.get("typeavis_lib", ""),
                    "activite": a.get("activite", ""),
                })

            offset += 100
            if offset >= min(total, 1000) or not annonces:
                break

        except Exception as e:
            print(f"   ❌ {e}")
            break

    print(f"   → {len(toutes_annonces)} annonces récupérées")

    # Filtre strict — SCI uniquement
    # Un vrai nom de SCI commence toujours par SCI ou contient "société civile"
    mots_sci = [
        "sci ", "s.c.i", "sci.", "sci-",
        "societe civile immobiliere",
        "société civile immobilière",
        "societe civile immo",
        "société civile immo",
    ]
    mots_jugement_immo = ["liquid", "redress"]

    resultats = []
    for a in toutes_annonces:
        desc = (a.get("description", "") or "").lower().strip()
        jugement = (a.get("jugement", "") or "").lower()

        # Doit être une SCI (commence par SCI ou contient société civile)
        est_sci = (
            desc.startswith("sci ") or
            desc.startswith("s.c.i") or
            "societe civile immo" in desc or
            "société civile immo" in desc or
            " sci " in desc
        )

        est_judiciaire = any(mot in jugement for mot in mots_jugement_immo)

        if est_sci or est_judiciaire:
            resultats.append(a)

    resultats.sort(key=lambda x: x.get("date", ""), reverse=True)

    print(f"   ✅ {len(resultats)} annonces SCI/liquidation après filtrage strict")
    print(f"\n   📋 Toutes les annonces filtrées :")
    for a in resultats:
        print(f"   → [{a['jugement']}] {a['description']} | {a['date']}")

    with open(os.path.join(OUTPUT_DIR, "bodacc.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)

    return resultats

# ============================================
# DÉCÈS INSEE
# ============================================

def tester_deces():
    print("\n⚰️  Test Décès INSEE...")

    fichiers = sorted([f for f in os.listdir(DECES_DIR) if f.endswith(".txt")])
    print(f"   📁 Fichiers : {fichiers}")

    codes_cibles = set(COMMUNES.values())  # {"51454", "51573"...}
    print(f"   Codes INSEE cibles : {codes_cibles}")

    tous_deces = []

    for fichier in fichiers:
        chemin = os.path.join(DECES_DIR, fichier)
        nb = 0
        nb_total = 0

        with open(chemin, encoding="utf-8", errors="ignore") as f:
            for ligne in f:
                nb_total += 1
                try:
                    if len(ligne) < 100:
                        continue

                    nom_prenom = ligne[0:80].strip()
                    if "*" not in nom_prenom:
                        continue

                    parties = nom_prenom.split("*", 1)
                    nom = parties[0].strip()
                    prenom = parties[1].replace("/", "").strip()

                    sexe = "M" if ligne[80:81].strip() == "1" else "F"
                    naiss_raw = ligne[81:89].strip()
                    code_deces = ligne[160:165].strip()
                    deces_raw = ligne[152:160].strip()

                    # Debug sur les 5 premières lignes
                    if nb_total <= 5:
    print(f"   Debug ligne {nb_total}: [79-94]=[{repr(ligne[79:95])}] code_deces=[{code_deces}]")

                    if code_deces in codes_cibles:
                        age = None
                        try:
                            if len(naiss_raw) >= 4 and len(deces_raw) >= 4:
                                age = int(deces_raw[:4]) - int(naiss_raw[:4])
                        except: pass

                        tous_deces.append({
                            "nom": nom,
                            "prenom": prenom,
                            "sexe": sexe,
                            "date_naissance": naiss_raw,
                            "date_deces": deces_raw,
                            "code_commune_deces": code_deces,
                            "commune": COMMUNES[code_deces],
                            "age_deces": age,
                            "fichier_source": fichier,
                        })
                        nb += 1

                except Exception as e:
                    continue

        print(f"   📄 {fichier} → {nb_total} lignes · {nb} décès trouvés")

    print(f"\n   💾 {len(tous_deces)} décès totaux")

    if tous_deces:
        print(f"\n   📋 Exemples :")
        for d in tous_deces[:5]:
            print(f"   → {d['nom']} {d['prenom']} · {d['commune']} · {d['date_deces']}")

    with open(os.path.join(OUTPUT_DIR, "deces.json"), "w", encoding="utf-8") as f:
        json.dump(tous_deces, f, ensure_ascii=False, indent=2)

    return tous_deces


if __name__ == "__main__":
    print("="*52)
    print("🧪 SENTINELLE IMMO — Collecteur Test v2")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)

    bodacc = tester_bodacc()
    deces  = tester_deces()

    print(f"\n{'='*52}")
    print(f"✅ RÉSULTATS")
    print(f"   BODACC SCI : {len(bodacc)} annonces")
    print(f"   Décès INSEE : {len(deces)} décès")
    print(f"{'='*52}")
