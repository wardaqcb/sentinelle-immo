import requests
r = requests.get(
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records",
    params={"where": "tribunal like 'Reims' and dateparution >= '2025-01-01' and commercant like 'SCI'", "limit": 1}
)
print("Total SCI Reims 2025:", r.json().get("total_count", 0))
