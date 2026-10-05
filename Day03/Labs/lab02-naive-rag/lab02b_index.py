"""Lab 2 Part B - Chunk the knowledge base and build your own vector index.

Run:   python Day03\\Labs\\lab02-naive-rag\\lab02b_index.py
Check: pytest Day03\\Labs\\lab02-naive-rag -k "challenge_4 or challenge_5 or challenge_6"

Complete TODO-4, TODO-5, TODO-6. Everything else is ready.

HOW TO WORK ON EACH TODO
  1. Read the WHY (what idea you are building).
  2. PREDICT the answer in the "My prediction" line, before you run anything.
  3. Fill the blanks (___) and delete the `raise NotImplementedError` line.
  4. Run the script. Was your prediction right? Write one sentence on why.

BIG IDEA: a long article mixes many topics, so its single vector is a blurry
average. We cut articles into small CHUNKS, embed each one, and search the chunks.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # lets us import askit_core
from askit_core import bedrock, config, data  # noqa: E402
from askit_core.rag import embed_text  # noqa: E402  (ready-made Titan embedding - same as your Part A)

HERE = Path(__file__).parent
RESULTS_FILE = HERE / "submission" / "lab02b_results.json"


def chunk_text(text, size=80, overlap=20):
    """Split text into chunks of `size` words; each chunk repeats the last `overlap` words of the previous one."""
    # TODO-4: Cut a long text into overlapping pieces of `size` words.
    # WHY:   Small chunks keep one idea each, so the right piece matches a question.
    #        OVERLAP repeats the last few words in the next chunk so a sentence that
    #        falls on a cut is not lost.
    # STEPS: (1) split the text into a list of words: text.split()
    #        (2) each new chunk starts `step` words after the previous one,
    #            where step = size - overlap
    #        (3) a chunk is words[start : start + size], joined back with " "
    #        (4) stop when the rest of the words are already inside the last chunk
    # SKELETON:  words = ___ ;  step = ___ ;  loop start = 0, step, 2*step ...
    # Example: 100 words, size=40, overlap=10 -> chunk 1 starts at word 0,
    #        chunk 2 starts at word ____ (predict, then check with the test)
    raise NotImplementedError("TODO-4")


def build_index(client, docs, size=80, overlap=20):
    """docs = {doc_id: text}. Return a list of chunks: {"id", "doc_id", "text", "vector"}."""
    # TODO-5: Build the index: every chunk stored together with its vector.
    # WHY:   An index is just a list where each chunk keeps its text (to show the
    #        user) and its vector (to search). Doing this once means we do not pay
    #        for embeddings again on every question.
    # STEPS: for each article, cut it with your chunk_text(); for each piece, add one
    #        dict with keys id, doc_id, text, vector. The id is "<doc_id>#<number>".
    #        The vector comes from embed_text(client, piece).
    # My prediction: with 20 articles, will there be fewer or more than 20 chunks? ____
    raise NotImplementedError("TODO-5")


def search(client, index, query, k=3):
    """Return the k best chunks for `query` as dicts WITHOUT the vector, plus a "score"."""
    # TODO-6: Find the chunks closest in meaning to the question.
    # WHY:   Same idea as Part A TODO-3, now on chunks. The question must be embedded
    #        with the SAME model, otherwise its numbers cannot be compared.
    # STEPS: (1) embed the query into a vector
    #        (2) score every chunk vector against it (cosine, as you wrote in Part A)
    #        (3) sort highest first, keep k, return {"id","doc_id","text","score"}
    #            (leave the long vector out of the result)
    # My prediction: what hit rate @3 will you get? ____ %  (you will see it on run)
    raise NotImplementedError("TODO-6")


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
