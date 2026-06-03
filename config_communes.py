# config_communes.py
# ============================================================
# SENTINELLE IMMO — Source unique de vérité du périmètre
# 8 communes surveillées. Ne pas modifier sans mettre à jour
# DECISIONS.md.
# ============================================================

# Format principal : nom → code INSEE
COMMUNES = {
    "Courcy":        "51183",
    "Gueux":         "51282",
    "Hermonville":   "51291",
    "Muizon":        "51391",
    "Pouillon":      "51444",
    "Reims":         "51454",
    "Saint-Thierry": "51518",
    "Tinqueux":      "51573",
}

# Formes dérivées — prêtes à l'emploi dans les collecteurs

# Sens inverse : code → nom  (ex: "51454" → "Reims")
CODE_TO_NOM = {v: k for k, v in COMMUNES.items()}

# Listes
CODES_INSEE = list(COMMUNES.values())
NOMS        = list(COMMUNES.keys())

# Noms en majuscules pour MAJIC (compare avec les fichiers DGFiP)
NOMS_UPPER = {nom.upper() for nom in NOMS}

# Set de codes pour membership test rapide
CODES_INSEE_SET = set(CODES_INSEE)

# Chaîne séparée par virgules pour les filtres API (ex: DiDo / Sit@del)
CODES_INSEE_STR = ",".join(CODES_INSEE)
