"""10-second Azure Foundry check. Run from this folder:  python test_azure.py
Reads the same course .env as the app. Prints OK / the exact error for the chat model and the embedding deployment."""
import os, sys
from pathlib import Path
from dotenv import dotenv_values
for d in reversed([p / ".env" for p in Path(__file__).resolve().parents if (p / ".env").is_file()]):
    for k, v in dotenv_values(d).items():
        if v:
            os.environ[k] = v
from openai import OpenAI
from urllib.parse import urlparse
ep = os.environ["AZURE_OPENAI_ENDPOINT"]; u = urlparse(ep.strip())
base = f"{u.scheme}://{u.netloc}/openai/v1/"
c = OpenAI(base_url=base, api_key=os.environ["AZURE_OPENAI_API_KEY"])
print("base url:", base)
for m in [x.strip() for x in os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENTS", "").split(",") if x.strip()]:
    try:
        r = c.chat.completions.create(model=m, messages=[{"role": "user", "content": "Say OK"}])
        print(f"chat  {m}: OK -> {r.choices[0].message.content!r}")
    except Exception as e:
        print(f"chat  {m}: FAIL {str(e)[:200]}")
emb = os.getenv("AZURE_OPENAI_EMBED_DEPLOYMENT")
if emb:
    import azure_foundry
    for name, url, body, parse in azure_foundry._routes(azure_foundry.host(ep), emb, ["hello"], False):
        try:
            v = parse(azure_foundry._post(url, os.environ["AZURE_OPENAI_API_KEY"], body))
            print(f"embed {emb} [{name}]: OK dims={len(v[0])}")
        except Exception as e:
            print(f"embed {emb} [{name}]: FAIL {str(e)[:200]}")
else:
    print("embed: no Azure deployment set -> app will embed locally (fastembed)")
