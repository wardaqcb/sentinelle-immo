import requests
import json
import os
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================
# SENTINELLE IMMO — Collecteur Judiciaire v4
# TJ Reims + TJ Châlons-en-Champagne
# Nouvelle structure URL Licitor (2026)
# ============================================

OUTPUT_DIR     = "donnees"
HISTORIQUE_DIR = "historique"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORIQUE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# Page France — liste tous les TJ avec leurs prochaines audiences
URL_FRANCE = "https://www.licitor.com/ventes-aux-encheres-immobilieres/france.html"

# Slugs des TJ ciblés (tels qu'ils apparaissent dans les URLs Licitor)
CIBLES_TJ = [
    {"slug": "tj-reims",                  "nom": "TJ Reims"},
    {"slug": "tj-chalons-en-champagne",   "nom": "TJ Châlons-en-Champagne"},
]

def get_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.encoding = "utf-8"
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"   ❌ Erreur GET {url} : {e}")
    return None

def extraire_info_url(url):
    """
    Extrait commune, type de bien et ID depuis une URL annonce Licitor.
    Format : /annonce/10/84/13/vente-aux-encheres/une-maison-d-habitation/montmirail/marne/108413.html
    """
    info = {"url": url}
    try:
        parts = url.rstrip("/").split("/")
        idx = parts.index("vente-aux-encheres")
        info["type_bien"] = parts[idx + 1].replace("-", " ").capitalize()
        info["commune"]   = parts[idx + 2].replace("-", " ").capitalize()
        info["dept"]      = parts[idx + 3] if idx + 3 < len(parts) else ""
        id_part = parts[-1].replace(".html", "")
        info["id"]        = id_part if id_part.isdigit() else ""
    except (ValueError, IndexError):
        pass
    return info

def parser_detail_annonce(url):
    """Parse le détail d'une page annonce pour récupérer mise à prix, surface, description."""
    soup = get_page(url)
    if not soup:
        return {}
    detail = {}
    texte = soup.get_text(" ", strip=True)

    # Mise à prix
    for m in re.finditer(r'([0-9][\d\s]+)\s*€', texte):
        val = int(m.group(1).replace(" ", ""))
        if 5_000 < val < 5_000_000:
            detail["mise_a_prix"] = val
            break

    # Surface
    m = re.search(r'(\d+[\.,]?\d*)\s*m[²2]', texte)
    if m:
        detail["surface"] = m.group(1).replace(",", ".") + " m²"

    # Description courte (premier bloc de texte pertinent)
    for tag in soup.find_all(["p", "li", "div"]):
        t = tag.get_text(strip=True)
        if len(t) > 80 and any(w in t.lower() for w in ["maison", "appartement", "terrain", "local", "immeuble", "habitation"]):
            detail["description"] = t[:300]
            break

    return detail

def collecter_licitor():
    print("\n🏛️  Collecteur Judiciaire v4 — TJ Reims & Châlons...")
    resultats = []

    # Étape 1 : page France → trouver les liens d'audience pour nos TJs
    print(f"\n   📡 Lecture de la page France Licitor...")
    soup_france = get_page(URL_FRANCE)
    if not soup_france:
        print("   ❌ Impossible d'atteindre la page France")
        return [], []

    # Cherche les liens href contenant nos slugs
    urls_tj = {}
    for lien in soup_france.find_all("a", href=True):
        href = lien.get("href", "")
        for cible in CIBLES_TJ:
            if cible["slug"] in href and "ventes-judiciaires-immobilieres" in href:
                url_complet = "https://www.licitor.com" + href if href.startswith("/") else href
                if cible["slug"] not in urls_tj:
                    urls_tj[cible["slug"]] = {"nom": cible["nom"], "url": url_complet}
                    print(f"   ✅ {cible['nom']} trouvé → {url_complet}")

    for cible in CIBLES_TJ:
        if cible["slug"] not in urls_tj:
            print(f"   ℹ️  {cible['nom']} : aucune audience programmée en ce moment")

    if not urls_tj:
        print("   ℹ️  Aucune vente active sur les TJ ciblés")
        # Sauvegarde quand même un fichier vide propre
        sauver_resultats(resultats)
        return resultats, []

    # Étape 2 : pour chaque TJ trouvé, récupérer les annonces
    for slug, info in urls_tj.items():
        print(f"\n   📋 {info['nom']} → {info['url']}")
        time.sleep(1)

        soup_tj = get_page(info["url"])
        if not soup_tj:
            print(f"   ⚠️  Page inaccessible")
            continue

        # Récupère tous les liens /annonce/
        urls_annonces = []
        for lien in soup_tj.find_all("a", href=True):
            href = lien.get("href", "")
            if "/annonce/" in href and "vente-aux-encheres" in href:
                url_complet = "https://www.licitor.com" + href if href.startswith("/") else href
                if url_complet not in urls_annonces:
                    urls_annonces.append(url_complet)

        print(f"   → {len(urls_annonces)} annonces trouvées")

        for url_annonce in urls_annonces:
            time.sleep(0.8)
            meta  = extraire_info_url(url_annonce)
            detail = parser_detail_annonce(url_annonce)

            annonce = {
                "id":              meta.get("id", ""),
                "tribunal":        info["nom"],
                "type_bien":       meta.get("type_bien", "Bien immobilier"),
                "commune":         meta.get("commune", ""),
                "url":             url_annonce,
                "mise_a_prix":     detail.get("mise_a_prix", 0),
                "surface":         detail.get("surface", ""),
                "description":     detail.get("description", ""),
                "date_detection":  datetime.now().strftime("%d/%m/%Y à %H:%M"),
            }
            resultats.append(annonce)
            prix_str = f"{annonce['mise_a_prix']:,} €".replace(",", " ") if annonce["mise_a_prix"] else "NC"
            print(f"   ✅ {annonce['type_bien']} — {annonce['commune']} · {prix_str}")

    return sauver_resultats(resultats)

def sauver_resultats(resultats):
    # Détection nouveautés
    hist_path = os.path.join(HISTORIQUE_DIR, "licitor_vus.json")
    historique = {}
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            historique = json.load(f)

    nouveaux = []
    for item in resultats:
        cle = item.get("url", "")
        if cle and cle not in historique:
            nouveaux.append(item)
            historique[cle] = {"date_detection": item["date_detection"]}

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "judiciaire.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "judiciaire_nouveaux.json"), "w", encoding="utf-8") as f:
        json.dump(nouveaux, f, ensure_ascii=False, indent=2)

    print(f"\n   💾 {len(resultats)} ventes · {len(nouveaux)} nouvelles")
    return resultats, nouveaux


if __name__ == "__main__":
    print("=" * 52)
    print("🏛️  SENTINELLE IMMO — Collecteur Judiciaire v4")
    print(f"   Tribunaux : Reims + Châlons-en-Champagne")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("=" * 52)
    collecter_licitor()
