

from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import torch

# ---- Check for GPU ----
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# ---- Load model ----
model = SentenceTransformer("all-MiniLM-L6-v2", device=device)

# ---- Load Chroma collection ----
persist_directory = "./chroma_db"
client = chromadb.Client(Settings(persist_directory=persist_directory))
collection = client.get_collection(name="numbers_collection")

# ---- Search function ----
def top_k_similar_by_number(number_query, top_k=5):
    result = collection.get(ids=[number_query])
    if not result["ids"]:
        print(f"Number {number_query} not found in ChromaDB")
        return []

    metadata = result["metadatas"][0]
    number_text = metadata["keywords"] + " " + metadata["features"].replace("; ", " ")
    query_emb = model.encode(number_text, device=device).tolist()

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k + 5
    )

    hits = []
    for i in range(len(results["ids"][0])):
        num = results["ids"][0][i]
        if num == number_query:
            continue
        features_list = results["metadatas"][0][i]["features"].split("; ")
        features_dict = {f.split(":")[0]: f.split(":")[1] for f in features_list if ":" in f}
        hit = {
            "number": num,
            "keywords": results["metadatas"][0][i]["keywords"].split(", "),
            "features": features_dict,
            "score": results["distances"][0][i]
        }
        hits.append(hit)
        if len(hits) >= top_k:
            break

    return hits

# ---- Example usage ----
number_to_search = "5703302156660"
top_matches = top_k_similar_by_number(number_to_search, top_k=10)

for idx, match in enumerate(top_matches, 1):
    print(f"{idx}. Number: {match['number']}, Score: {match['score']}")
    print(f"   Keywords: {match['keywords']}")
    print(f"   Features: {match['features']}\n")
