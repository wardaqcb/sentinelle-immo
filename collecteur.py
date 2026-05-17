import requests
import json
import os
import csv
import io
import zipfile
from datetime import datetime

# ============================================
# SENTINELLE IMMO — Collecteur v9
# Sources : DVF + BODACC + Décès INSEE
# Détection des nouveautés sur toutes les sources
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

COMMUNES_NOM = {v: k for k, v in COMMUNES.items()}

OUTPUT_DIR = "donnees"
CACHE_DIR = "cache"
DECES_DIR = os.path.join("cache", "deces")
HISTORIQUE_DIR = "historique"

for d in [OUTPUT_DIR, CACHE_DIR, DECES_DIR, HISTORIQUE_DIR]:
    os.makedirs(d, exist_ok=True)

DVF_URL = "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002321/valeursfoncieres-2025.txt.zip"
DVF_CACHE = os.path.join(CACHE_DIR, "valeursfoncieres-2025.zip")

# ============================================
# UTILITAIRES
# ============================================

def charger_historique(nom):
    chemin = os.path.join(HISTORIQUE_DIR, nom)
    if os.path.exists(chemin):
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    return {}

def sauvegarder_historique(nom, data):
    with open(os.path.join(HISTORIQUE_DIR, nom), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def sauvegarder(nom, data):
    with open(os.path.join(OUTPUT_DIR, nom), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

# ============================================
# 1. DVF
# ============================================

def collecter_dvf():
    print("\n📊 Collecte DVF...")
    codes = set(COMMUNES.keys())
    resultats = []

    if os.path.exists(DVF_CACHE):
        print(f"   ✅ Cache ({os.path.getsize(DVF_CACHE)//1024//1024} Mo)")
    else:
        print("   ⏳ Téléchargement...")
        try:
            r = requests.get(DVF_URL, timeout=120, stream=True)
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(DVF_CACHE, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024*1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        print(f"   ⬇️  {int(downloaded/total*100)}%", end="\r")
            print(f"\n   ✅ Terminé")
        except Exception as e:
            print(f"   ❌ {e}")
            return [], []

    try:
        with zipfile.ZipFile(DVF_CACHE) as z:
            with z.open(z.namelist()[0]) as f:
                contenu = f.read().decode("utf-8", errors="ignore")

        reader = csv.DictReader(io.StringIO(contenu), delimiter="|")
        for row in reader:
            dept = row.get("Code departement", "").strip().zfill(2)
            commune = row.get("Code commune", "").strip().zfill(3)
            code = dept + commune
            if code in codes:
                try:
                    valeur = float(row.get("Valeur fonciere", "0").replace(",", ".").replace(" ", "") or "0")
                    surface = float(row.get("Surface reelle bati", "0").replace(",", ".").replace(" ", "") or "0")
                    type_local = row.get("Type local", "").strip()
                    prix_m2 = round(valeur / surface, 0) if surface > 0 else 0
                    if valeur > 0 and surface >= 15 and type_local in ["Maison", "Appartement"] and 500 <= prix_m2 <= 15000:
                        resultats.append({
                            "commune": COMMUNES.get(code, code),
                            "code_insee": code,
                            "date_mutation": row.get("Date mutation", ""),
                            "valeur_fonciere": valeur,
                            "surface_bati": surface,
                            "prix_m2": prix_m2,
                            "type_local": type_local,
                            "nombre_pieces": row.get("Nombre pieces principales", ""),
                            "adresse": row.get("No voie", "") + " " + row.get("Voie", ""),
                            "nature_mutation": row.get("Nature mutation", ""),
                        })
                except:
                    continue

        resultats.sort(key=lambda x: x["date_mutation"], reverse=True)

        hist = charger_historique("dvf_vus.json")
        nouveaux = []
        for t in resultats:
            cle = f"{t['commune']}_{t['adresse']}_{t['date_mutation']}_{t['valeur_fonciere']}"
            if cle not in hist:
                nouveaux.append(t)
                hist[cle] = {"date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M")}
        sauvegarder_historique("dvf_vus.json", hist)

        for nom in COMMUNES.values():
            tc = [t for t in resultats if t["commune"] == nom]
            prix = [t["prix_m2"] for t in tc]
            moy = round(sum(prix)/len(prix), 0) if prix else 0
            nb_new = len([t for t in nouveaux if t["commune"] == nom])
            print(f"   → {nom} : {len(tc)} transactions · {moy} €/m² · {nb_new} nouvelles")

    except Exception as e:
        print(f"   ❌ {e}")
        return [], []

    sauvegarder("dvf.json", resultats)
    sauvegarder("dvf_nouveaux.json", nouveaux)
    print(f"   💾 {len(resultats)} transactions · {len(nouveaux)} nouvelles")
    return resultats, nouveaux

# ============================================
# 2. BODACC
# ============================================

def collecter_bodacc():
    print("\n⚖️  Collecte BODACC...")
    resultats = []
    try:
        url = (
            "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/"
            "catalog/datasets/annonces-commerciales/records"
            "?where=tribunal%20like%20%27Reims%27&limit=100&order_by=dateparution%20desc"
        )
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            for a in r.json().get("results", []):
                resultats.append({
                    "id": a.get("numerodannonce", ""),
                    "type": a.get("familleavis_lib", ""),
                    "date": a.get("dateparution", ""),
                    "description": a.get("commercant", ""),
                    "tribunal": a.get("tribunal", ""),
                    "numero": a.get("numerodannonce", ""),
                    "jugement": a.get("typeavis_lib", ""),
                })
            print(f"   ✅ {len(resultats)} annonces récupérées")
        else:
            print(f"   ⚠️ Erreur {r.status_code}")
    except Exception as e:
        print(f"   ❌ {e}")

    hist = charger_historique("bodacc_vus.json")
    nouveaux = []
    for a in resultats:
        cle = a.get("id", "") or a.get("numero", "")
        if cle and cle not in hist:
            nouveaux.append(a)
            hist[cle] = {"date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"), "type": a.get("type", "")}
    sauvegarder_historique("bodacc_vus.json", hist)
    sauvegarder("bodacc.json", resultats)
    sauvegarder("bodacc_nouveaux.json", nouveaux)
    print(f"   💾 {len(resultats)} annonces · {len(nouveaux)} nouvelles")
    return resultats, nouveaux

# ============================================
# 3. DÉCÈS INSEE
# ============================================

def parser_ligne_deces(ligne):
    try:
        if len(ligne) < 100:
            return None
        nom_prenom = ligne[0:80].strip()
        if "*" not in nom_prenom:
            return None
        parties = nom_prenom.split("*", 1)
        nom = parties[0].strip()
        prenom = parties[1].replace("/", "").strip()
        sexe_code = ligne[80:81].strip()
        sexe = "M" if sexe_code == "1" else "F" if sexe_code == "2" else "?"
        naiss_raw = ligne[81:89].strip()
        code_deces = ligne[89:94].strip()
        commune_lib = ligne[94:152].strip()
        deces_raw = ligne[152:160].strip()
        age = None
        try:
            if len(naiss_raw) >= 4 and len(deces_raw) >= 4:
                age = int(deces_raw[:4]) - int(naiss_raw[:4])
        except:
            pass
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
            "age_deces": age,
        }
    except:
        return None

def collecter_deces():
    print("\n⚰️  Collecte Décès INSEE...")
    fichiers = sorted([f for f in os.listdir(DECES_DIR) if f.endswith(".txt")])

    if not fichiers:
        print(f"   ⚠️ Aucun fichier dans {DECES_DIR}")
        print(f"   ℹ️  Téléchargez les fichiers sur data.gouv.fr/datasets/fichier-des-personnes-decedees")
        return [], []

    print(f"   📁 {len(fichiers)} fichiers")
    codes_cibles = set(COMMUNES.keys())
    tous_deces = []

    for fichier in fichiers:
        chemin = os.path.join(DECES_DIR, fichier)
        nb_trouves = 0
        with open(chemin, encoding="utf-8", errors="ignore") as f:
            for ligne in f:
                parsed = parser_ligne_deces(ligne)
                if parsed and parsed["code_commune_deces"] in codes_cibles:
                    parsed["commune"] = COMMUNES[parsed["code_commune_deces"]]
                    parsed["fichier_source"] = fichier
                    tous_deces.append(parsed)
                    nb_trouves += 1
        print(f"   📄 {fichier} → {nb_trouves} décès")

    tous_deces.sort(key=lambda x: x.get("date_deces_raw", ""), reverse=True)

    hist = charger_historique("deces_vus.json")
    nouveaux = []
    for d in tous_deces:
        cle = f"{d['nom']}_{d['prenom']}_{d['date_deces_raw']}_{d['code_commune_deces']}"
        if cle not in hist:
            nouveaux.append(d)
            hist[cle] = {
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                "commune": d["commune"],
                "date_deces": d["date_deces"],
            }
    sauvegarder_historique("deces_vus.json", hist)
    sauvegarder("deces.json", tous_deces)
    sauvegarder("deces_nouveaux.json", nouveaux)

    print(f"\n   Résumé par commune :")
    for code, nom in COMMUNES.items():
        nb = len([d for d in tous_deces if d["code_commune_deces"] == code])
        nb_new = len([d for d in nouveaux if d["code_commune_deces"] == code])
        if nb > 0:
            print(f"   → {nom} : {nb} décès · {nb_new} nouveaux")

    print(f"   💾 {len(tous_deces)} décès totaux · {len(nouveaux)} nouveaux")
    return tous_deces, nouveaux

# ============================================
# 4. STATS DVF
# ============================================

def calculer_stats(dvf):
    print("\n📈 Calcul des statistiques...")
    stats = {}
    for nom in COMMUNES.values():
        tc = [t for t in dvf if t["commune"] == nom]
        prix = [t["prix_m2"] for t in tc]
        maisons = [t for t in tc if t["type_local"] == "Maison"]
        apparts = [t for t in tc if t["type_local"] == "Appartement"]
        stats[nom] = {
            "nb_transactions": len(tc),
            "nb_maisons": len(maisons),
            "nb_appartements": len(apparts),
            "prix_m2_moyen": round(sum(prix)/len(prix), 0) if prix else 0,
            "prix_median": sorted(prix)[len(prix)//2] if prix else 0,
            "prix_m2_maisons": round(sum(t["prix_m2"] for t in maisons)/len(maisons), 0) if maisons else 0,
            "prix_m2_apparts": round(sum(t["prix_m2"] for t in apparts)/len(apparts), 0) if apparts else 0,
        }
        print(f"   → {nom} : {len(tc)} transactions · {stats[nom]['prix_m2_moyen']} €/m²")
    sauvegarder("stats.json", stats)
    return stats

# ============================================
# 5. RAPPORT FINAL
# ============================================

def generer_rapport(dvf, bodacc, deces, stats, new_dvf, new_bodacc, new_deces):
    rapport = {
        "date_collecte": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "communes": list(COMMUNES.values()),
        "stats": {
            "transactions_dvf": len(dvf),
            "annonces_bodacc": len(bodacc),
            "deces_insee": len(deces),
        },
        "nouveautes": {
            "dvf": len(new_dvf),
            "bodacc": len(new_bodacc),
            "deces": len(new_deces),
            "total": len(new_dvf) + len(new_bodacc) + len(new_deces),
        },
        "marche": stats,
        "transactions_recentes": dvf[:20],
        "annonces_recentes": bodacc[:20],
        "deces_recents": deces[:20],
        "nouvelles_dvf": new_dvf[:10],
        "nouveaux_bodacc": new_bodacc[:10],
        "nouveaux_deces": new_deces[:20],
    }
    sauvegarder("rapport.json", rapport)

    print(f"\n{'='*54}")
    print(f"✅ COLLECTE TERMINÉE — {rapport['date_collecte']}")
    print(f"{'='*54}")
    print(f"   📊 Transactions DVF   : {len(dvf)} ({len(new_dvf)} nouvelles)")
    print(f"   ⚖️  Annonces BODACC    : {len(bodacc)} ({len(new_bodacc)} nouvelles)")
    print(f"   ⚰️  Décès INSEE        : {len(deces)} ({len(new_deces)} nouveaux)")
    print(f"   🔔 Total nouveautés   : {rapport['nouveautes']['total']}")
    print(f"{'='*54}\n")

# ============================================
# LANCEMENT
# ============================================

if __name__ == "__main__":
    print("="*54)
    print("🏠 SENTINELLE IMMO — Collecteur v9")
    print(f"   Zone : Reims & environs (Marne 51)")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*54)

    dvf,    new_dvf    = collecter_dvf()
    bodacc, new_bodacc = collecter_bodacc()
    deces,  new_deces  = collecter_deces()
    stats              = calculer_stats(dvf)
    generer_rapport(dvf, bodacc, deces, stats, new_dvf, new_bodacc, new_deces)
