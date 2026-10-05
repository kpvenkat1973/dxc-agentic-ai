"""Run this before the lab: python check_setup.py
Checks AWS Bedrock (main) first, then the OpenAI backup if a key is set. Verifies chat, JSON replies and embeddings."""
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")   # course .env (AWS keys, BEDROCK_SMALL_MODEL_ID)
load_dotenv()

from rag import config  # noqa: E402
from rag.llm import LLM, bedrock_ready  # noqa: E402


def check(llm):
    t = time.time()
    v = llm.embed(["hello"], op="check")[0]
    print(f"OK embeddings  {llm.embed_model}: dim={len(v)} ({time.time() - t:.1f}s)")
    t = time.time()
    msg, row = llm.chat([{"role": "user", "content": 'Reply with JSON {"ok": true}'}], op="check", json_mode=True)
    print(f"OK chat        {llm.chat_model}: {msg.content!r} tokens={row['input_tokens']}+{row['output_tokens']} ({time.time() - t:.1f}s)")


ok = False
if bedrock_ready():
    try:
        check(LLM(provider="bedrock", cache_dir=".cache_check"))
        ok = True
    except Exception as e:
        print(f"Bedrock FAILED: {str(e)[:300]}")
else:
    print("Bedrock not configured: need AWS keys and BEDROCK_SMALL_MODEL_ID in the course .env")
if os.getenv("OPENAI_API_KEY"):
    try:
        check(LLM(os.getenv("OPENAI_API_KEY"), cache_dir=".cache_check"))
        ok = True
    except Exception as e:
        print(f"OpenAI FAILED: {str(e)[:300]}")
if not ok:
    sys.exit("No working provider. Ask the trainer. (The app still runs in offline mode.)")
print("All good. Start the app with: streamlit run app.py")
