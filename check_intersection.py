import json, unicodedata, re

def normaliser(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.upper().strip())

triple = json.load(open('donnees/leads_triple.json', encoding='utf-8'))
sitadel = json.load(open('donnees/leads_sitadel_dpe.json', encoding='utf-8'))['leads']

triple_ids = set(normaliser(l['adresse']) for l in triple)
sitadel_ids = set(normaliser(l.get('adresse', '')) for l in sitadel)
intersection = triple_ids & sitadel_ids

print(f"Triple        : {len(triple_ids)}")
print(f"Sitadel x DPE : {len(sitadel_ids)}")
print(f"Intersection  : {len(intersection)} leads dans les DEUX")