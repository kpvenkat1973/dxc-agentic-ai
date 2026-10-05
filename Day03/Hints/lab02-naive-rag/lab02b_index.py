"""Lab B - Chunk the knowledge base and build your own vector index.

Run:   python Day03\\Labs\\lab02-naive-rag\\lab02b_index.py
Check: pytest Day03\\Labs\\lab02-naive-rag -k "challenge_4 or challenge_5 or challenge_6"

Complete TODO-4, TODO-5, TODO-6. Everything else is ready.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # lets us import askit_core
from askit_core import bedrock, config, data  # noqa: E402
from askit_core.rag import embed_text  # noqa: E402  (ready-made Titan embedding - same as your Lab A)

HERE = Path(__file__).parent
RESULTS_FILE = HERE / "submission" / "lab02b_results.json"


def chunk_text(text, size=80, overlap=20):
    """Split text into chunks of `size` words; each chunk repeats the last `overlap` words of the previous one."""
    # TODO-4:
    #   words = text.split()
    #   step = size - overlap
    #   make chunks words[i : i + size] for i = 0, step, 2*step, ... while there are still new words
    #   join each chunk back with " " and return the list of strings
    #   Tip: stop when i + overlap >= len(words) (the rest is already in the previous chunk)
    words = text.split()
    step = size - overlap
    chunks = []
    i = 0
    while True:
        chunks.append(" ".join(words[i:i + size]))
        i += step
        if i + overlap >= len(words):
            break
    return chunks


def build_index(client, docs, size=80, overlap=20):
    """docs = {doc_id: text}. Return a list of chunks: {"id", "doc_id", "text", "vector"}."""
    # TODO-5: for each doc, split with chunk_text(); for each piece create
    #   {"id": f"{doc_id}#{i}", "doc_id": doc_id, "text": piece, "vector": embed_text(client, piece)}
    index = []
    for doc_id, text in docs.items():
        for i, piece in enumerate(chunk_text(text, size, overlap)):
            index.append({"id": f"{doc_id}#{i}", "doc_id": doc_id, "text": piece, "vector": embed_text(client, piece)})
    return index


def search(client, index, query, k=3):
    """Return the k best chunks for `query` as dicts WITHOUT the vector, plus a "score"."""
    # TODO-6:
    #   q = np.array(embed_text(client, query))
    #   score each chunk: cosine similarity between q and chunk["vector"]
    #   sort highest first, return top k as {"id", "doc_id", "text", "score"}
    q = np.array(embed_text(client, query))
    scored = []
    for ch in index:
        v = np.array(ch["vector"])
        s = float(q @ v / (np.linalg.norm(q) * np.linalg.norm(v)))
        scored.append({"id": ch["id"], "doc_id": ch["doc_id"], "text": ch["text"], "score": s})
    return sorted(scored, key=lambda h: h["score"], reverse=True)[:k]


def main():
    client = bedrock.client()
    docs = data.load_kb()
    print(f"Chunking + embedding {len(docs)} KB articles ...")
    index = build_index(client, docs)
    print(f"{len(index)} chunks, {len(index[0]['vector'])} dimensions each")

    with open(config.DATA_DIR / "rag_questions.csv", encoding="utf-8") as f:
        questions = [q for q in csv.DictReader(f) if q["expected_doc"] != "NONE"]

    rows, hits = [], 0
    for q in questions:
        top = search(client, index, q["question"], k=3)
        found = q["expected_doc"] in [t["doc_id"] for t in top]
        hits += found
        rows.append({"question": q["question"], "expected": q["expected_doc"], "found": found,
                     "top3": [(t["doc_id"], round(t["score"], 3)) for t in top]})
        print(f"{'HIT ' if found else 'MISS'} {q['question'][:55]:55} -> {[t['doc_id'] for t in top]}")

    hit_rate = round(hits / len(questions), 2)
    print(f"\nHit rate @3: {hit_rate:.0%}")
    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"chunks": len(index), "hit_rate": hit_rate, "rows": rows}, indent=2), encoding="utf-8")
    print(f"Saved {RESULTS_FILE.name} in submission")


if __name__ == "__main__":
    main()
