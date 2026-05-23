import requests
import json
import os
import time
import re
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================
# SENTINELLE IMMO — Collecteur Judiciaire v3
# TJ Reims + TJ Châlons-en-Champagne
# ============================================

OUTPUT_DIR = "donnees"
HISTORIQUE_DIR = "historique"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORIQUE_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "fr-FR,fr;q=0.9",
}

# URLs directes des pages tribunal sur Licitor
URLS_TRIBUNAUX = [
    {"nom": "TJ Châlons-en-Champagne", "url": "https://www.licitor.com/ventes/10/marne/chalons-en-champagne"},
    {"nom": "TJ Reims",                "url": "https://www.licitor.com/ventes/10/marne/reims"},
]

def extraire_info_url(url):
    """Extrait titre, commune, type depuis l'URL Licitor."""
    # Format : /annonce/10/84/13/vente-aux-encheres/une-maison-d-habitation/montmirail/marne/108413.html
    parts = url.rstrip('/').split('/')
    info = {"url": url}
    try:
        # Le type de bien est après "vente-aux-encheres"
        idx = parts.index("vente-aux-encheres")
        type_bien = parts[idx + 1].replace("-", " ").capitalize() if idx + 1 < len(parts) else ""
        commune   = parts[idx + 2].replace("-", " ").capitalize() if idx + 2 < len(parts) else ""
        info["titre"]   = type_bien
        info["commune"] = commune
    except (ValueError, IndexError):
        pass
    return info

def get_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.encoding = "utf-8"
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"   ❌ Erreur {url} : {e}")
    return None

def parser_detail(url):
    """Parse le détail d'une annonce Licitor pour récupérer mise à prix, surface, date audience."""
    soup = get_page(url)
    if not soup:
        return {}

    detail = {}
    texte = soup.get_text(" ", strip=True)

    # Mise à prix
    prix = re.findall(r'([0-9][0-9\s\.]+)\s*€', texte)
    for p in prix:
        val = int(p.replace(" ", "").replace(".", ""))
        if 5000 < val < 2000000:
            detail["mise_a_prix"] = val
            break

    # Surface
    surfaces = re.findall(r'(\d+[\.,]?\d*)\s*m[²2]', texte)
    if surfaces:
        detail["surface"] = surfaces[0].replace(",", ".") + " m²"

    # Date audience
    dates = re.findall(r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})', texte)
    if dates:
        detail["date_audience"] = dates[0]

    # Description courte
    for tag in soup.find_all(["p", "td", "div"]):
        t = tag.get_text(strip=True)
        if len(t) > 60 and any(m in t.lower() for m in ["maison", "appartement", "local", "terrain", "habitation", "bien"]):
            detail["description"] = t[:250]
            break

    return detail

def collecter_licitor():
    print("\n🏛️  Collecteur Judiciaire v3 — TJ Reims & Châlons...")
    resultats = []

    for tj in URLS_TRIBUNAUX:
        print(f"\n   📋 {tj['nom']}...")
        time.sleep(1)

        soup = get_page(tj["url"])
        if not soup:
            print(f"   ⚠️  Page inaccessible")
            continue

        # Cherche tous les liens /annonce/
        liens = soup.find_all("a", href=True)
        urls_annonces = set()
        for lien in liens:
            href = lien.get("href", "")
            if "/annonce/" in href:
                url_complet = "https://www.licitor.com" + href if href.startswith("/") else href
                urls_annonces.add(url_complet)

        print(f"   → {len(urls_annonces)} annonces trouvées")

        for url_annonce in urls_annonces:
            time.sleep(0.8)
            info = extraire_info_url(url_annonce)
            detail = parser_detail(url_annonce)

            resultats.append({
                "tribunal": tj["nom"],
                "titre": info.get("titre", "Bien immobilier"),
                "commune": info.get("commune", ""),
                "url": url_annonce,
                "mise_a_prix": detail.get("mise_a_prix", 0),
                "surface": detail.get("surface", ""),
                "date_audience": detail.get("date_audience", ""),
                "description": detail.get("description", ""),
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            })
            print(f"   ✅ {info.get('titre','?')} — {info.get('commune','?')} · {detail.get('mise_a_prix','?')} €")

    # Détection nouveautés
    hist_path = os.path.join(HISTORIQUE_DIR, "licitor_vus.json")
    historique = {}
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            historique = json.load(f)

    nouveaux = []
    for item in resultats:
        cle = item["url"]
        if cle not in historique:
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
    print("="*52)
    print("🏛️  SENTINELLE IMMO — Collecteur Judiciaire v3")
    print(f"   Tribunaux : Reims + Châlons-en-Champagne")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    collecter_licitor()
