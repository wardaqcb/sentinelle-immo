import json
import os
from datetime import datetime
from difflib import SequenceMatcher

# ============================================
# SENTINELLE IMMO — Croisement DPE × DVF
# Filtre les passoires thermiques dont le bien
# a été vendu APRÈS la date du DPE
# ============================================

OUTPUT_DIR = "donnees"

def normaliser_adresse(adresse):
    """Normalise une adresse pour comparaison."""
    if not adresse:
        return ""
    adresse = adresse.lower().strip()
    # Supprime le code postal et la ville (garde juste numéro + rue)
    import re
    adresse = re.sub(r'\b5\d{4}\b', '', adresse)  # retire codes postaux 51xxx
    adresse = re.sub(r'\breims\b|\btinqueux\b|\bgueux\b|\bmuizon\b|\bhermonville\b|\bcourcy\b|\bsaint.thierry\b|\bpouillon\b', '', adresse)
    # Normalise les abréviations
    adresse = adresse.replace("rue", "rue").replace("r.", "rue")
    adresse = adresse.replace("av.", "avenue").replace("ave.", "avenue")
    adresse = adresse.replace("bd.", "boulevard").replace("bld.", "boulevard")
    adresse = re.sub(r'\s+', ' ', adresse).strip()
    return adresse

def similarite(a, b):
    """Calcule la similarité entre deux adresses (0 à 1)."""
    return SequenceMatcher(None, a, b).ratio()

def extraire_numero_rue(adresse):
    """Extrait le numéro de rue."""
    import re
    match = re.match(r'^(\d+)', adresse.strip())
    return match.group(1) if match else ""

def croiser_dpe_dvf():
    print("\n🔗 Croisement DPE × DVF...")

    # Charge les données
    dpe_path = os.path.join(OUTPUT_DIR, "dpe.json")
    dvf_path = os.path.join(OUTPUT_DIR, "dvf.json")

    if not os.path.exists(dpe_path):
        print("   ❌ dpe.json introuvable")
        return []
    if not os.path.exists(dvf_path):
        print("   ❌ dvf.json introuvable")
        return []

    with open(dpe_path, encoding="utf-8") as f:
        dpe_data = json.load(f)
    with open(dvf_path, encoding="utf-8") as f:
        dvf_data = json.load(f)

    print(f"   📊 DPE chargés : {len(dpe_data)}")
    print(f"   📊 DVF chargés : {len(dvf_data)}")

    # Prépare un index DVF par commune + adresse normalisée
    print("\n   🔍 Indexation DVF...")
    dvf_index = {}
    for t in dvf_data:
        commune = t.get("commune", "")
        adresse_brute = t.get("adresse", "").strip()
        adresse_norm = normaliser_adresse(adresse_brute)
        numero = extraire_numero_rue(adresse_norm)
        date = t.get("date_mutation", "")

        if commune not in dvf_index:
            dvf_index[commune] = []
        dvf_index[commune].append({
            "adresse_norm": adresse_norm,
            "adresse_brute": adresse_brute,
            "numero": numero,
            "date": date,
            "valeur": t.get("valeur_fonciere", 0),
        })

    print(f"   ✅ Index DVF créé pour {len(dvf_index)} communes")

    # Croisement
    leads_propres = []
    leads_vendus = []
    leads_inconnus = []

    print("\n   🔗 Croisement en cours...")

    for dpe in dpe_data:
        adresse_dpe = normaliser_adresse(dpe.get("adresse", ""))
        numero_dpe = extraire_numero_rue(adresse_dpe)
        commune_dpe = dpe.get("commune", "")
        date_dpe = dpe.get("date_dpe", "")

        # Cherche dans DVF de la même commune
        transactions_commune = dvf_index.get(commune_dpe, [])

        vendu_apres = False
        transaction_trouvee = None

        for t in transactions_commune:
            # Compare d'abord les numéros de rue (rapide)
            if numero_dpe and t["numero"] and numero_dpe != t["numero"]:
                continue

            # Compare les adresses normalisées
            sim = similarite(adresse_dpe, t["adresse_norm"])

            if sim >= 0.65:  # Seuil de similarité
                # Adresse similaire trouvée — vérifie si vendu APRÈS le DPE
                if date_dpe and t["date"] and t["date"] > date_dpe:
                    vendu_apres = True
                    transaction_trouvee = t
                    break

        dpe_enrichi = {
            **dpe,
            "statut_croisement": "",
            "transaction_dvf": None,
        }

        if vendu_apres:
            dpe_enrichi["statut_croisement"] = "vendu_apres_dpe"
            dpe_enrichi["transaction_dvf"] = {
                "adresse": transaction_trouvee["adresse_brute"],
                "date": transaction_trouvee["date"],
                "valeur": transaction_trouvee["valeur"],
            }
            leads_vendus.append(dpe_enrichi)
        elif transaction_trouvee:
            dpe_enrichi["statut_croisement"] = "transaction_anterieure"
            leads_inconnus.append(dpe_enrichi)
        else:
            dpe_enrichi["statut_croisement"] = "non_vendu"
            leads_propres.append(dpe_enrichi)

    # Résultats
    print(f"\n   📊 Résultats du croisement :")
    print(f"   ✅ Leads propres (non vendus depuis DPE) : {len(leads_propres)}")
    print(f"   ⚠️  Vendus après le DPE (à écarter)      : {len(leads_vendus)}")
    print(f"   ❓ Transaction antérieure au DPE          : {len(leads_inconnus)}")

    # Sauvegarde
    with open(os.path.join(OUTPUT_DIR, "dpe_leads_propres.json"), "w", encoding="utf-8") as f:
        json.dump(leads_propres, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUTPUT_DIR, "dpe_leads_vendus.json"), "w", encoding="utf-8") as f:
        json.dump(leads_vendus, f, ensure_ascii=False, indent=2)

    print(f"\n   💾 dpe_leads_propres.json → {len(leads_propres)} leads actionnables")
    print(f"   💾 dpe_leads_vendus.json  → {len(leads_vendus)} écartés")

    # Affiche les meilleurs leads
    if leads_propres:
        print(f"\n   🎯 Top leads actionnables :")
        # Priorité aux G récents
        top = sorted(leads_propres, key=lambda x: (
            0 if x.get("etiquette_dpe") == "G" else 1,
            x.get("date_dpe", "")
        ), reverse=False)
        for d in top[:8]:
            print(f"   → {d['adresse']} | {d['etiquette_dpe']} | {d['type_batiment']} | {d['date_dpe']}")

    # Exemple de vendus écartés
    if leads_vendus:
        print(f"\n   ❌ Exemples écartés (vendus depuis) :")
        for d in leads_vendus[:3]:
            t = d.get("transaction_dvf", {})
            print(f"   → {d['adresse']} | DPE: {d['date_dpe']} | Vendu: {t.get('date','?')} ({t.get('valeur',0):,.0f} €)")

    return leads_propres


if __name__ == "__main__":
    print("="*52)
    print("🔗 SENTINELLE IMMO — Croisement DPE × DVF")
    print(f"   Date : {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
    print("="*52)
    croiser_dpe_dvf()
