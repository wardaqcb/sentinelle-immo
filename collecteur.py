import requests
import json
import os
import csv
import io
import zipfile
import re
import time
from datetime import datetime
from difflib import SequenceMatcher
from collections import Counter
from bs4 import BeautifulSoup

# ============================================================
# SENTINELLE IMMO — Collecteur v11
# Sources  : DVF multi-années · BODACC SCI · Décès INSEE
#            Licitor · DPE ADEME · MAJIC DGFiP
# Croisements : DPE×DVF · MAJIC×DPE · Triple DPE×DVF×MAJIC
# ============================================================

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
COMMUNES_upper = {v.upper() for v in COMMUNES.keys()}

OUTPUT_DIR     = "donnees"
CACHE_DIR      = "cache"
DECES_DIR      = os.path.join("cache", "deces")
HISTORIQUE_DIR = "historique"
for d in [OUTPUT_DIR, CACHE_DIR, DECES_DIR, HISTORIQUE_DIR]:
    os.makedirs(d, exist_ok=True)

DVF_URLS = {
    2021: "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002223/valeursfoncieres-2021.txt.zip",
    2022: "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002236/valeursfoncieres-2022.txt.zip",
    2023: "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002251/valeursfoncieres-2023.txt.zip",
    2024: "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002306/valeursfoncieres-2024.txt.zip",
    2025: "https://static.data.gouv.fr/resources/demandes-de-valeurs-foncieres/20260405-002321/valeursfoncieres-2025.txt.zip",
}

BASE_DPE  = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines"
BASE_BODACC = "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records"
TRIBUNAUX = ["reims", "chalons-en-champagne"]
HEADERS_HTTP = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

MAJIC_LOCAUX    = os.path.join(CACHE_DIR, "PM_25_B_510.csv")
MAJIC_PARCELLES = os.path.join(CACHE_DIR, "PM_25_NB_510.csv")

MOTS_SCI = ["sci ", "s.c.i", "sci.", "societe civile immo", "société civile immo", "societe civile", "société civile"]

# ============================================================
# UTILITAIRES
# ============================================================

def charger_hist(nom):
    p = os.path.join(HISTORIQUE_DIR, nom)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}

def sauver_hist(nom, data):
    with open(os.path.join(HISTORIQUE_DIR, nom), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def sauver(nom, data):
    with open(os.path.join(OUTPUT_DIR, nom), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def formater_date(raw):
    try:
        if len(raw) == 8 and raw.isdigit():
            a, m, j = raw[:4], raw[4:6], raw[6:8]
            if m == "00": m = "01"
            if j == "00": j = "01"
            return f"{j}/{m}/{a}"
    except: pass
    return raw

def normaliser_adresse(adresse):
    if not adresse: return "", ""
    a = adresse.lower().strip()
    a = re.sub(r'\b5\d{4}\b', '', a)
    for ville in ["reims","tinqueux","gueux","muizon","hermonville","courcy","saint-thierry","pouillon"]:
        a = re.sub(r'\b'+ville+r'\b', '', a)
    remplacements = [("\\ball\\b","allee"),("\\bav\\b","avenue"),("\\bbd\\b","boulevard"),
                     ("\\bbvd\\b","boulevard"),("\\bpl\\b","place"),("\\bimp\\b","impasse"),("\\besp\\b","esplanade")]
    for pattern, remplacement in remplacements:
        a = re.sub(pattern, remplacement, a)
    a = re.sub(r'\b0+(\d)', r'\1', a)
    a = re.sub(r'[^\w\s]', ' ', a)
    a = re.sub(r'\s+', ' ', a).strip()
    match = re.match(r'^(\d+)\s*(.*)', a)
    if match:
        return match.group(1), match.group(2).strip()
    return "", a

def est_sci(forme, groupe, denomination):
    texte = (forme + " " + groupe + " " + denomination).lower()
    return any(mot in texte for mot in MOTS_SCI)

# ============================================================
# 1. DVF MULTI-ANNÉES
# ============================================================

def detecter_annees_dvf():
    annee_min = 2025
    dpe_path = os.path.join(OUTPUT_DIR, "dpe.json")
    if os.path.exists(dpe_path):
        with open(dpe_path, encoding="utf-8") as f:
            dpe_data = json.load(f)
        dates = [d.get("date_dpe","") for d in dpe_data if d.get("date_dpe")]
        if dates:
            annee_min = int(min(dates)[:4])
            print(f"   ℹ️  DPE le plus ancien : {min(dates)} → DVF depuis {annee_min}")
    return list(range(annee_min, 2026))

def telecharger_dvf(annee):
    cache_path = os.path.join(CACHE_DIR, f"valeursfoncieres-{annee}.zip")
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 10*1024*1024:
        print(f"   ✅ DVF {annee} en cache ({os.path.getsize(cache_path)//1024//1024} Mo)")
        return cache_path
    url = DVF_URLS.get(annee)
    if not url: return None
    print(f"   ⬇️  Téléchargement DVF {annee}...")
    try:
        r = requests.get(url, timeout=300, stream=True)
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(cache_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                f.write(chunk)
                downloaded += len(chunk)
                if total: print(f"   ⬇️  {int(downloaded/total*100)}%", end="\r")
        print(f"\n   ✅ DVF {annee} téléchargé")
        return cache_path
    except Exception as e:
        print(f"   ❌ {e}")
        return None

def parser_dvf(cache_path, annee):
    codes = set(COMMUNES.values())
    noms = {v: k for k, v in COMMUNES.items()}
    resultats = []
    try:
        with zipfile.ZipFile(cache_path) as z:
            with z.open(z.namelist()[0]) as f:
                contenu = f.read().decode("utf-8", errors="ignore")
        reader = csv.DictReader(io.StringIO(contenu), delimiter="|")
        for row in reader:
            dept    = row.get("Code departement","").strip().zfill(2)
            commune = row.get("Code commune","").strip().zfill(3)
            code    = dept + commune
            if code not in codes: continue
            try:
                valeur  = float(row.get("Valeur fonciere","0").replace(",",".").replace(" ","") or "0")
                surface = float(row.get("Surface reelle bati","0").replace(",",".").replace(" ","") or "0")
                type_local = row.get("Type local","").strip()
                prix_m2 = round(valeur/surface, 0) if surface > 0 else 0
                if valeur > 0 and surface >= 15 and type_local in ["Maison","Appartement"] and 500 <= prix_m2 <= 15000:
                    resultats.append({
                        "commune": noms.get(code, code),
                        "code_insee": code,
                        "annee": annee,
                        "date_mutation": row.get("Date mutation",""),
                        "valeur_fonciere": valeur,
                        "surface_bati": surface,
                        "prix_m2": prix_m2,
                        "type_local": type_local,
                        "nombre_pieces": row.get("Nombre pieces principales",""),
                        "adresse": (row.get("No voie","")+" "+row.get("Voie","")).strip(),
                        "nature_mutation": row.get("Nature mutation",""),
                    })
            except: continue
    except Exception as e:
        print(f"   ❌ Parsing DVF {annee} : {e}")
    return resultats

def collecter_dvf():
    print("\n📊 Collecte DVF multi-années...")
    annees = detecter_annees_dvf()
    print(f"   → Années : {annees}")
    tous = []
    par_annee = {}
    for annee in annees:
        cache = telecharger_dvf(annee)
        if not cache: continue
        print(f"   📦 Parsing {annee}...", end=" ")
        transactions = parser_dvf(cache, annee)
        par_annee[annee] = transactions
        tous.extend(transactions)
        print(f"{len(transactions)} transactions")
    tous.sort(key=lambda x: x["date_mutation"], reverse=True)
    hist = charger_hist("dvf_vus.json")
    nouveaux = []
    for t in tous:
        cle = f"{t['commune']}_{t['adresse']}_{t['date_mutation']}_{t['valeur_fonciere']}"
        if cle not in hist:
            nouveaux.append(t)
            hist[cle] = {"date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M")}
    sauver_hist("dvf_vus.json", hist)
    sauver("dvf.json", tous)
    sauver("dvf_nouveaux.json", nouveaux)
    print(f"   💾 {len(tous)} transactions · {len(nouveaux)} nouvelles")
    return tous, nouveaux

# ============================================================
# 2. BODACC SCI
# ============================================================

def extraire_adresse_bodacc(a):
    try:
        etabs = a.get("listeetablissements","")
        if isinstance(etabs, str) and etabs:
            etabs = json.loads(etabs)
        if isinstance(etabs, dict):
            etab = etabs.get("etablissement", etabs)
            if isinstance(etab, list): etab = etab[0]
            adr = etab.get("adresse",{})
            if adr:
                return f"{adr.get('numeroVoie','')} {adr.get('typeVoie','')} {adr.get('nomVoie','')} {adr.get('codePostal','')} {adr.get('ville','')}".strip()
    except: pass
    return ""

def extraire_prix_bodacc(a):
    try:
        etabs = a.get("listeetablissements","")
        if isinstance(etabs, str) and etabs:
            etabs = json.loads(etabs)
        if isinstance(etabs, dict):
            etab = etabs.get("etablissement", etabs)
            if isinstance(etab, list): etab = etab[0]
            origine = etab.get("origineFonds","")
            match = re.search(r'(\d[\d\s]*)\s*EUR', origine)
            if match: return int(match.group(1).replace(" ",""))
    except: pass
    return None

def collecter_bodacc():
    print("\n⚖️  Collecte BODACC SCI...")
    toutes = []
    REQUETES = [
        {"label": "Procédures collectives", "where": "tribunal like 'Reims' and dateparution >= '2024-01-01' and familleavis_lib like 'Procédures collectives'"},
        {"label": "Ventes et cessions SCI", "where": "tribunal like 'Reims' and dateparution >= '2024-01-01' and familleavis_lib like 'Ventes et cessions' and (commercant like 'SCI' or commercant like 'societe civile' or commercant like 'société civile')"},
    ]
    for req in REQUETES:
        print(f"   📋 {req['label']}...", end=" ")
        offset = 0
        while True:
            try:
                r = requests.get(BASE_BODACC, params={"where": req["where"], "limit": 100, "offset": offset, "order_by": "dateparution desc"}, timeout=15)
                if r.status_code != 200: break
                data = r.json()
                annonces = data.get("results",[])
                total = data.get("total_count",0)
                if offset == 0: print(f"{total} annonces")
                for a in annonces:
                    registre = a.get("registre",[])
                    siren = ""
                    if isinstance(registre, list):
                        for reg in registre:
                            reg = str(reg).replace(" ","").strip()
                            if len(reg)==9 and reg.isdigit(): siren = reg; break
                    toutes.append({
                        "id": a.get("id",""),
                        "famille": a.get("familleavis_lib",""),
                        "type": a.get("typeavis_lib",""),
                        "date": a.get("dateparution",""),
                        "description": a.get("commercant",""),
                        "tribunal": a.get("tribunal",""),
                        "ville": a.get("ville",""),
                        "cp": a.get("cp",""),
                        "adresse": extraire_adresse_bodacc(a),
                        "prix_cession": extraire_prix_bodacc(a),
                        "siren": siren,
                        "url": a.get("url_complete",""),
                    })
                offset += 100
                if offset >= total or not annonces: break
            except Exception as e:
                print(f"   ❌ {e}"); break

    # Filtre strict
    resultats = []
    for a in toutes:
        famille = (a.get("famille","") or "").lower()
        desc = (a.get("description","") or "").lower().strip()
        sci = desc.startswith("sci ") or desc.startswith("s.c.i") or "societe civile immo" in desc or "société civile immo" in desc or " sci " in desc
        judiciaire = any(mot in famille for mot in ["liquid","redress","proc","collectif"])
        cession_sci = "vente" in famille and sci
        if sci or judiciaire or cession_sci:
            resultats.append(a)

    resultats.sort(key=lambda x: x.get("date",""), reverse=True)
    hist = charger_hist("bodacc_vus.json")
    nouveaux = []
    for a in resultats:
        cle = a.get("id","")
        if cle and cle not in hist:
            nouveaux.append(a)
            hist[cle] = {"date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M")}
    sauver_hist("bodacc_vus.json", hist)
    sauver("bodacc.json", resultats)
    sauver("bodacc_nouveaux.json", nouveaux)
    print(f"   💾 {len(resultats)} annonces · {len(nouveaux)} nouvelles")
    return resultats, nouveaux

# ============================================================
# 3. DÉCÈS INSEE (silencieux — pour croisements futurs)
# ============================================================

def collecter_deces():
    print("\n⚰️  Collecte Décès INSEE (silencieux)...")
    fichiers = sorted([f for f in os.listdir(DECES_DIR) if f.endswith(".txt")])
    if not fichiers:
        print("   ℹ️  Aucun fichier décès")
        return [], []
    codes_cibles = set(COMMUNES.values())
    tous = []
    for fichier in fichiers:
        nb = 0
        with open(os.path.join(DECES_DIR, fichier), encoding="utf-8", errors="ignore") as f:
            for ligne in f:
                try:
                    if len(ligne) < 100 or "*" not in ligne[0:80]: continue
                    parties = ligne[0:80].strip().split("*",1)
                    nom = parties[0].strip()
                    prenom = parties[1].replace("/","").strip()
                    sexe = "M" if ligne[80:81].strip()=="1" else "F"
                    naiss_raw = ligne[81:89].strip()
                    code_deces = ligne[89:94].strip()
                    deces_raw = ligne[152:160].strip()
                    if code_deces in codes_cibles:
                        age = None
                        try: age = int(deces_raw[:4]) - int(naiss_raw[:4])
                        except: pass
                        tous.append({"nom":nom,"prenom":prenom,"sexe":sexe,
                                     "date_naissance":formater_date(naiss_raw),
                                     "date_deces":formater_date(deces_raw),
                                     "date_deces_raw":deces_raw,
                                     "code_commune_deces":code_deces,
                                     "commune":COMMUNES[code_deces],
                                     "age_deces":age,"fichier_source":fichier})
                        nb += 1
                except: continue
        print(f"   📄 {fichier} → {nb} décès")
    tous.sort(key=lambda x: x.get("date_deces_raw",""), reverse=True)
    hist = charger_hist("deces_vus.json")
    nouveaux = []
    for d in tous:
        cle = f"{d['nom']}_{d['prenom']}_{d['date_deces_raw']}_{d['code_commune_deces']}"
        if cle not in hist:
            nouveaux.append(d)
            hist[cle] = {"date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M")}
    sauver_hist("deces_vus.json", hist)
    sauver("deces.json", tous)
    sauver("deces_nouveaux.json", nouveaux)
    print(f"   💾 {len(tous)} décès · {len(nouveaux)} nouveaux")
    return tous, nouveaux

# ============================================================
# 4. LICITOR — Ventes judiciaires
# ============================================================

def collecter_licitor():
    print("\n🏛️  Collecte Licitor...")
    resultats = []
    try:
        soup = BeautifulSoup(requests.get("https://www.licitor.com/", headers=HEADERS_HTTP, timeout=15).text, "html.parser")
        urls_trouvees = {}
        for lien in soup.find_all("a", href=True):
            href = lien.get("href","")
            texte = lien.get_text().strip()
            for cible in TRIBUNAUX:
                if cible in href.lower() and href.startswith("/ventes"):
                    urls_trouvees[cible] = {"nom": texte.split("\n")[0].strip(), "url": "https://www.licitor.com"+href}
        if not urls_trouvees:
            print("   ℹ️  Aucune vente programmée sur les TJ cibles")
        else:
            for cible, info in urls_trouvees.items():
                print(f"   ✅ {info['nom']}")
                time.sleep(1)
                soup_tj = BeautifulSoup(requests.get(info["url"], headers=HEADERS_HTTP, timeout=15).text, "html.parser")
                for lien in soup_tj.find_all("a", href=True):
                    href = lien.get("href","")
                    if "/annonce/" in href:
                        resultats.append({"tribunal": info["nom"], "url": "https://www.licitor.com"+href if href.startswith("/") else href, "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M")})
    except Exception as e:
        print(f"   ❌ {e}")
    hist = charger_hist("licitor_vus.json")
    nouveaux = []
    for item in resultats:
        cle = item.get("url","")
        if cle and cle not in hist:
            nouveaux.append(item)
            hist[cle] = {"date_detection": item["date_detection"]}
    sauver_hist("licitor_vus.json", hist)
    sauver("judiciaire.json", resultats)
    sauver("judiciaire_nouveaux.json", nouveaux)
    print(f"   💾 {len(resultats)} ventes · {len(nouveaux)} nouvelles")
    return resultats, nouveaux

# ============================================================
# 5. DPE ADEME
# ============================================================

def collecter_dpe():
    print("\n🔋 Collecte DPE ADEME...")
    tous = []
    for commune, code_insee in COMMUNES.items():
        try:
            r = requests.get(BASE_DPE, params={
                "size": 10000,
                "qs": f"etiquette_dpe:(F OR G) AND code_insee_ban:{code_insee}",
                "select": "numero_dpe,adresse_ban,nom_commune_ban,code_insee_ban,etiquette_dpe,etiquette_ges,surface_habitable_immeuble,type_batiment,date_etablissement_dpe,date_fin_validite_dpe,periode_construction",
                "sort": "-date_etablissement_dpe",
            }, timeout=30)
            if r.status_code != 200: continue
            data = r.json()
            total = data.get("total",0)
            for item in data.get("results",[]):
                tous.append({
                    "commune": commune,
                    "code_insee": code_insee,
                    "numero_dpe": item.get("numero_dpe",""),
                    "adresse": item.get("adresse_ban",""),
                    "etiquette_dpe": item.get("etiquette_dpe",""),
                    "etiquette_ges": item.get("etiquette_ges",""),
                    "surface": item.get("surface_habitable_immeuble",""),
                    "type_batiment": item.get("type_batiment",""),
                    "date_dpe": item.get("date_etablissement_dpe","")[:10] if item.get("date_etablissement_dpe") else "",
                    "date_fin_validite": item.get("date_fin_validite_dpe","")[:10] if item.get("date_fin_validite_dpe") else "",
                    "periode_construction": item.get("periode_construction",""),
                    "total_commune": total,
                })
            print(f"   → {commune} : {total} passoires F/G")
        except Exception as e:
            print(f"   ❌ {commune} : {e}")
    tous.sort(key=lambda x: x.get("date_dpe",""), reverse=True)
    hist = charger_hist("dpe_vus.json")
    nouveaux = []
    for d in tous:
        cle = d.get("numero_dpe","")
        if cle and cle not in hist:
            nouveaux.append(d)
            hist[cle] = {"date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M")}
    sauver_hist("dpe_vus.json", hist)
    sauver("dpe.json", tous)
    sauver("dpe_nouveaux.json", nouveaux)
    print(f"   💾 {len(tous)} DPE · {len(nouveaux)} nouveaux")
    return tous, nouveaux

# ============================================================
# 6. MAJIC DGFiP
# ============================================================

def lire_majic(chemin, type_bien):
    resultats = []
    if not os.path.exists(chemin):
        print(f"   ⚠️  {chemin} introuvable")
        return []
    for enc in ["utf-8","latin-1","cp1252"]:
        try:
            with open(chemin, encoding=enc) as f:
                contenu = f.read()
            break
        except: contenu = None
    if not contenu: return []
    reader = csv.DictReader(io.StringIO(contenu), delimiter=";")
    nb = 0
    for row in reader:
        commune = row.get("Nom de la commune","").strip().upper()
        if commune not in COMMUNES_upper: continue
        forme = (row.get("Forme juridique abrégée - par") or row.get("Forme juridique abrégée") or "").strip()
        groupe = (row.get("Groupe personne - par") or row.get("Groupe personne") or "").strip()
        denomination = (row.get("Dénomination - par") or row.get("Dénomination") or "").strip()
        if not est_sci(forme, groupe, denomination): continue
        num_voirie = row.get("N° voirie","").strip()
        nature_voie = row.get("Nature voie","").strip()
        nom_voie = row.get("Nom voie","").strip()
        adresse = f"{num_voirie} {nature_voie} {nom_voie} {commune.title()}".strip()
        siren = (row.get("N° SIREN - par") or row.get("N° SIREN") or "").strip()
        resultats.append({
            "type_bien": type_bien,
            "commune": commune.title(),
            "adresse": adresse,
            "denomination": denomination,
            "forme_juridique": forme,
            "siren": siren,
            "source": "MAJIC DGFiP 2025",
        })
        nb += 1
    print(f"   → {type_bien} : {nb} SCI trouvées")
    return resultats

def collecter_majic():
    print("\n🏢 Collecte MAJIC DGFiP...")
    tous = []
    tous.extend(lire_majic(MAJIC_LOCAUX, "locaux"))
    tous.extend(lire_majic(MAJIC_PARCELLES, "parcelles"))
    vus = set()
    uniques = []
    for r in tous:
        cle = f"{r['denomination']}_{r['adresse']}"
        if cle not in vus:
            vus.add(cle)
            uniques.append(r)
    uniques.sort(key=lambda x: (x["commune"], x["denomination"]))
    hist = charger_hist("majic_vus.json")
    nouveaux = []
    for r in uniques:
        cle = f"{r['denomination']}_{r['adresse']}"
        if cle not in hist:
            nouveaux.append(r)
            hist[cle] = {"date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M")}
    sauver_hist("majic_vus.json", hist)
    sauver("majic.json", uniques)
    sauver("majic_nouveaux.json", nouveaux)
    communes = Counter([r["commune"] for r in uniques])
    for c, nb in communes.most_common():
        print(f"   → {c} : {nb} SCI")
    print(f"   💾 {len(uniques)} SCI · {len(nouveaux)} nouvelles")
    return uniques, nouveaux

# ============================================================
# 7. CROISEMENT DPE × DVF
# ============================================================

def croiser_dpe_dvf(tous_dvf, tous_dpe):
    print("\n🔗 Croisement DPE × DVF...")
    dvf_index = {}
    for t in tous_dvf:
        commune = t.get("commune","")
        num, rue = normaliser_adresse(t.get("adresse",""))
        if not rue: continue
        cle = f"{commune}_{num}_{rue[:20]}"
        if cle not in dvf_index: dvf_index[cle] = []
        dvf_index[cle].append(t)

    leads_propres = []
    leads_vendus  = []
    for d in tous_dpe:
        commune = d.get("commune","")
        num, rue = normaliser_adresse(d.get("adresse",""))
        date_dpe = d.get("date_dpe","")
        cle = f"{commune}_{num}_{rue[:20]}"
        vendu_apres = False
        transaction = None
        for t in dvf_index.get(cle,[]):
            if date_dpe and t.get("date_mutation","") > date_dpe:
                vendu_apres = True
                transaction = t
                break
        enrichi = {**d, "statut_croisement": "", "transaction_dvf": None}
        if vendu_apres:
            enrichi["statut_croisement"] = "vendu_apres_dpe"
            enrichi["transaction_dvf"] = {"adresse": transaction.get("adresse",""), "date": transaction.get("date_mutation",""), "valeur": transaction.get("valeur_fonciere",0)}
            leads_vendus.append(enrichi)
        else:
            enrichi["statut_croisement"] = "non_vendu"
            leads_propres.append(enrichi)

    sauver("dpe_leads_propres.json", leads_propres)
    sauver("dpe_leads_vendus.json", leads_vendus)
    print(f"   ✅ {len(leads_propres)} leads propres · {len(leads_vendus)} écartés")
    return leads_propres

# ============================================================
# 8. CROISEMENT MAJIC × DPE
# ============================================================

def croiser_majic_dpe(tous_majic, tous_dpe):
    print("\n🔗 Croisement MAJIC × DPE...")
    majic_index = {}
    for m in tous_majic:
        commune = m.get("commune","").upper()
        num, rue = normaliser_adresse(m.get("adresse",""))
        if not rue: continue
        for cle in [f"{commune}_{num}_{rue[:20]}", f"{commune}_{rue[:20]}"]:
            if cle not in majic_index: majic_index[cle] = []
            majic_index[cle].append(m)

    leads = []
    for d in tous_dpe:
        commune = d.get("commune","").upper()
        num, rue = normaliser_adresse(d.get("adresse",""))
        if not rue: continue
        cle = f"{commune}_{num}_{rue[:20]}"
        candidats = majic_index.get(cle,[])
        if not candidats:
            candidats2 = majic_index.get(f"{commune}_{rue[:20]}",[])
            candidats = [c for c in candidats2 if not num or normaliser_adresse(c.get("adresse",""))[0] == num]
        sirens_vus = set()
        for m in candidats:
            siren = m.get("siren","")
            if siren in sirens_vus: continue
            if siren: sirens_vus.add(siren)
            leads.append({
                "source_croisement": "MAJIC × DPE",
                "adresse": d.get("adresse",""),
                "commune": d.get("commune",""),
                "etiquette_dpe": d.get("etiquette_dpe",""),
                "surface": d.get("surface",""),
                "type_batiment": d.get("type_batiment",""),
                "date_dpe": d.get("date_dpe",""),
                "sci_denomination": m.get("denomination",""),
                "sci_siren": siren,
                "sci_forme_juridique": m.get("forme_juridique",""),
                "type_bien": m.get("type_bien",""),
                "pappers_url": f"https://pappers.fr/entreprise/{siren}" if siren else "",
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            })

    sauver("leads_majic_dpe.json", leads)
    print(f"   ✅ {len(leads)} leads MAJIC × DPE")
    return leads

# ============================================================
# 9. TRIPLE CROISEMENT DPE × DVF × MAJIC
# ============================================================

def croiser_triple(leads_dpe_dvf, leads_majic_dpe):
    print("\n🔗 Triple croisement DPE × DVF × MAJIC...")
    majic_index = {}
    for m in leads_majic_dpe:
        commune = m.get("commune","").upper()
        num, rue = normaliser_adresse(m.get("adresse",""))
        cle = f"{commune}_{num}_{rue[:25]}"
        if cle not in majic_index: majic_index[cle] = []
        majic_index[cle].append(m)

    leads = []
    for d in leads_dpe_dvf:
        commune = d.get("commune","").upper()
        num, rue = normaliser_adresse(d.get("adresse",""))
        cle = f"{commune}_{num}_{rue[:25]}"
        candidats = majic_index.get(cle,[])
        sirens_vus = set()
        for m in candidats:
            siren = m.get("sci_siren","")
            if siren in sirens_vus: continue
            if siren: sirens_vus.add(siren)
            leads.append({
                "source": "DPE × DVF × MAJIC",
                "adresse": d.get("adresse",""),
                "commune": d.get("commune",""),
                "etiquette_dpe": d.get("etiquette_dpe",""),
                "surface": d.get("surface",""),
                "type_batiment": d.get("type_batiment",""),
                "date_dpe": d.get("date_dpe",""),
                "statut_croisement": "non_vendu",
                "sci_denomination": m.get("sci_denomination",""),
                "sci_siren": siren,
                "pappers_url": f"https://pappers.fr/entreprise/{siren}" if siren else "",
                "signal": f"Passoire {d.get('etiquette_dpe','')} · Non vendue · SCI identifiée",
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            })

    leads.sort(key=lambda x: (0 if x["etiquette_dpe"]=="G" else 1, x["date_dpe"]))
    sauver("leads_triple.json", leads)
    print(f"   ✅ {len(leads)} leads béton")
    classes = Counter([l["etiquette_dpe"] for l in leads])
    for c, nb in classes.most_common():
        print(f"   → Classe {c} : {nb} leads")
    return leads

# ============================================================
# 10. STATS MARCHÉ
# ============================================================

def calculer_stats(tous_dvf):
    print("\n📈 Statistiques marché (2025)...")
    dvf_2025 = [t for t in tous_dvf if t.get("annee")==2025]
    stats = {}
    for commune in COMMUNES.keys():
        tc = [t for t in dvf_2025 if t["commune"]==commune]
        prix = [t["prix_m2"] for t in tc]
        maisons = [t for t in tc if t["type_local"]=="Maison"]
        apparts  = [t for t in tc if t["type_local"]=="Appartement"]
        stats[commune] = {
            "nb_transactions": len(tc),
            "nb_maisons": len(maisons),
            "nb_appartements": len(apparts),
            "prix_m2_moyen": round(sum(prix)/len(prix),0) if prix else 0,
            "prix_median": sorted(prix)[len(prix)//2] if prix else 0,
            "prix_m2_maisons": round(sum(t["prix_m2"] for t in maisons)/len(maisons),0) if maisons else 0,
            "prix_m2_apparts": round(sum(t["prix_m2"] for t in apparts)/len(apparts),0) if apparts else 0,
        }
        print(f"   → {commune} : {len(tc)} transactions · {stats[commune]['prix_m2_moyen']} €/m²")
    sauver("stats.json", stats)
    return stats

# ============================================================
# 11. RAPPORT FINAL
# ============================================================

def generer_rapport(tous_dvf, bodacc, deces, judiciaire, dpe, majic,
                    leads_propres, leads_majic_dpe, leads_triple, stats,
                    new_dvf, new_bodacc, new_deces, new_judiciaire, new_dpe, new_majic):
    dvf_2025 = [t for t in tous_dvf if t.get("annee")==2025]
    rapport = {
        "date_collecte": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "communes": list(COMMUNES.keys()),
        "stats": {
            "transactions_dvf_total": len(tous_dvf),
            "transactions_dvf_2025": len(dvf_2025),
            "annonces_bodacc": len(bodacc),
            "deces_insee": len(deces),
            "ventes_judiciaires": len(judiciaire),
            "dpe_passoires": len(dpe),
            "sci_majic": len(majic),
            "leads_dpe_dvf": len(leads_propres),
            "leads_majic_dpe": len(leads_majic_dpe),
            "leads_triple": len(leads_triple),
        },
        "nouveautes": {
            "dvf": len(new_dvf),
            "bodacc": len(new_bodacc),
            "deces": len(new_deces),
            "judiciaire": len(new_judiciaire),
            "dpe": len(new_dpe),
            "majic": len(new_majic),
            "total": len(new_dvf)+len(new_bodacc)+len(new_deces)+len(new_judiciaire)+len(new_dpe)+len(new_majic),
        },
        "marche": stats,
        "transactions_recentes": dvf_2025[:20],
        "annonces_bodacc": bodacc[:20],
        "judiciaire": judiciaire[:10],
        "leads_triple_top": leads_triple[:20],
        "leads_dpe_dvf_top": leads_propres[:20],
    }
    sauver("rapport.json", rapport)

    print(f"\n{'='*58}")
    print(f"✅ COLLECTE TERMINÉE — {rapport['date_collecte']}")
    print(f"{'='*58}")
    print(f"   📊 DVF total (2021-2025)     : {len(tous_dvf):>6} ({len(new_dvf)} nouveaux)")
    print(f"   ⚖️  BODACC SCI               : {len(bodacc):>6} ({len(new_bodacc)} nouveaux)")
    print(f"   ⚰️  Décès INSEE               : {len(deces):>6} ({len(new_deces)} nouveaux)")
    print(f"   🏛️  Ventes judiciaires        : {len(judiciaire):>6} ({len(new_judiciaire)} nouveaux)")
    print(f"   🔋 DPE passoires F/G         : {len(dpe):>6} ({len(new_dpe)} nouveaux)")
    print(f"   🏢 SCI MAJIC                 : {len(majic):>6} ({len(new_majic)} nouveaux)")
    print(f"{'='*58}")
    print(f"   🎯 Leads DPE × DVF           : {len(leads_propres):>6}")
    print(f"   🎯 Leads MAJIC × DPE         : {len(leads_majic_dpe):>6}")
    print(f"   🏆 Leads Triple (béton)      : {len(leads_triple):>6}")
    print(f"   🔔 Total nouveautés          : {rapport['nouveautes']['total']}")
    print(f"{'='*58}\n")

# ============================================================
# LANCEMENT
# ============================================================

if __name__ == "__main__":
    print("="*58)
    print("🏠 SENTINELLE IMMO — Collecteur v11")
    print(f"   Zone : Reims & environs (Marne 51)")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*58)

    tous_dvf,    new_dvf       = collecter_dvf()
    bodacc,      new_bodacc    = collecter_bodacc()
    deces,       new_deces     = collecter_deces()
    judiciaire,  new_judiciaire = collecter_licitor()
    dpe,         new_dpe       = collecter_dpe()
    majic,       new_majic     = collecter_majic()

    leads_propres   = croiser_dpe_dvf(tous_dvf, dpe)
    leads_majic_dpe = croiser_majic_dpe(majic, dpe)
    leads_triple    = croiser_triple(leads_propres, leads_majic_dpe)

    stats = calculer_stats(tous_dvf)
    generer_rapport(tous_dvf, bodacc, deces, judiciaire, dpe, majic,
                    leads_propres, leads_majic_dpe, leads_triple, stats,
                    new_dvf, new_bodacc, new_deces, new_judiciaire, new_dpe, new_majic)
