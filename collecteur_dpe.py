import requests
import json
import os
from datetime import datetime

# ============================================
# SENTINELLE IMMO — Collecteur DPE ADEME
# Passoires thermiques F/G — vendeurs sous pression
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

OUTPUT_DIR = "donnees"
HISTORIQUE_DIR = "historique"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HISTORIQUE_DIR, exist_ok=True)

BASE_URL = "https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines"

def collecter_dpe():
    print("\n🔋 Collecte DPE — Passoires thermiques F/G...")
    tous_dpe = []

    for commune, code_insee in COMMUNES.items():
        print(f"\n   📍 {commune} ({code_insee})...")
        try:
            r = requests.get(BASE_URL, params={
                "size": 10000,
                "qs": f"etiquette_dpe:(F OR G) AND code_insee_ban:{code_insee}",
                "select": "numero_dpe,adresse_ban,nom_commune_ban,code_insee_ban,etiquette_dpe,etiquette_ges,surface_habitable_immeuble,type_batiment,date_etablissement_dpe,date_fin_validite_dpe,periode_construction",
                "sort": "-date_etablissement_dpe",
            }, timeout=15)

            if r.status_code != 200:
                print(f"   ❌ Erreur {r.status_code}")
                continue

            data = r.json()
            total = data.get("total", 0)
            resultats = data.get("results", [])

            print(f"   → {total} passoires F/G · {len(resultats)} récupérées")

            for item in resultats:
                tous_dpe.append({
                    "commune": commune,
                    "code_insee": code_insee,
                    "numero_dpe": item.get("numero_dpe", ""),
                    "adresse": item.get("adresse_ban", ""),
                    "etiquette_dpe": item.get("etiquette_dpe", ""),
                    "etiquette_ges": item.get("etiquette_ges", ""),
                    "surface": item.get("surface_habitable_immeuble", ""),
                    "type_batiment": item.get("type_batiment", ""),
                    "date_dpe": item.get("date_etablissement_dpe", "")[:10] if item.get("date_etablissement_dpe") else "",
                    "date_fin_validite": item.get("date_fin_validite_dpe", "")[:10] if item.get("date_fin_validite_dpe") else "",
                    "periode_construction": item.get("periode_construction", ""),
                    "total_commune": total,
                })

        except Exception as e:
            print(f"   ❌ Erreur : {e}")
            continue

    # Trier par date DPE (plus récent en premier)
    tous_dpe.sort(key=lambda x: x.get("date_dpe", ""), reverse=True)

    # Détection nouveautés
    hist_path = os.path.join(HISTORIQUE_DIR, "dpe_vus.json")
    historique = {}
    if os.path.exists(hist_path):
        with open(hist_path, encoding="utf-8") as f:
            historique = json.load(f)

    nouveaux = []
    for d in tous_dpe:
        cle = d.get("numero_dpe", "")
        if cle and cle not in historique:
            nouveaux.append(d)
            historique[cle] = {
                "date_detection": datetime.now().strftime("%d/%m/%Y à %H:%M"),
                "commune": d["commune"],
                "adresse": d["adresse"],
                "etiquette": d["etiquette_dpe"],
            }

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "dpe.json"), "w", encoding="utf-8") as f:
        json.dump(tous_dpe, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "dpe_nouveaux.json"), "w", encoding="utf-8") as f:
        json.dump(nouveaux, f, ensure_ascii=False, indent=2)

    # Résumé
    print(f"\n   📊 Résumé par commune :")
    for commune in COMMUNES.keys():
        tc = [d for d in tous_dpe if d["commune"] == commune]
        total = tc[0]["total_commune"] if tc else 0
        f_count = len([d for d in tc if d["etiquette_dpe"] == "F"])
        g_count = len([d for d in tc if d["etiquette_dpe"] == "G"])
        if total > 0:
            print(f"   → {commune} : {total} passoires (F:{f_count} G:{g_count} affichés)")

    print(f"\n   💾 {len(tous_dpe)} DPE récupérés · {len(nouveaux)} nouveaux")

    # Exemples
    if tous_dpe:
        print(f"\n   📋 Exemples de leads :")
        for d in tous_dpe[:5]:
            print(f"   → {d['adresse']} | {d['etiquette_dpe']} | {d['type_batiment']} | {d['surface']} m²")

    return tous_dpe, nouveaux


if __name__ == "__main__":
    print("="*52)
    print("🔋 SENTINELLE IMMO — Collecteur DPE")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    collecter_dpe()
