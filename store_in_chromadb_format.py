
import json
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
from tqdm import tqdm
import numpy as np
import os
import torch

# ---- Check for GPU ----
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# ---- Load JSON ----
with open("filtered_numbers_data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ---- Initialize embedding model with CUDA ----
model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

# ---- Initialize Chroma client with local persistence ----
persist_directory = "./chroma_db"
os.makedirs(persist_directory, exist_ok=True)

client = chromadb.Client(Settings(
    persist_directory=persist_directory
))

collection_name = "numbers_collection"
if collection_name in [col.name for col in client.list_collections()]:
    collection = client.get_collection(name=collection_name)
else:
    collection = client.create_collection(name=collection_name)

# ---- Process data and create embeddings ----
ids = []
embeddings = []
metadatas = []

for item in tqdm(data):
    number = item["number"]
    keywords = item.get("keywords", [])
    classifications = item.get("classifications", [])

    # 1. Embedding for keywords
    keywords_emb = model.encode(" ".join(keywords), device=device) if keywords else np.zeros(model.get_sentence_embedding_dimension())

    # 2. Embeddings for featureId + value
    feature_embs = []
    features_dict = {}
    features_str_list = []
    for cls in classifications:
        fid = cls.get("featureId", "")
        val = cls.get("value", "")
        if fid and val:
            # for embeddings
            emb = model.encode(fid + " " + str(val), device=device)
            feature_embs.append(emb)
            # n = len(feature_embs)
            # for metadata string
            features_str_list.append(f"{fid}:{val}")
            # keep original dict for reference in code (won't go into Chroma)
            features_dict[fid] = val

    feature_emb_avg = np.mean(feature_embs, axis=0) if feature_embs else np.zeros(model.get_sentence_embedding_dimension())

    # 3. Average of keywords + feature embeddings
    final_emb = (keywords_emb + feature_emb_avg) / 2

    # 4. Flatten metadata to primitives only
    metadata = {
        "number": number,
        "keywords": ", ".join(keywords),
        "features": "; ".join(features_str_list)  # store as string
    }

    ids.append(number)
    embeddings.append(final_emb.tolist())
    metadatas.append(metadata)

# ---- Upsert into Chroma ----
collection.upsert(
    ids=ids,
    embeddings=embeddings,
    metadatas=metadatas
)

print(f"✅ Stored {len(ids)} items in ChromaDB at {persist_directory}")

# # ---- Search function ----
# def top_k_similar_by_number(number_query, top_k=5):
#     result = collection.get(ids=[number_query])
#     if not result["ids"]:
#         print(f"Number {number_query} not found in ChromaDB")
#         return []

#     metadata = result["metadatas"][0]
#     # recreate query text from stored string
#     number_text = metadata["keywords"] + " " + metadata["features"].replace("; ", " ")
#     query_emb = model.encode(number_text, device=device).tolist()

#     results = collection.query(
#         query_embeddings=[query_emb],
#         n_results=top_k + 5
#     )

#     hits = []
#     for i in range(len(results["ids"][0])):
#         num = results["ids"][0][i]
#         if num == number_query:
#             continue
#         # parse features string back to dict
#         features_list = results["metadatas"][0][i]["features"].split("; ")
#         features_dict = {f.split(":")[0]: f.split(":")[1] for f in features_list if ":" in f}
#         hit = {
#             "number": num,
#             "keywords": results["metadatas"][0][i]["keywords"].split(", "),
#             "features": features_dict,
#             "score": results["distances"][0][i]
#         }
#         hits.append(hit)
#         if len(hits) >= top_k:
#             break

#     return hits

# # ---- Example usage ----
# number_to_search = "5703302156660"
# top_matches = top_k_similar_by_number(number_to_search, top_k=10)

# for idx, match in enumerate(top_matches, 1):
#     print(f"{idx}. Number: {match['number']}, Score: {match['score']}")
#     print(f"   Keywords: {match['keywords']}")
#     print(f"   Features: {match['features']}\n")

