# Sentinelle Immo — Récap complet du projet
*Mis à jour le 26/05/2026*

---

## ✅ CE QUI EST FAIT

### Infrastructure
- Site en ligne sur Vercel : https://sentinelle-immo.vercel.app
- GitHub avec déploiement automatique : https://github.com/wardaqcb/sentinelle-immo
- Dossier local : `C:\SentinelleImmo\`
- Stack : HTML/CSS/JS statique + Python pour la collecte
- Cache/ purgé de GitHub (fichiers trop lourds, téléchargés à la demande)

### Collecte de données (collecteur v11)
| Source | Volume | Statut |
|--------|--------|--------|
| DVF 2021-2025 | 17 361 transactions | ✅ |
| BODACC SCI/liquidations | 26 annonces actionnables | ✅ |
| DPE passoires F/G | 8 612 | ✅ |
| SCI MAJIC | 7 947 | ✅ |
| Leads DPE × DVF | 8 608 | ✅ |
| Leads MAJIC × DPE | 3 025 | ✅ |
| Leads Triple (DPE × DVF × MAJIC) | 3 025 (dont 1004 classe G) | ✅ |
| PLU enrichi sur leads | 3 023/3 025 leads géocodés | ✅ |
| Licitor judiciaire | 4 ventes | ✅ |

### Croisements effectués
1. **DPE × DVF** → `dpe_leads_propres.json` (8 608 leads) — passoires non revendues depuis le DPE
2. **MAJIC × DPE** → `leads_majic_dpe.json` (3 025 leads) — SCI propriétaires de passoires
3. **Triple béton DPE × DVF × MAJIC** → `leads_triple.json` (3 025 leads) — SCI + passoire + non vendu + zone PLU
4. **DPE × DVF sans Triple** → ~7 079 leads uniques (passoires sans SCI, affichés en section 2 du dashboard)

### Dashboard (sentinelle-dashboard.html)
- Tableau dense style "salle de contrôle"
- **Section 1 — Leads Triple** : 3 025 leads avec filtres DPE (G/F), commune, type maison/appart, surface ↑↓, date DPE
- **Section 2 — Leads DPE × DVF** : ~7 079 leads avec filtres + période de construction
- **Section BODACC** : 26 annonces avec recherche, filtre famille, filtre type
- **Section Judiciaire** : ventes Licitor
- **Section Successions** : vide (données décès sans adresse = pas actionnable)
- **Section Enchères** : vide (pas encore de collecteur)
- Fiche détail au clic : zone PLU, SCI, lien Pappers, SIREN
- Stats en temps réel dans la topbar

### Pages existantes
- `sentinelle-dashboard.html` — dashboard principal ✅
- `sentinelle-zones.html` — configuration communes ✅
- `sentinelle-marche.html` — référencée mais contenu à faire
- `sentinelle-dossiers.html` — référencée mais contenu à faire

---

## 📋 CE QUI RESTE À FAIRE

### Priorité 1 — Données manquantes
- **Décès INSEE** : collecteur existe, retourne 0. Bug : codes communes non filtrés. À corriger et tester. Sans adresse = pas actionnable directement, mais utile pour croisements futurs
- **Ventes judiciaires Licitor** : collecteur v3 écrit mais URLs `/ventes/10/marne/` retournent 404. À débugger — trouver la bonne URL de listing par département
- **Enchères notariales** : pas encore de collecteur. Source : sites notaires, immonot.com, adsites.fr

### Priorité 2 — Pages manquantes
- **Page Marché local** (`sentinelle-marche.html`) : brancher `dvf.json`, stats par commune (prix/m², évolution 2021-2025, volumes), boutons filtre par année, biens vacants LOVAC en stats agrégées (pas de leads individuels)
- **Page Mes dossiers** (`sentinelle-dossiers.html`) : CRM Kanban pour suivre les leads (colonnes : À contacter / Contacté / En cours / Signé / Perdu)

### Priorité 3 — Automatisation
- **Tâche planifiée Windows** : faire tourner `collecteur.py` chaque nuit automatiquement via le Planificateur de tâches Windows
- **BODACC** : tourne chaque jour ouvré → relancer toutes les nuits

### Priorité 4 — Système d'alertes
- **Email/SMS automatique** : quand un nouveau signal est détecté (comparaison avec historique), envoyer un email aux abonnés avec les nouveaux leads
- C'est ce qui transforme le produit en abonnement actif — sans ça, l'utilisateur doit aller vérifier lui-même

### Priorité 5 — Commercial
- **Premiers clients à Reims** : montrer le dashboard à 2-3 agents immobiliers, marchands de biens ou notaires. Leur demander ce qui leur ferait vraiment gagner du temps. Valider avant de continuer à construire

### Ce qu'on a abandonné (et pourquoi)
- **Pappers API** → payante, abandonnée (SIREN visible directement dans MAJIC)
- **encheres-immo.fr** → site en construction, abandonné
- **Sit@del (permis de construire)** → prévu mais pas encore attaqué. Signal d'anticipation : permis déposé = propriétaire qui va potentiellement libérer un bien

---

## 🔑 DÉCISIONS IMPORTANTES

| Décision | Raison |
|----------|--------|
| DVF → toutes années dans un seul dvf.json, stats sur 2025 | Simplicité, filtres par année dans l'interface |
| LOVAC → page Marché local uniquement, pas de leads individuels | Stats agrégées sans adresses = pas actionnable |
| Décès INSEE → en base silencieusement, pas affichés | Sans adresse du bien = pas actionnable |
| `sentinelle-dashboard.html` = seul dashboard actif | L'ancien était obsolète, remplacé par dashboard-live renommé |
| Ne pas afficher les sources de données sur le site public | Garder le mystère = valeur perçue |
| Fismes retiré des communes surveillées | Hors zone cible |
| Cache/ exclu de GitHub | Fichiers trop lourds (82-228 Mo), re-téléchargeables |
| Leads Triple = meilleure source | SCI + passoire + non vendu = propriétaire le plus motivé |
| Zone PLU dans fiche détail, pas en colonne | Info utile à la demande, pas à surcharger le tableau |
| Architecture SaaS unique | Pas de sites par client, personnalisation via "Mes zones" |

---

## 🏗️ ARCHITECTURE FICHIERS

```
C:\SentinelleImmo\
├── collecteur.py              ← Collecteur principal v11
├── collecteur_bodacc.py       ← BODACC standalone
├── collecteur_dpe.py          ← DPE standalone
├── collecteur_judiciaire.py   ← Licitor v3 (URLs à corriger)
├── collecteur_majic.py        ← MAJIC standalone
├── croisement_dpe_dvf.py      ← Croisement DPE × DVF
├── croisement_majic_dpe.py    ← Croisement MAJIC × DPE
├── croisement_triple.py       ← Croisement Triple
├── enrichir_plu.py            ← Enrichissement PLU via API GPU IGN
├── lovac.py                   ← LOVAC standalone
│
├── donnees/
│   ├── dvf.json               ← 17 361 transactions 2021-2025
│   ├── bodacc.json            ← 26 annonces actionnables SCI
│   ├── deces.json             ← 0 décès (bug à corriger)
│   ├── dpe.json               ← 8 612 passoires F/G
│   ├── majic.json             ← 7 947 SCI propriétaires
│   ├── judiciaire.json        ← 4 ventes Licitor
│   ├── lovac.json             ← Stats biens vacants par commune
│   ├── dpe_leads_propres.json ← 8 608 leads DPE × DVF
│   ├── leads_majic_dpe.json   ← 3 025 leads MAJIC × DPE
│   ├── leads_triple.json      ← 3 025 leads béton + zone_plu
│   ├── stats.json
│   └── rapport.json
│
├── sentinelle-dashboard.html  ← DASHBOARD PRINCIPAL ✅
├── sentinelle-marche.html     ← À créer
├── sentinelle-dossiers.html   ← À créer
└── sentinelle-zones.html      ← ✅
```

---

## 🗺️ COMMUNES SURVEILLÉES

```python
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
```
*Fismes retiré. Codes INSEE vérifiés et corrects.*

---

## ⚠️ BUGS ACTIFS

1. **Décès INSEE retourne 0** — Le collecteur utilise `set(COMMUNES.values())` (corrigé dans le code) mais pas encore testé avec les vrais fichiers `cache/deces/`
2. **Judiciaire Licitor** — Le collecteur v3 a des URLs directes par tribunal qui retournent 404. Fallback : scraper la page d'accueil et filtrer `/annonce/` avec `marne` dans l'URL
3. **Successions vides** — Dépend de la correction des décès INSEE + croisement avec cadastre (complexe)

---

## 💰 MODÈLE ÉCONOMIQUE CIBLE

- Abonnement mensuel par agent/professionnel
- Valeur = gain de temps sur la prospection hors-marché
- Différenciateur = croisement de sources que personne ne fait manuellement
- Prix envisagé : 49-99€/mois (à valider avec les premiers clients)


## 2026-05-28 — Recherche de nouvelles sources de leads + intégration RNC (en cours)

### Contexte
Recensement large des sources publiques pour enrichir les croisements DPE × DVF × MAJIC × BODACC × LOVAC × PLU. Identification des angles morts.

### Sources identifiées par ordre de priorité
1. **Sit@del2** (autorisations d'urbanisme : PC, DP, démolition) — à attaquer demain
2. **BODACC successions** — écarté car le notaire est déjà intermédiaire
3. **RNC (Registre National des Copropriétés)** — exploré aujourd'hui, résultats mitigés (voir ci-dessous)
4. **Ventes aux enchères** (Licitor, encheres-publiques) — à voir plus tard
5. **BDNB** — à évaluer comme socle potentiel
6. **Géorisques API** — utile pour qualifier les leads, pas pour en trouver

### Sources écartées et pourquoi
- **DIA** : non communicable aux tiers (avis CADA), juridiquement bloqué
- **Scraping Leboncoin/SeLoger/PAP** : jurisprudence défavorable (Jinka condamnée à 50k€ en mai 2024)

### Périmètre géographique figé
7 communes surveillées par tous les collecteurs :
- Courcy : 51183
- Gueux : 51282
- Hermonville : 51291
- Muizon : 51391
- Pouillon : 51444
- Reims : 51454
- Tinqueux : 51573

### Avancement RNC
- Source : data.gouv.fr (ANAH), CSV 386 Mo, MAJ quotidienne, Licence Ouverte 2.0
- **Découverte importante** : la version open data du RNC NE CONTIENT PAS les colonnes d'arrêtés (péril, insalubrité, équipements) ni les procédures 29-1A / 29-1, contrairement à ce que laisse entendre la doc PDF ANAH. Ces données sont vraisemblablement réservées aux institutionnels (collectivités, ANAH, syndics).
- **À investiguer demain** : voir s'il est possible d'accéder à la version complète du RNC (avec 29-1 et arrêtés) en tant que pro privé, via une demande ANAH ou un statut spécifique. Si non, le RNC open data perd beaucoup d'intérêt comme source de leads "marchands de biens copros dégradées".

### Volumétrie RNC sur le périmètre
- Total France : 644 328 copros
- Périmètre Sentinelle : **3 125 copros**
  - Reims : 3 058
  - Tinqueux : 59
  - Courcy : 4
  - Gueux : 3
  - Muizon : 1
  - Hermonville : 0
  - Pouillon : 0
- Signaux exploitables :
  - Mandat expiré : 50
  - Pas de mandat en cours : 940 (volume trop large, signal faible)
  - Aidées ANAH : 21 (signal qualitatif fort)
  - En QPV 2024 : 67
  - En ACV / PVD : 0 (Reims pas dans ces programmes)
  - Construites avant 1949 : 1 274

### À faire demain
1. **Investiguer l'accès à la version complète du RNC** (avec procédures 29-1 et arrêtés) — démarche officielle auprès de l'ANAH ?
2. Selon le résultat, soit on continue RNC (avec score de fragilité combiné), soit on bascule complètement sur Sit@del2
3. **Attaquer Sit@del2** dans tous les cas

### Fichiers touchés
- `cache/rnic_full.csv` (téléchargement source ANAH, 386 Mo)
- `test_rnic.py` (script de diagnostic, à transformer en `collecteur_rnc.py` propre si on continue)
- `donnees/rnc_communes_surveillees.json` (3 125 copros filtrées, 8,4 Mo)

## 2026-05-28 (suite) — Conclusion RNC + bascule Sit@del2

### RNC : accès 29-1 = cul-de-sac juridique (CONFIRMÉ)
Vérifié via sources officielles (DREAL, ANIL, préfectures). Les procédures 29-1A / 29-1 et les arrêtés ne sont PAS accessibles à un pro privé :
- Syndics/administrateurs : accès uniquement à LEURS copros (inutile en prospection)
- Notaires : accès élargi dans le cadre d'une vente
- Collectivités/État : accès complet (finalités publiques uniquement)
- Pro privé / SaaS commercial (nous) : annuaire limité + open data expurgé
→ Porte fermée par construction réglementaire, comme la DIA. On n'insiste pas.

### Décision RNC
- **On intègre quand même le RNC open data**, mais en BASSE PRIORITÉ, comme couche d'ENRICHISSEMENT (pas source de leads chauds)
- Usage prévu : quand un lead existant (Triple, DPE×DVF) tombe dans une copro identifiée (aidée ANAH, mandat expiré, QPV), l'afficher dans la fiche détail du lead
- Données dispo : 3 125 copros sur le périmètre, dont 21 aidées ANAH, 50 mandats expirés, 67 en QPV
- À faire plus tard, après Sit@del2

### ⚠️ Correction périmètre à ne pas oublier
Le filtre RNC d'hier n'utilisait que 7 communes — **Saint-Thierry (51518) a été oubliée**. La config officielle DECISIONS.md compte bien 8 communes. À corriger dans tous les futurs collecteurs (RNC inclus). À centraliser dans config_communes.py.

### Priorité du jour : Sit@del2
Bascule actée. Reconnaissance de la source en cours.

## 2026-05-28 — Sessions du jour : RNC, Sit@del2, croisement Sit@del2 × DPE

### 🔑 PRINCIPE DATA GÉNÉRAL (vaut pour tout le projet)
**À la collecte : on garde tout et on annote. À l'affichage : on filtre.**
- On n'efface jamais une donnée brute (dpe.json, majic.json, sitadel.json, etc. restent intacts)
- Les croisements produisent des fichiers dérivés (leads_*.json), jamais une modification destructive des sources
- Un signal "négatif" (ex: passoire en cours de rénovation) se traduit par un DRAPEAU/champ ajouté, pas par une suppression
- Raison : le jour où les critères de "bon lead" changent, la donnée reste réutilisable. On décide à l'affichage, pas à la collecte.

### Recherche large des sources de leads complémentaires
Sources retenues par ordre de priorité :
1. **Sit@del2** (autorisations d'urbanisme) — INTÉGRÉ aujourd'hui ✅
2. ~~BODACC successions~~ — écarté (notaire déjà intermédiaire)
3. **RNC** (Registre National des Copropriétés) — exploré, à intégrer plus tard comme ENRICHISSEMENT léger
4. **Ventes aux enchères** (Licitor, encheres-publiques) — à voir plus tard
5. **BDNB** — à évaluer comme socle potentiel
6. **Géorisques API** — pour qualifier les leads, pas pour en trouver

Sources écartées définitivement :
- **DIA** : non communicable aux tiers (avis CADA), juridiquement bloqué
- **Scraping LBC/SeLoger/PAP** : jurisprudence Jinka mai 2024, 50k€ d'amende

### RNC — exploré, accès 29-1 = cul-de-sac (CONFIRMÉ)
- Source : data.gouv.fr (ANAH), CSV 386 Mo, MAJ quotidienne, Licence Ouverte 2.0
- **L'open data NE CONTIENT PAS** les colonnes d'arrêtés (péril, insalubrité) ni les procédures 29-1A / 29-1
- Vérification sources officielles : ces données sont réservées aux syndics (leurs copros uniquement), notaires (cadre vente), collectivités/État. PAS d'accès pour un SaaS commercial.
- → Porte fermée par construction réglementaire, comme la DIA
- **Décision RNC** : on INTÈGRE plus tard en BASSE PRIORITÉ comme couche d'ENRICHISSEMENT (pas source de leads chauds). Usage prévu : afficher dans la fiche détail d'un lead s'il tombe dans une copro identifiée (aidée ANAH, mandat expiré, QPV)
- Volumétrie périmètre : 3 125 copros, dont 21 aidées ANAH, 50 mandats expirés, 67 en QPV

### ⚠️ Périmètre — Saint-Thierry à NE PAS oublier
Le filtre RNC du 27/05 n'utilisait que 7 communes — Saint-Thierry (51518) avait été oubliée.
Config officielle = **8 communes**. À centraliser dans `config_communes.py` à terme.
Le `collecteur_sitadel.py` utilise bien les 8 (corrigé).

### Sit@del2 — SOURCE VALIDÉE ET INTÉGRÉE ✅
- API DiDo publique sans authentification : `https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1`
- 4 fichiers (rid), millésime 2026-04, MAJ mensuelle :
  - logements : `8b35affb-55fc-4c1f-915b-7750f974446a`
  - locaux    : `f8f0700f-806c-40a7-83b1-f21cf507e7c4`
  - amenager  : `96883f50-538b-41f9-a059-c6eb97e6a23a`
  - demolir   : `1a9a2f0c-56fe-4e69-84a7-fbbda2121f02`
- Filtre serveur multi-communes en 1 requête : `COMM=in:51183,51282,...`
- **Champs en or** : SIREN_DEM (croisable MAJIC/Pappers), parcelles cadastrales (jusqu'à 3), adresse terrain, dates (dépôt/autorisation/ouverture chantier/achèvement), demandeur (nom + localité)
- `collecteur_sitadel.py` opérationnel → `donnees/sitadel.json` (3 485 permis sur 8 communes)
- Répartition : logements 1823, locaux 1128, demolir 425, amenager 109
- 1 565 permis avec SIREN (45% du total) — croisables MAJIC
- 1 336 demandeurs domiciliés hors commune du bien — profil investisseur

### Croisement Sit@del2 × DPE
- ⚠️ `dpe.json` N'A PAS de parcelle cadastrale → croisement sur ADRESSE uniquement (pas sur parcelle)
- Test des 2 méthodes :
  - **Strict** (rue normalisée identique) = FIABLE → **378 matchs**
  - **Souple** (début de nom de rue) = POURRI → 1 978 matchs dont quasi tous faux positifs ("Rue Marcel Thil" ↔ "Rue Marcelle Loiseau", etc.)
- → On garde uniquement le STRICT
- `croisement_sitadel_dpe.py` écrit (en attente de premier lancement) → produit `donnees/leads_sitadel_dpe.json`
- Méthode : on enrichit les passoires matchées d'un bloc `permis_sitadel` (signaux: rénovation/démolition/division/locaux_non_resid, SIREN, demandeur hors commune, détail des permis). On ne supprime rien du DPE source.

### À faire pour la prochaine session
1. **Lancer `croisement_sitadel_dpe.py`** pour produire `leads_sitadel_dpe.json` et valider les volumes finaux par signal
2. **Décider de l'usage** des signaux Sit@del2 dans le dashboard :
   - Drapeau "⚠️ permis en cours" sur les passoires du dashboard principal
   - Ou nouvelle section "Permis détectés" avec sous-onglets (démolir / aménager / rénover) ?
3. **Enrichir le DPE avec la parcelle cadastrale** si possible (re-collecte ADEME avec champ parcellaire) → permettrait à terme un croisement parcelle plutôt qu'adresse, plus fiable
4. **RNC** : revenir dessus en mode enrichissement léger après Sit@del2 stabilisé
5. **Centraliser** la liste des 8 communes dans `config_communes.py` (actuellement dupliquée dans plusieurs collecteurs)

### Fichiers touchés cette session
- `cache/rnic_full.csv` (téléchargement ANAH, 386 Mo, à conserver pour usage enrichissement futur)
- `test_rnic.py` (script de diagnostic, peut être archivé)
- `donnees/rnc_communes_surveillees.json` (3 125 copros filtrées, 8,4 Mo)
- `test_sitadel.py` (script de reconnaissance API DiDo)
- `sitadel_metadata.json` (métadonnées complètes des 4 fichiers, pour référence)
- `collecteur_sitadel.py` ✅ (collecteur production)
- `donnees/sitadel.json` ✅ (3 485 permis, 8,4 Mo)
- `test_croisement_sitadel_dpe.py` (script de validation des 2 méthodes de matching)
- `croisement_sitadel_dpe.py` (écrit, à lancer)

---

## 2026-06-03 — Session du jour : Sit@del×DPE, config communes, Licitor, Marché local, CRM Kanban

### Croisement Sit@del × DPE — LANCÉ ET VALIDÉ ✅

- `croisement_sitadel_dpe.py` lancé → `donnees/leads_sitadel_dpe.json`
- **315 leads** produits (passoires DPE avec permis Sit@del sur même adresse, matching strict)
- Répartition : rénovation 213 · locaux_non_resid 91 · démolition 24 · division 8
- 151 leads avec SIREN demandeur (croisables MAJIC) · 123 demandeurs hors commune

### Intersection Sit@del × Triple

- `check_intersection.py` : 64 adresses uniques en commun → **224 leads Triple enrichis** (plusieurs unités par adresse)
- `enrichir_triple_sitadel.py` → `donnees/leads_triple_enrichi.json` (produit, non utilisé en dashboard pour l'instant)
- **Décision architecture** : 2 sections séparées dans le dashboard, Triple reste Triple
  - Section Triple → `leads_triple.json` (inchangé, riche en data SCI/PLU/etc.)
  - Section Sit@del → `leads_sitadel_dpe_hors_triple.json` (207 leads, aucun overlap avec Triple)

### Filtrage Sit@del hors Triple

- `filtrer_sitadel_hors_triple.py` → `donnees/leads_sitadel_dpe_hors_triple.json`
- **207 leads** : rénovation 144 · locaux_non_resid 46 · **démolition 21** · division 7
- À noter : 21 démolitions hors Triple = propriétaires non-SCI avec permis de démolir → signal foncier fort

### Dashboard — Nouvelle section Sit@del ✅

- `sentinelle-dashboard.html` : section 🏗️ Permis Sit@del ajoutée
- Filtres : DPE (G/F) + signal (Démolition / Division / Rénovation / Locaux)
- Badges colorés par type de signal dans la table
- Fiche détail avec détail de chaque permis (date, demandeur, localité, SIREN, N° DAU)
- Stat card violette "Permis Sit@del" dans la topbar
- Barre de filtres globale redondante supprimée (chaque section a ses propres filtres)

### config_communes.py — CRÉÉ ✅

- Fichier `config_communes.py` = source unique de vérité pour le périmètre 8 communes
- Exports : `COMMUNES` (nom→code), `CODE_TO_NOM`, `CODES_INSEE`, `NOMS`, `NOMS_UPPER`, `CODES_INSEE_SET`, `CODES_INSEE_STR`
- **5 collecteurs mis à jour** : `collecteur.py`, `collecteur_dpe.py`, `collecteur_deces.py`, `collecteur_majic.py`, `collecteur_sitadel.py`, `collecteur_test.py`
- `collecteur_bodacc.py` et `collecteur_judiciaire.py` inchangés (pas de filtre commune)

### Bug décès corrigé ✅

- **Bug** dans `collecteur.py` : `COMMUNES[code_deces]` utilisait un code INSEE comme clé dans le dict nom→code → KeyError silencieuse → 0 décès retournés
- **Fix** : remplacé par `CODE_TO_NOM[code_deces]`
- Résultat après fix : **1 297 décès** récupérés sur 8 communes (2026, 5 fichiers)

### Collecteur Judiciaire v4 ✅

- Anciennes URLs `/ventes/10/marne/reims` → 404 (structure Licitor changée)
- Nouvelle structure : `/ventes-judiciaires-immobilieres/tj-reims/[date].html`
- Nouvelle logique : fetch page France → détection dynamique des liens d'audience actifs
- Si TJ sans audience programmée → skip propre sans erreur
- Test : TJ Châlons-en-Champagne 2 ventes récupérées · TJ Reims 0 audience ce jour

### Page Marché local — Complétée ✅

- **Filtre par année** (boutons Toutes / 2021→2025) sur l'onglet Stats
- Tous les blocs (KPIs, type stats, comparatif, chart prix/commune) se recalculent dynamiquement
- **Graphe évolution** prix/m² par année : ligne Reims vs Zone hors Reims, 2021→2025
- **Filtre année** ajouté dans l'onglet Recherche DVF
- Charts Chart.js détruits/recréés proprement à chaque changement d'année

### CRM Kanban — Mes dossiers ✅

- `sentinelle-dossiers.html` transformé : données hardcodées → **localStorage** (`sentinelle_dossiers`)
- 5 colonnes : À contacter → Contacté → En négociation → Mandat signé → Archivé
- **Drag & drop** entre colonnes avec entrée automatique dans la timeline
- **Création manuelle** via "+ Nouveau dossier" (titre, commune, source, prix estimé)
- **Sauvegarde notes + statut** depuis le panel détail
- **Suppression** avec confirmation
- Stats (total actifs, à contacter, en négociation, mandats) calculées dynamiquement
- `sentinelle-dashboard.html` : bouton "🗂️ Ajouter à mes dossiers" branché sur localStorage
  - Fonctionne pour les 3 types de leads : Triple (`openLeadDetail`), Sit@del, DVF
  - **Anti-doublon** : détection par adresse, message "⚠️ Déjà dans vos dossiers" (orange 2,5s)
  - Feedback visuel vert "✅ Dossier créé !" à la création

### Fichiers touchés cette session

- `donnees/leads_sitadel_dpe.json` ✅ (315 leads)
- `donnees/leads_sitadel_dpe_hors_triple.json` ✅ (207 leads, utilisé en dashboard)
- `donnees/leads_triple_enrichi.json` (224 leads Triple + signaux Sit@del, non utilisé pour l'instant)
- `croisement_sitadel_dpe.py` ✅
- `filtrer_sitadel_hors_triple.py` ✅
- `enrichir_triple_sitadel.py` ✅ (disponible pour usage futur)
- `check_intersection.py` (script diagnostic, peut être archivé)
- `config_communes.py` ✅ (nouveau)
- `collecteur.py` ✅ (fix bug décès + import config_communes)
- `collecteur_dpe.py` ✅ (import config_communes)
- `collecteur_deces.py` ✅ (import config_communes)
- `collecteur_majic.py` ✅ (import config_communes)
- `collecteur_sitadel.py` ✅ (import config_communes)
- `collecteur_test.py` ✅ (import config_communes)
- `collecteur_judiciaire.py` ✅ (v4 — nouvelles URLs Licitor)
- `sentinelle-dashboard.html` ✅ (section Sit@del + CRM + anti-doublon + suppression filtre global)
- `sentinelle-marche.html` ✅ (filtre année + graphe évolution)
- `sentinelle-dossiers.html` ✅ (CRM Kanban complet localStorage)

### À faire — prochaine session

1. **Tâche planifiée Windows** — collecte automatique nocturne (Task Scheduler)
2. **Décès INSEE dans le dashboard** — section à créer (données dispo, non affichées)
3. **Enrichissement Triple avec Sit@del** — `leads_triple_enrichi.json` prêt, badge à afficher dans la section Triple
4. **RNC** — enrichissement léger (couche fiche détail), basse priorité
5. **BDNB** — à évaluer comme socle potentiel
---

## 2026-06-04 — Badge Sit@del dans la section Triple du dashboard

### Contexte
`leads_triple_enrichi.json` (224 leads sur 3 025 avec un bloc `permis_sitadel`) était produit depuis la session du 03/06 mais pas encore exploité visuellement dans le dashboard. Objectif du soir : rendre ce signal visible dans la section Triple sans créer de section séparée.

### Changements (sentinelle-dashboard.html)
- **Fetch** : la section Triple charge désormais `donnees/leads_triple_enrichi.json` au lieu de `leads_triple.json`. Même structure (3 025 leads, dédoublonnage existant conservé), `permis_sitadel` en plus sur 224 leads.
- **Table Triple** : petit 🏗️ discret ajouté après l'adresse pour les leads avec permis. Au survol (`title`), liste des signaux ("Locaux, Rénovation"...).
- **Fiche détail** : nouveau bloc "🏗️ Signaux Sit@del" (nb permis, signaux, SIREN demandeur, demandeur hors commune, + détail de chaque permis), inséré entre le bloc SCI et le bloc Source. Réutilise l'objet `SIGNAL_STYLE` déjà présent dans le fichier.
- **Dédup à l'affichage** : les blocs `permis_sitadel.details` contiennent des permis dupliqués (12 → 2 sur le cas testé "25 Rue Marlot, Reims"). Filtrage par (num_dau + signal + date) à l'affichage de la fiche détail.

### Déploiement
- Commit `81de28b` "Badge Sit@del dans section Triple + bloc detail" → poussé sur `main` → déployé en production Vercel (Ready).
- `leads_triple_enrichi.json` déjà suivi par Git et présent en prod (vérifié via `git ls-files`) → section Triple non vide en ligne.

### À suivre / dette technique
1. **Doublons à corriger À LA SOURCE** : la duplication des permis vient probablement de `enrichir_triple_sitadel.py` ou `croisement_sitadel_dpe.py`. Le patch actuel est cosmétique (dédup à l'affichage seulement).
2. **`openSitadelDetail` a le même bug de doublons non filtrés** (section Sit@del) — à harmoniser avec le fix Triple.
3. **Fichiers non commités sur le PC** (vus dans `git status` / Vercel) à pousser pour ne pas les perdre : `config_communes.py`, `croisement_sitadel_dpe.py`, `enrichir_triple_sitadel.py`, `filtrer_sitadel_hors_triple.py`, `check_intersection.py`, `donnees/leads_sitadel_dpe.json`, `donnees/sitadel.json`, `donnees/rnc_communes_surveillees.json`, scripts de test. À faire un soir de ménage Git.

### À faire — prochaine session (mise à jour)
1. **Tâche planifiée Windows** — collecte automatique nocturne (Task Scheduler) — *priorité haute, débloque les alertes*
2. **Décès INSEE dans le dashboard** — section à créer (1 297 décès dispo après fix, non affichés). À challenger : section dédiée vs simple couche de croisement silencieuse (pas d'adresse = signal faible).
3. ~~Enrichissement Triple avec Sit@del~~ — ✅ FAIT le 04/06.
4. **RNC** — enrichissement léger (couche fiche détail), basse priorité.
5. **BDNB** — à évaluer comme socle potentiel.
6. **Système d'alertes email/SMS** — dépend de l'automatisation (#1). C'est ce qui transforme l'outil en abonnement actif.
7. **Validation commerciale** — montrer le dashboard à 2-3 pros rémois avant d'empiler d'autres features.
8. **Ménage Git** — committer les fichiers non suivis listés ci-dessus.
