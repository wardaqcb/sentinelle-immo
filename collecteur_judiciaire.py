import requests
import json
import os
import time
from datetime import datetime
from bs4 import BeautifulSoup

# ============================================
# SENTINELLE IMMO — Collecteur Judiciaire v2
# TJ Reims + TJ Châlons-en-Champagne
# ============================================

OUTPUT_DIR = "donnees"
HISTORIQUE_DIR = "historique"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORIQUE_DIR, exist_ok=True)

TRIBUNAUX_CIBLES = ["reims", "chalons-en-champagne", "chalons"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9",
    "Referer": "https://www.licitor.com/",
}

def get_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"   ❌ Erreur {url} : {e}")
    return None

def parser_detail_vente(url_vente):
    """Parse le détail d'une page de vente Licitor."""
    soup = get_page(url_vente)
    if not soup:
        return {}

    details = {"url": url_vente}
    texte_complet = soup.get_text(" ", strip=True)

    # Cherche adresse, mise à prix, surface dans le texte
    import re

    # Mise à prix
    prix = re.findall(r'(\d[\d\s]*)\s*€', texte_complet)
    if prix:
        details["mise_a_prix_brut"] = prix[0].replace(" ", "")

    # Surface
    surface = re.findall(r'(\d+[\.,]?\d*)\s*m[²2]', texte_complet)
    if surface:
        details["surface"] = surface[0]

    # Texte principal (description)
    # Cherche les balises de description
    for tag in ["p", "div", "td"]:
        elements = soup.find_all(tag)
        for el in elements:
            t = el.get_text(strip=True)
            if len(t) > 50 and any(mot in t.lower() for mot in ["maison", "appartement", "immeuble", "local", "terrain", "habitation"]):
                details["description"] = t[:300]
                break
        if "description" in details:
            break

    return details

def collecter_licitor():
    print("\n🏛️  Collecteur Judiciaire — TJ Reims & Châlons...")
    resultats = []

    # Récupère la page principale
    soup = get_page("https://www.licitor.com/")
    if not soup:
        return [], []

    # Trouve tous les liens de tribunaux cibles
    liens = soup.find_all("a", href=True)
    urls_trouvees = {}

    for lien in liens:
        href = lien.get("href", "")
        texte = lien.get_text().strip()
        title = lien.get("title", "")

        for cible in TRIBUNAUX_CIBLES:
            if cible in href.lower() or cible in texte.lower() or cible in title.lower():
                nom = texte.split("\n")[0].strip()
                if nom and href.startswith("/ventes"):
                    urls_trouvees[cible] = {
                        "nom": nom,
                        "url": "https://www.licitor.com" + href,
                        "href": href,
                    }
                    print(f"   ✅ {nom} → {href}")

    if not urls_trouvees:
        print("   ℹ️  Aucune vente programmée sur les TJ cibles en ce moment")
        with open(os.path.join(OUTPUT_DIR, "judiciaire.json"), "w", encoding="utf-8") as f:
            json.dump([], f)
        with open(os.path.join(OUTPUT_DIR, "judiciaire_nouveaux.json"), "w", encoding="utf-8") as f:
            json.dump([], f)
        print("   💾 0 ventes · 0 nouvelles")
        return [], []

    # Pour chaque tribunal trouvé, parse les ventes
    for cible, info in urls_trouvees.items():
        print(f"\n   📋 Détail des ventes : {info['nom']}...")
        time.sleep(1)

        soup_tj = get_page(info["url"])
        if not soup_tj:
            continue

        # Cherche les biens listés
        texte = soup_tj.get_text(" ", strip=True)
        print(f"   Contenu ({len(texte)} chars) :")
        print(f"   {texte[:400]}")

        # Cherche les liens vers les biens individuels
        liens_biens = soup_tj.find_all("a", href=True)
        for lien in liens_biens:
            href = lien.get("href", "")
            if "/bien/" in href or "/annonce/" in href or "/lot/" in href:
                url_bien = "https://www.licitor.com" + href if href.startswith("/") else href
                print(f"   → Bien trouvé : {url_bien}")
                time.sleep(0.5)
                detail = parser_detail_vente(url_bien)
                resultats.append({
                    "tribunal": info["nom"],
                    "url_tribunal": info["url"],
                    "url_bien": url_bien,
                    "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                    **detail,
                })

        # Si pas de lien /bien/, sauvegarde quand même la vente globale
        if not any(r.get("tribunal") == info["nom"] for r in resultats):
            resultats.append({
                "tribunal": info["nom"],
                "url_tribunal": info["url"],
                "texte_page": texte[:500],
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            })

    # Détection nouveautés
    hist_path = os.path.join(HISTORIQUE_DIR, "licitor_vus.json")
    historique = {}
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            historique = json.load(f)

    nouveaux = []
    for item in resultats:
        cle = item.get("url_bien") or item.get("url_tribunal", "")
        if cle and cle not in historique:
            nouveaux.append(item)
            historique[cle] = {
                "date_detection": item["date_detection"],
                "tribunal": item["tribunal"],
            }

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
    print("🏛️  SENTINELLE IMMO — Collecteur Judiciaire v2")
    print(f"   Tribunaux : Reims + Châlons-en-Champagne")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    collecter_licitor()
