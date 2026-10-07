"""Azure AI Foundry embeddings: tries every route a Foundry embedding deployment can answer on, remembers the one that works.
Used by app.py and test_azure.py (one key + one resource endpoint for all deployments)."""
from urllib.parse import urlparse

import requests

_working = {}      # model -> route name that worked


def host(endpoint):
    """Resource root only: the Foundry *project* endpoint (…/api/projects/xyz) or any longer URL also works."""
    u = urlparse(endpoint.strip())
    return f"{u.scheme or 'https'}://{u.netloc or u.path.split('/')[0]}"


def _post(url, key, body):
    r = requests.post(url, headers={"api-key": key, "Authorization": f"Bearer {key}"}, json=body, timeout=120)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:160]}")
    return r.json()


def _routes(h, model, batch, query):
    kind = "search_query" if query else "search_document"
    res = h.replace(".openai.azure.com", ".services.ai.azure.com")
    yield "openai-v1", f"{h}/openai/v1/embeddings", {"model": model, "input": batch}, lambda j: [d["embedding"] for d in j["data"]]
    yield "model-inference", f"{res}/models/embeddings?api-version=2024-05-01-preview", {"model": model, "input": batch}, \
        lambda j: [d["embedding"] for d in sorted(j["data"], key=lambda d: d.get("index", 0))]
    yield "cohere-v2", f"{res}/providers/cohere/v2/embed", \
        {"model": model, "texts": batch, "input_type": kind, "embedding_types": ["float"]}, lambda j: j["embeddings"]["float"]
    yield "openai-deployment", f"{h}/openai/deployments/{model}/embeddings?api-version=2024-10-21", {"input": batch}, \
        lambda j: [d["embedding"] for d in j["data"]]


def embed_batch(batch, model, key, endpoint, query=False):
    h, errors = host(endpoint), []
    routes = list(_routes(h, model, batch, query))
    if model in _working:                                   # known good route first
        routes.sort(key=lambda r: r[0] != _working[model])
    for name, url, body, parse in routes:
        try:
            out = parse(_post(url, key, body))
            _working[model] = name
            return out
        except Exception as e:
            errors.append(f"[{name}] {e}")
    raise RuntimeError("Azure embedding failed on all routes: " + " | ".join(errors))
