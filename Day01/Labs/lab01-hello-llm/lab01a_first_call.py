"""Lab B - Your first Bedrock call and a model shoot-out.

Run:   python Day01\\Labs\\lab01-hello-llm\\lab01a_first_call.py
Check: pytest Day01\\Labs\\lab01-hello-llm -k "challenge_1 or challenge_2 or challenge_3"

Complete TODO-1, TODO-2, TODO-3. Everything else is ready.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # lets us import askit_core
from askit_core import bedrock, config, data  # noqa: E402

HERE = Path(__file__).parent
RESULTS_FILE = HERE / "submission" / "lab01a_results.json"

SYSTEM = "You are AskIT, the IT helpdesk assistant at Orbit Corp. Reply in at most 3 short sentences."


def build_prompt(ticket):
    return f"A user raised this helpdesk ticket:\n\nSubject: {ticket['subject']}\n{ticket['description']}\n\nWhat should they do first?"


def ask(client, model_id, prompt, system=SYSTEM, temperature=0.2, max_tokens=300):
    """Send one prompt to Bedrock.
    Returns {"text": str, "input_tokens": int, "output_tokens": int, "latency_ms": int}
    """
    start = time.perf_counter()

    # TODO-1: Call the Bedrock Converse API and get the reply text.
    #   response = client.converse(
    #       modelId=...,
    #       system=[{"text": ...}],
    #       messages=[{"role": "user", "content": [{"text": ...}]}],
    #       inferenceConfig={"temperature": ..., "maxTokens": ...},
    #   )
    #   The reply text is in: response["output"]["message"]["content"][0]["text"]
    response = client.converse(modelId=model_id, system=[{"text": system}], messages=[{"role": "user", "content": [{"text": prompt}]}], inferenceConfig={"temperature": temperature, "maxTokens": max_tokens})
    text = response["output"]["message"]["content"][0]["text"]

    latency_ms = round((time.perf_counter() - start) * 1000)

    # TODO-2: Read the token counts from response["usage"]  (keys: "inputTokens", "outputTokens")
    input_tokens = response["usage"]["inputTokens"]
    output_tokens = response["usage"]["outputTokens"]

    return {"text": text, "input_tokens": input_tokens, "output_tokens": output_tokens, "latency_ms": latency_ms}


def compare_models(client, model_ids, tickets):
    """Ask every model about every ticket. Returns a list of rows."""
    rows = []
    # TODO-3: For each model_id in model_ids, and each ticket in tickets:
    #   - result = ask(client, model_id, build_prompt(ticket))
    #   - rows.append({"model_id": model_id, "ticket_id": ticket["ticket_id"], **result})




    return rows


def summarise(rows):
    """Average latency and tokens per model (ready-made)."""
    out = {}
    for m in sorted({r["model_id"] for r in rows}):
        mr = [r for r in rows if r["model_id"] == m]
        out[m] = {
            "calls": len(mr),
            "avg_latency_ms": round(sum(r["latency_ms"] for r in mr) / len(mr)),
            "avg_input_tokens": round(sum(r["input_tokens"] or 0 for r in mr) / len(mr)),
            "avg_output_tokens": round(sum(r["output_tokens"] or 0 for r in mr) / len(mr)),
        }
    return out


def main():
    config.require_models()
    client = bedrock.client()

    print("\n--- One call ---")
    first = data.load_tickets()[0]
    print(json.dumps(ask(client, config.SMALL_MODEL, build_prompt(first)), indent=2))

    print("\n--- Shoot-out: 5 tickets x 2 models ---")
    tickets = data.load_tickets()[:5]
    rows = compare_models(client, [config.SMALL_MODEL, config.LARGE_MODEL], tickets)
    summary = summarise(rows)
    for m, s in summary.items():
        print(f"{m}\n   avg latency {s['avg_latency_ms']} ms | avg tokens in {s['avg_input_tokens']} / out {s['avg_output_tokens']}")

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    print(f"\nSaved {RESULTS_FILE.relative_to(HERE.parents[2])}")


if __name__ == "__main__":
    main()
