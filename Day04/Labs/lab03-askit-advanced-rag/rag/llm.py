"""Thin wrapper over the model provider that records tokens, cost and latency for every call.
Providers: "bedrock" (AWS Bedrock: Nova chat + Titan embeddings, the course default), "openai" (backup) and
"offline" (no keys: deterministic stand-ins so the app still runs)."""
import hashlib, json, os, re, time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from datetime import datetime
import numpy as np

from .config import PRICES, DEFAULT_CHAT_MODEL, DEFAULT_EMBED_MODEL, DEFAULT_BEDROCK_MODEL, DEFAULT_BEDROCK_EMBED


class UsageLog:
    def __init__(self):
        self.rows = []

    def add(self, op, model, tin, tout, latency_ms, prices=None, note=""):
        p = (prices or PRICES).get(model) or (prices or PRICES).get(re.sub(r"^(us|eu|apac)\.", "", model), (0.0, 0.0))
        cost = tin / 1e6 * p[0] + tout / 1e6 * p[1]
        row = dict(time=datetime.now().strftime("%H:%M:%S"), operation=op, model=model,
                   input_tokens=int(tin), output_tokens=int(tout), cost_usd=round(cost, 6),
                   latency_ms=int(latency_ms), note=note)
        self.rows.append(row)
        return row


def bedrock_ready():
    """True when AWS credentials and a Bedrock chat model id are available (from .env or the environment)."""
    try:
        import boto3
        return bool(os.getenv("BEDROCK_SMALL_MODEL_ID")) and boto3.Session().get_credentials() is not None
    except Exception:
        return False


def _bedrock_client(region):
    import boto3
    from botocore.config import Config
    return boto3.client("bedrock-runtime", region_name=region,
                        config=Config(retries={"max_attempts": 8, "mode": "adaptive"}, read_timeout=120, connect_timeout=10))


def _extract_json(text):
    """Models sometimes wrap JSON in ``` fences or add a sentence. Return just the JSON object."""
    t = (text or "").strip()
    m = re.search(r"\{.*\}", t, re.S)
    return m.group(0) if m else t


class LLM:
    """provider: "bedrock" | "openai" | None. None = "openai" if an api_key is given, else offline."""

    def __init__(self, api_key=None, chat_model=None, embed_model=None, prices=None, log=None, cache_dir=".cache",
                 provider=None):
        self.provider = provider or ("openai" if api_key else "offline")
        self.offline = self.provider == "offline"
        if self.provider == "bedrock":
            chat_model = chat_model or os.getenv("BEDROCK_SMALL_MODEL_ID", DEFAULT_BEDROCK_MODEL)
            embed_model = embed_model or DEFAULT_BEDROCK_EMBED
        else:
            chat_model = chat_model or DEFAULT_CHAT_MODEL
            embed_model = embed_model or DEFAULT_EMBED_MODEL
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.prices = prices or PRICES
        self.log = log or UsageLog()
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.client = None
        if self.provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key)
        elif self.provider == "bedrock":
            self.client = _bedrock_client(os.getenv("AWS_REGION", "us-east-1"))

    # ---------- embeddings (cached on disk: re-runs cost nothing) ----------
    def _cache_path(self):
        return os.path.join(self.cache_dir, f"emb_{self.embed_model if not self.offline else 'offline'}.json")

    def embed(self, texts, op="embed"):
        path = self._cache_path()
        cache = json.load(open(path)) if os.path.exists(path) else {}
        keys = [hashlib.sha1(t.encode()).hexdigest() for t in texts]
        missing = [(k, t) for k, t in zip(keys, texts) if k not in cache]
        if missing:
            t0 = time.perf_counter()
            if self.offline:
                for k, t in missing:
                    cache[k] = _hash_embed(t)
                self.log.add(op, "offline-hash", sum(len(t) // 4 for _, t in missing), 0,
                             (time.perf_counter() - t0) * 1000, self.prices, f"{len(missing)} texts")
            elif self.provider == "bedrock":
                def one(t):
                    body = json.dumps({"inputText": t[:20000], "dimensions": 512, "normalize": True})
                    r = self.client.invoke_model(modelId=self.embed_model, body=body)
                    out = json.loads(r["body"].read())
                    return out["embedding"], out.get("inputTextTokenCount", len(t) // 4)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(one, [t for _, t in missing]))
                for (k, _), (vec, _n) in zip(missing, results):
                    cache[k] = vec
                self.log.add(op, self.embed_model, sum(n for _, n in results), 0,
                             (time.perf_counter() - t0) * 1000, self.prices, f"{len(missing)} texts")
            else:
                resp = self.client.embeddings.create(model=self.embed_model, input=[t for _, t in missing])
                for (k, _), d in zip(missing, resp.data):
                    cache[k] = d.embedding
                self.log.add(op, self.embed_model, resp.usage.prompt_tokens, 0,
                             (time.perf_counter() - t0) * 1000, self.prices, f"{len(missing)} texts")
            json.dump(cache, open(path, "w"))
        return np.array([cache[k] for k in keys], dtype=float)

    # ---------- chat ----------
    def chat(self, messages, op="generate", json_mode=False, tools=None, model=None):
        """Returns (message, usage_row). message has .content and .tool_calls (OpenAI object)."""
        model = model or self.chat_model
        t0 = time.perf_counter()
        if self.provider == "bedrock":
            return self._chat_bedrock(messages, op, json_mode, tools, model, t0)
        kwargs = dict(model=model, messages=messages)
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if tools:
            kwargs["tools"] = tools
        if model.startswith("gpt-5"):  # reasoning model: keep "thinking" short for fast lookups
            kwargs["reasoning_effort"] = "minimal"
        resp = self.client.chat.completions.create(**kwargs)
        u = resp.usage
        row = self.log.add(op, model, u.prompt_tokens, u.completion_tokens,
                           (time.perf_counter() - t0) * 1000, self.prices)
        return resp.choices[0].message, row

    # ---------- AWS Bedrock (Converse API: one call shape for every model) ----------
    def _chat_bedrock(self, messages, op, json_mode, tools, model, t0):
        system, msgs = [], []
        for m in messages:
            role, content = m["role"], m.get("content") or ""
            if role == "system":
                system.append({"text": content})
            elif role == "assistant" and m.get("tool_calls"):
                blocks = ([{"text": content}] if content else []) + [
                    {"toolUse": {"toolUseId": tc["id"], "name": tc["function"]["name"],
                                 "input": json.loads(tc["function"]["arguments"] or "{}")}} for tc in m["tool_calls"]]
                msgs.append({"role": "assistant", "content": blocks})
            elif role == "tool":
                try:
                    payload = json.loads(content)
                except Exception:
                    payload = {"result": content}
                block = {"toolResult": {"toolUseId": m["tool_call_id"],
                                        "content": [{"json": payload if isinstance(payload, dict) else {"result": payload}}]}}
                if msgs and msgs[-1]["role"] == "user" and msgs[-1].get("_tool"):
                    msgs[-1]["content"].append(block)   # several tool results go into ONE user message
                else:
                    msgs.append({"role": "user", "content": [block], "_tool": True})
            else:
                msgs.append({"role": role, "content": [{"text": content}]})
        if json_mode:
            last = next(x for x in reversed(msgs) if x["role"] == "user")
            last["content"][-1]["text"] += "\n\nReply with a single valid JSON object only. No markdown, no explanation."
        kwargs = dict(modelId=model, messages=[{k: v for k, v in x.items() if k != "_tool"} for x in msgs],
                      inferenceConfig={"maxTokens": 1500, "temperature": 0.2})
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["toolConfig"] = {"tools": [{"toolSpec": {"name": t["function"]["name"],
                                                            "description": t["function"].get("description", ""),
                                                            "inputSchema": {"json": t["function"]["parameters"]}}}
                                              for t in tools]}
        resp = self.client.converse(**kwargs)
        blocks = resp["output"]["message"]["content"]
        text = "".join(b.get("text", "") for b in blocks)
        calls = [SimpleNamespace(id=b["toolUse"]["toolUseId"],
                                 function=SimpleNamespace(name=b["toolUse"]["name"], arguments=json.dumps(b["toolUse"]["input"])))
                 for b in blocks if "toolUse" in b]
        if json_mode:
            text = _extract_json(text)
        u = resp.get("usage", {})
        row = self.log.add(op, model, u.get("inputTokens", 0), u.get("outputTokens", 0),
                           (time.perf_counter() - t0) * 1000, self.prices)
        return SimpleNamespace(content=text, tool_calls=calls or None), row

    def log_offline(self, op, prompt_text, output_text, t0):
        return self.log.add(op, "offline", len(prompt_text) // 4, len(output_text) // 4,
                            (time.perf_counter() - t0) * 1000, self.prices)


def _hash_embed(text, dim=256):
    """Offline stand-in for embeddings: hashed bag of words (NOT semantic)."""
    v = np.zeros(dim)
    for w in text.lower().split():
        w = "".join(c for c in w if c.isalnum())
        if w:
            v[int(hashlib.md5(w.encode()).hexdigest(), 16) % dim] += 1
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()
