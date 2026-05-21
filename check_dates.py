import json

data = json.load(open('donnees/dpe.json'))
dates = sorted([d['date_dpe'] for d in data if d['date_dpe']])
print('Nombre de DPE :', len(dates))
print('Plus ancien    :', dates[0])
print('Plus récent    :', dates[-1])

from collections import Counter
annees = Counter([d[:4] for d in dates])
print('\nRépartition par année :')
for annee, nb in sorted(annees.items()):
    print(f'  {annee} : {nb} DPE')
