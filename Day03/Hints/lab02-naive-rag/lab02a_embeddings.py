"""Lab A - Embeddings with Amazon Titan: turn text into meaning.

Run:   python Day03\\Labs\\lab02-naive-rag\\lab02a_embeddings.py
Check: pytest Day03\\Labs\\lab02-naive-rag -k "challenge_1 or challenge_2 or challenge_3"

Complete TODO-1, TODO-2, TODO-3. Everything else is ready.
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # lets us import askit_core
from askit_core import bedrock, data  # noqa: E402

HERE = Path(__file__).parent
RESULTS_FILE = HERE / "submission" / "lab02a_results.json"
EMBED_MODEL = "amazon.titan-embed-text-v2:0"


def embed(client, text, dimensions=512):
    """Return the embedding of `text` as a list of floats."""
    # TODO-1: Call Titan Text Embeddings v2 through Bedrock.
    #   body = json.dumps({"inputText": text, "dimensions": dimensions, "normalize": True})
    #   response = client.invoke_model(modelId=EMBED_MODEL, body=body)
    #   result = json.loads(response["body"].read())
    #   return result["embedding"]
    body = json.dumps({"inputText": text, "dimensions": dimensions, "normalize": True})
    response = client.invoke_model(modelId=EMBED_MODEL, body=body)
    return json.loads(response["body"].read())["embedding"]


def cosine(a, b):
    """Cosine similarity between two vectors: 1 = same meaning, ~0 = unrelated."""
    # TODO-2: dot(a, b) / (norm(a) * norm(b))   -> use np.dot and np.linalg.norm
    #   Return a plain Python float.
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def top_k(query_vec, items, k=3):
    """items = [{"id": ..., "vector": [...]}, ...]
    Return the k most similar items as [{"id": ..., "score": ...}], highest score first."""
    # TODO-3: score every item with cosine(query_vec, item["vector"]),
    #   sort by score (highest first) and return the first k as {"id", "score"} dicts.
    scored = [{"id": it["id"], "score": cosine(query_vec, it["vector"])} for it in items]
    return sorted(scored, key=lambda h: h["score"], reverse=True)[:k]


PAIRS = [
    ("I'm locked out of my account", "I can't sign in to my laptop"),
    ("I'm locked out of my account", "The printer on floor 3 is jammed"),
    ("VPN keeps dropping", "Remote connection disconnects every few minutes"),
    ("My phone was stolen", "Lost device with company data"),
]


def main():
    client = bedrock.client()

    print("\n--- Does similarity match meaning? ---")
    pairs = []
    for a_text, b_text in PAIRS:
        s = cosine(embed(client, a_text), embed(client, b_text))
        pairs.append({"a": a_text, "b": b_text, "score": round(s, 3)})
        print(f"{s:5.2f}  '{a_text}'  vs  '{b_text}'")

    print("\n--- Which KB article matches each ticket? ---")
    kb = [{"id": doc_id, "vector": embed(client, text)} for doc_id, text in data.load_kb().items()]
    rows = []
    for tk in data.load_tickets()[:5]:
        hits = top_k(embed(client, tk["description"]), kb, k=3)
        rows.append({"ticket_id": tk["ticket_id"], "subject": tk["subject"], "top3": hits})
        print(f"{tk['ticket_id']} {tk['subject'][:32]:32} -> " + ", ".join(f"{h['id']} ({h['score']:.2f})" for h in hits))

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"pairs": pairs, "tickets": rows}, indent=2), encoding="utf-8")
    print(f"\nSaved {RESULTS_FILE.name} in submission")


if __name__ == "__main__":
    main()
