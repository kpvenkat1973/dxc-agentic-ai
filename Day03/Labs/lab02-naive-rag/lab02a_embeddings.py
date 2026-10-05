"""Lab 2 Part A - Embeddings with Amazon Titan: turn text into meaning.

Run:   python Day03\\Labs\\lab02-naive-rag\\lab02a_embeddings.py
Check: pytest Day03\\Labs\\lab02-naive-rag -k "challenge_1 or challenge_2 or challenge_3"

Complete TODO-1, TODO-2, TODO-3. Everything else is ready.

HOW TO WORK ON EACH TODO
  1. Read the WHY (what idea you are building).
  2. PREDICT the answer in the "My prediction" line, before you run anything.
  3. Fill the blanks (___) and delete the `raise NotImplementedError` line.
  4. Run the script. Was your prediction right? Write one sentence on why.

BIG IDEA: a computer cannot compare "meaning" in words. An embedding turns a
sentence into a list of numbers (a vector). Sentences with similar meaning get
similar numbers, so "find similar meaning" becomes "find nearby numbers".
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
    # TODO-1: Ask Titan to turn `text` into a vector of numbers.
    # WHY:   Titan is a model on AWS. We send it text, it sends back 512 numbers
    #        that capture the meaning. We never read the numbers; we only compare them.
    # STEPS: (1) build the request as JSON with the text, the size and normalize=True
    #            (normalize=True keeps every vector the same length, so scores are fair)
    #        (2) call client.invoke_model with the model id and that body
    #        (3) the reply body is a stream: read it, parse the JSON, take "embedding"
    # SKELETON (fill the ___):
    #   body = json.dumps({"inputText": ___, "dimensions": ___, "normalize": True})
    #   response = client.invoke_model(modelId=___, body=body)
    #   result = json.loads(response["body"].___())
    #   return result["___"]
    # My prediction: how many numbers will come back for one sentence? ____
    raise NotImplementedError("TODO-1")


def cosine(a, b):
    """Cosine similarity between two vectors: 1 = same meaning, ~0 = unrelated."""
    # TODO-2: Measure how close two meanings are with one number.
    # WHY:   Each vector is an arrow. Two arrows pointing the same way = same meaning
    #        (score 1). At right angles = unrelated (score 0). Cosine similarity
    #        is the angle between the arrows, ignoring how long they are.
    # STEPS: multiply the two vectors element by element and add up (np.dot), then
    #        divide by the length of each vector (np.linalg.norm). Return a float().
    # SKELETON:  float( np.dot(a, b) / ( np.linalg.norm(___) * np.linalg.norm(___) ) )
    # My prediction: score for ("locked out of account", "can't sign in") will be
    #        close to ____ and for ("locked out", "printer jammed") close to ____
    raise NotImplementedError("TODO-2")


def top_k(query_vec, items, k=3):
    """items = [{"id": ..., "vector": [...]}, ...]
    Return the k most similar items as [{"id": ..., "score": ...}], highest score first."""
    # TODO-3: Rank the KB articles by how close they are to the ticket.
    # WHY:   This is retrieval, the "R" in RAG: given a question, find the pieces
    #        of knowledge nearest in meaning. Everything else in RAG builds on it.
    # STEPS: (1) give every item a score with your cosine() function
    #        (2) sort the scores, highest first
    #        (3) keep only the first k and return them as {"id": ..., "score": ...}
    # Hint:  sorted(list, key=lambda x: x["score"], reverse=___) and list[:k]
    # My prediction: will the top match for "VPN keeps dropping" be a VPN article? ____
    raise NotImplementedError("TODO-3")


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
