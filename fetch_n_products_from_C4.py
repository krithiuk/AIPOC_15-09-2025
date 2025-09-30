from azure.cosmos import CosmosClient
import json
import re

# ---- Cosmos DB connection details ----
url = "https://eg-dk-c4-db-d1.documents.azure.com:443"
key = "dOwfPDX1lUsnHfX8GjKyHOy3LoTSCE9anY75EmzcrKYHBLuIWX0Rd3bxwJtolHV2BxdPm2s2uBzXACDbDpKVsw=="
database_name = "ComponentCatalog-ring0"
container_name = "Components"

# ---- Regex filters ----
only_number = r"^\d+$"
number_decimal = r"^\d+[.,]\d+$"
only_specials = r"^[^\w\d]+$"

def filter_keywords(keywords):
    if not keywords:
        return []
    filtered = [
        kw for kw in keywords
        if not (re.fullmatch(only_number, kw)
                or re.fullmatch(number_decimal, kw)
                or re.fullmatch(only_specials, kw))
    ]
    # Deduplicate while keeping order
    seen = set()
    deduped = []
    for kw in filtered:
        if kw not in seen:
            seen.add(kw)
            deduped.append(kw)
    return deduped

# ---- Initialize client ----
client = CosmosClient(url, credential=key)
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)

# ---- SQL query ----
query = """
SELECT TOP 500 c.number, c.keywords, c.classifications
FROM c
ORDER BY c.randKey
"""

# ---- Execute and fetch all results ----
results = []
for item in container.query_items(
    query=query,
    enable_cross_partition_query=True
):
    number = item.get("number")
    keywords = filter_keywords(item.get("keywords", []))
    classifications = item.get("classifications", [])

    results.append({
        "number": number,
        "keywords": keywords,
        "classifications": classifications
    })

print(f"Total items fetched: {len(results)}")

# ---- Save to JSON file ----
with open("random500_1.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print("✅ Saved random20.json with cleaned keywords")
