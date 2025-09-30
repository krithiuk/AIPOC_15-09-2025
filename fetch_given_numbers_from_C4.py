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

# ---- Read numbers from .txt ----
txt_file = "unique_numbers.txt"
with open(txt_file, "r", encoding="utf-8") as f:
    numbers_to_fetch = [line.strip() for line in f if line.strip()]

print(f"Total numbers to fetch: {len(numbers_to_fetch)}")

# ---- Initialize Cosmos client ----
client = CosmosClient(url, credential=key)
database = client.get_database_client(database_name)
container = database.get_container_client(container_name)

# ---- Fetch data for each number ----
results = []
for number in numbers_to_fetch:
    query = f"""
    SELECT c.number, c.keywords, c.classifications
    FROM c
    WHERE c.number = '{number}'
    """
    for item in container.query_items(
        query=query,
        enable_cross_partition_query=True
    ):
        keywords = filter_keywords(item.get("keywords", []))
        classifications = item.get("classifications", [])
        results.append({
            "number": item.get("number"),
            "keywords": keywords,
            "classifications": classifications
        })

print(f"Total items fetched: {len(results)}")

# ---- Save to JSON file ----
output_file = "filtered_numbers_data.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=4, ensure_ascii=False)

print(f"✅ Saved {output_file} with cleaned keywords")
