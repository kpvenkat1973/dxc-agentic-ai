"""Lab C - Naive RAG: AskIT answers from the Orbit knowledge base (and admits when it can't).

Run:   python Day03\\Labs\\lab02-naive-rag\\lab02c_rag.py
Check: pytest Day03\\Labs\\lab02-naive-rag -k "challenge_7 or challenge_8 or challenge_9"

Complete TODO-7 and TODO-8, then run the script (Challenge 9). Everything else is ready.
This lab uses the ready-made index from askit_core, so it works even if Lab B isn't finished.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # lets us import askit_core
from askit_core import bedrock, config, data  # noqa: E402
from askit_core.rag import SimpleIndex  # noqa: E402

HERE = Path(__file__).parent
INDEX_FILE = HERE / "index" / "kb_index.json"   # cached on your VM (not pushed)
RESULTS_FILE = HERE / "submission" / "lab02c_results.json"
IDK = "I don't know based on the Orbit KB."


def build_rag_prompt(question, hits):
    """hits = [{"doc_id", "text", ...}]. Return the full prompt text for the model."""
    # TODO-7: Build a grounded prompt with 3 parts:
    #   1. CONTEXT: every hit as  "[KB-00X] chunk text"  (one per line)
    #   2. RULES:   answer ONLY from the context; cite the [KB-00X] ids you used;
    #               if the answer is not in the context reply exactly: IDK  (the constant above)
    #   3. QUESTION: the question
    #   Return it as one string (an f-string or "\n".join([...]) both work).
    context = "\n".join(f"[{h['doc_id']}] {h['text']}" for h in hits)
    return (
        "You are AskIT, the Orbit Corp IT helpdesk assistant.\n\n"
        f"CONTEXT:\n{context}\n\n"
        "RULES:\n- Answer ONLY using the context above.\n"
        "- Cite the [KB-xxx] ids you used.\n"
        f"- If the answer is not in the context, reply exactly: {IDK}\n\n"
        f"QUESTION: {question}"
    )


def ask_model(client, model_id, prompt):
    """Ready-made: one Converse call, returns the text."""
    r = client.converse(modelId=model_id, messages=[{"role": "user", "content": [{"text": prompt}]}],
                        inferenceConfig={"temperature": 0.0, "maxTokens": 400})
    return r["output"]["message"]["content"][0]["text"]


def answer_with_rag(client, model_id, index, question, k=3):
    """Return {"answer": str, "sources": [doc_ids used as context]}."""
    # TODO-8:
    #   hits = index.search(client, question, k=k)
    #   prompt = build_rag_prompt(question, hits)
    #   return {"answer": ask_model(client, model_id, prompt), "sources": [h["doc_id"] for h in hits]}
    hits = index.search(client, question, k=k)
    prompt = build_rag_prompt(question, hits)
    return {"answer": ask_model(client, model_id, prompt), "sources": [h["doc_id"] for h in hits]}


def get_index(client):
    if INDEX_FILE.exists():
        return SimpleIndex.load(INDEX_FILE)
    print("Building the KB index once (about a minute) ...")
    idx = SimpleIndex.build(client, data.load_kb())
    idx.save(INDEX_FILE)
    return idx


def main():
    config.require_models()
    client = bedrock.client()
    index = get_index(client)
    with open(config.DATA_DIR / "rag_questions.csv", encoding="utf-8") as f:
        qs = list(csv.DictReader(f))
    picked = qs[:4] + [q for q in qs if q["expected_doc"] == "NONE"]  # 4 answerable + 2 not in KB

    rows = []
    for q in picked:
        no_rag = ask_model(client, config.SMALL_MODEL, q["question"])
        rag = answer_with_rag(client, config.SMALL_MODEL, index, q["question"])
        rows.append({"question": q["question"], "expected_doc": q["expected_doc"],
                     "no_rag": no_rag, "rag": rag["answer"], "sources": rag["sources"]})
        print(f"\nQ: {q['question']}\n  WITHOUT RAG: {no_rag[:160]}\n  WITH RAG:    {rag['answer'][:160]}\n  sources: {rag['sources']}")

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"\nSaved {RESULTS_FILE.name} in submission")


if __name__ == "__main__":
    main()
