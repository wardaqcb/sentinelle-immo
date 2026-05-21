import requests

r = requests.get(
    "https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales/records",
    params={"where": 'tribunal like "Reims"', "limit": 1},
    timeout=15
)
data = r.json()
print(f"Total annonces BODACC Reims : {data.get('total_count', 0)}")
