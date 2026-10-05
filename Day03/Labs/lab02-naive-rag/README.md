# Lab 2, Parts A and B: embeddings and your own vector index

**AskIT today:** finds the right Orbit KB article for a question, by meaning. You build the engine yourself, then Part C (next folder) wraps it in an app.

| Part | Where | Time | You do |
|---|---|---|---|
| **A** | `lab02a_embeddings.py` | 35 min | Embeddings, cosine similarity, top-k (Challenges 1-3) |
| **B** | `lab02b_index.py` | 40 min | Chunking, your own index, hit rate @3 (Challenges 4-6) |
| **C** | `..\lab02-askit-rag-app` | 40 min | The full RAG app: chunk-size and top-k experiments |
| ⭐ | each part | | Stretch for fast movers (below) |

Parts are independent: stuck in A? Do B anyway.

## How to work
1. Open the file in VS Code, find `TODO-n`. Each TODO explains **why** it exists, lists the **steps** and gives a **skeleton with blanks (`___`)**. Write your **prediction** first, fill the blanks, then run.
2. Run it: `python Day03\Labs\lab02-naive-rag\lab02a_embeddings.py`
3. Check yourself: `pytest Day03\Labs\lab02-naive-rag -k "challenge_1 or challenge_2 or challenge_3"` (Part A), `-k "challenge_4 or challenge_5 or challenge_6"` (Part B).
4. Stuck on a TODO for more than 5 minutes? `Day03\Hints\lab02-naive-rag\`. Copy ONE TODO only, then explain it to your neighbour in one sentence.

Models: **AWS Bedrock Titan Text Embeddings v2** and a small Nova model. It uses the same `.env` as Lab 1. Nothing to set up.

## Part A: embeddings (`lab02a_embeddings.py`)
| # | Do | Test |
|---|---|---|
| Challenge 1 | TODO-1: call Titan Text Embeddings v2 with `client.invoke_model(...)` | `test_challenge_1` |
| Challenge 2 | TODO-2: cosine similarity | `test_challenge_2` |
| Challenge 3 | TODO-3: top-k most similar, then **run the script** | `test_challenge_3` |
| ⭐ Stretch | Re-run with `dimensions=256` and `1024`. Do the top-3 KB matches change? Add 3 tickets of your own that should match a KB article and check. | |

## Part B: your own index (`lab02b_index.py`)
| # | Do | Test |
|---|---|---|
| Challenge 4 | TODO-4: overlapping word chunks | `test_challenge_4` |
| Challenge 5 | TODO-5: build the index (id, doc_id, text, vector) | `test_challenge_5` |
| Challenge 6 | TODO-6: search, then **run the script** → hit rate @3 | `test_challenge_6` |
| ⭐ Stretch | Try `size=40`, `80`, `200`. Record the hit rate for each in `submission\stretch_chunking.md`. Which size wins, and why? | |

## ⭐ Stretch for the whole lab: RAG in code (`lab02c_rag.py`)
Finished early? Write the last step yourself: a grounded prompt and the retrieve → prompt → answer loop (Challenges 7-9, `pytest` → 9 passed). Then try `k=1` and `k=6`: which answers break?

## Stuck?
| Symptom | Fix |
|---|---|
| `AccessDeniedException` on Titan | Titan Embeddings v2 is not enabled for your user: tell the trainer |
| `ThrottlingException` | The whole class is embedding at once. Wait 30 seconds and re-run (retries are automatic) |
| First run of Part B is slow | It embeds every chunk once (about a minute) (it is rebuilt on each run) |
