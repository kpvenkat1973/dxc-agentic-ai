"""Lab 2 auto-checks - one test per challenge. Run: pytest Day03\\Labs\\lab02-naive-rag
Tests 1-8 run offline with a fake Bedrock. Test 9 checks your saved results.
"""
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pytest

LAB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LAB))
sys.path.insert(0, str(LAB.parents[2]))

import lab02a_embeddings as a  # noqa: E402
import lab02b_index as b  # noqa: E402
import lab02c_rag as c  # noqa: E402
from askit_core.rag import SimpleIndex  # noqa: E402


def fake_vector(text, dims=64):
    """Bag-of-words vector: texts sharing words get similar vectors (enough for offline tests)."""
    v = np.zeros(dims)
    for w in text.lower().split():
        v[int(hashlib.md5(w.strip(".,?!").encode()).hexdigest(), 16) % dims] += 1
    n = np.linalg.norm(v)
    return (v / n if n else v).tolist()


class FakeClient:
    def __init__(self, reply="Restart OrbitConnect [KB-004]."):
        self.embed_calls, self.converse_calls, self.reply = [], [], reply

    def invoke_model(self, modelId, body, **kw):
        req = json.loads(body)
        self.embed_calls.append({"modelId": modelId, **req})
        return {"body": io.BytesIO(json.dumps({"embedding": fake_vector(req["inputText"]),
                                               "inputTextTokenCount": 5}).encode())}

    def converse(self, **kw):
        self.converse_calls.append(kw)
        return {"output": {"message": {"role": "assistant", "content": [{"text": self.reply}]}},
                "usage": {"inputTokens": 10, "outputTokens": 5}}


DOCS = {"KB-002": "Accounts lock after 5 failed sign-in attempts and unlock after 30 minutes.",
        "KB-011": "Printers use follow-me printing. Tap your ID card at any printer.",
        "KB-004": "Use OrbitConnect VPN. Error 809 means switch gateway and restart."}


# ---------- Lab A ----------
def test_challenge_1_embed():
    fc = FakeClient()
    v = a.embed(fc, "locked out")
    assert fc.embed_calls, "TODO-1: call client.invoke_model(...)"
    assert fc.embed_calls[0]["modelId"] == a.EMBED_MODEL and fc.embed_calls[0]["inputText"] == "locked out"
    assert isinstance(v, list) and len(v) == 64, "TODO-1: return result['embedding']"


def test_challenge_2_cosine():
    assert a.cosine([1, 0], [1, 0]) == pytest.approx(1.0)
    assert a.cosine([1, 0], [0, 1]) == pytest.approx(0.0)
    assert a.cosine([1, 1], [2, 2]) == pytest.approx(1.0), "TODO-2: divide by both norms"
    assert isinstance(a.cosine([1, 2], [3, 4]), float)


def test_challenge_3_top_k():
    items = [{"id": "x", "vector": [0, 1]}, {"id": "y", "vector": [1, 0]}, {"id": "z", "vector": [1, 1]}]
    r = a.top_k([1, 0.1], items, k=2)
    assert [h["id"] for h in r] == ["y", "z"], "TODO-3: sort highest score first, keep k"
    assert "score" in r[0]


# ---------- Lab B ----------
def test_challenge_4_chunking():
    text = " ".join(f"w{i}" for i in range(100))
    ch = b.chunk_text(text, size=40, overlap=10)
    assert ch[0].split()[0] == "w0" and len(ch[0].split()) == 40
    assert ch[1].split()[0] == "w30", "TODO-4: next chunk starts size-overlap words later"
    assert ch[-1].split()[-1] == "w99", "TODO-4: the last words must not be lost"
    assert len(ch) == 3, "TODO-4: no tiny duplicate chunk at the end"
    assert b.chunk_text("short text here", size=40, overlap=10) == ["short text here"]


def test_challenge_5_build_index():
    idx = b.build_index(FakeClient(), DOCS, size=5, overlap=1)
    assert idx and {"id", "doc_id", "text", "vector"} <= set(idx[0]), "TODO-5: each chunk needs id, doc_id, text, vector"
    assert {c["doc_id"] for c in idx} == set(DOCS)
    assert idx[0]["id"] == "KB-002#0"


def test_challenge_6_search():
    fc = FakeClient()
    idx = b.build_index(fc, DOCS, size=80, overlap=20)
    top = b.search(fc, idx, "failed sign-in attempts lock", k=2)
    assert len(top) == 2 and top[0]["doc_id"] == "KB-002", "TODO-6: best match first"
    assert "vector" not in top[0] and "score" in top[0], "TODO-6: return score, drop the vector"


# ---------- Lab C ----------
HITS = [{"doc_id": "KB-004", "text": "Error 809 means switch gateway."},
        {"doc_id": "KB-012", "text": "Orbit-Guest is for visitors."}]


def test_challenge_7_rag_prompt():
    p = c.build_rag_prompt("What does error 809 mean?", HITS)
    assert isinstance(p, str)
    assert "Error 809 means switch gateway." in p and "KB-004" in p, "TODO-7: include each chunk with its [KB id]"
    assert "What does error 809 mean?" in p, "TODO-7: include the question"
    assert c.IDK in p, "TODO-7: tell the model to reply with IDK when the answer isn't in the context"


def test_challenge_8_answer_with_rag():
    fc = FakeClient()
    idx = SimpleIndex.build(fc, DOCS)
    r = c.answer_with_rag(fc, "model-x", idx, "VPN error 809 gateway", k=2)
    assert r["answer"] == "Restart OrbitConnect [KB-004]." and "KB-004" in r["sources"]
    sent = json.dumps(fc.converse_calls[-1]["messages"])
    assert "OrbitConnect VPN" in sent, "TODO-8: the retrieved context must be in the prompt sent to the model"


def test_challenge_9_results_show_grounding():
    assert c.RESULTS_FILE.exists(), "Run for real: python Day03\\Labs\\lab02-naive-rag\\lab02c_rag.py"
    rows = json.loads(c.RESULTS_FILE.read_text(encoding="utf-8"))
    assert len(rows) >= 5 and all(r["rag"] and r["no_rag"] for r in rows)
    none_rows = [r for r in rows if r["expected_doc"] == "NONE"]
    idk = ("don't know", "do not know", "not in the", "no information")
    assert any(any(p in r["rag"].lower() for p in idk) for r in none_rows), \
        "AskIT should say it doesn't know for questions not in the KB - tighten your TODO-7 rules"
    answerable = [r for r in rows if r["expected_doc"] != "NONE"]
    assert any("KB-" in r["rag"] for r in answerable), "Answers should cite [KB-xxx] sources - tighten TODO-7"
