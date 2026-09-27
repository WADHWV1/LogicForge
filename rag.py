"""Small, local-first retrieval layer for LogicForge.

No corpus or user prompt is uploaded for retrieval. If a local Ollama server is
available, its embedding endpoint is used; otherwise a standard-library TF-IDF
ranker keeps the app usable without extra services.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.request
from collections import Counter


KNOWLEDGE = [
    {"id": "intent-identifiers", "title": "Intent and identifier preservation", "text": "Treat variable names, function names, keys, and explicit requirements in the user's sketch as a contract. Preserve spelling and casing unless the selected language makes a name invalid; explain any necessary rename. Separate the intended behavior from syntax noise. If a requirement conflicts with another, flag the conflict instead of silently changing the design."},
    {"id": "control-flow", "title": "Control flow and execution order", "text": "Initialize state before it is used. Register event handlers before events can arrive. Use explicit branches for mutually exclusive cases and independent conditions where several inputs can be active. Keep computation in the function that owns the behavior and pass needed values explicitly."},
    {"id": "movement", "title": "Keyboard movement logic", "text": "For keyboard movement, map each key to a boolean, combine booleans to detect any movement, and update coordinates along the correct axes. Multiply speed by delta time for frame-rate-independent movement. State assumptions about the game loop, event object, key casing, and position ownership."},
    {"id": "python", "title": "Python correctness", "text": "Python blocks require consistent indentation. Names used inside a function must be parameters, local values, or declared state; avoid accidental UnboundLocalError when updating outer state. Use ast.parse only for syntax validation; syntax parsing does not prove runtime correctness."},
    {"id": "dotnet", "title": "C# and modern .NET", "text": "Use idiomatic C# and standard .NET types. Keep framework-specific APIs out unless the user selected a framework such as ASP.NET Core or Unity. Distinguish local variables from mutable object state, use descriptive method parameters, and identify the .NET SDK/framework requirement."},
    {"id": "validation", "title": "Safe code review", "text": "Never run generated code as part of a conversion. Validate structure with non-executing parsers where available, check explicitly named identifiers, then ask a reviewer model for logic gaps. Report exactly which checks ran and which did not; a model review is not proof of correctness."},
    {"id": "beginner", "title": "Beginner-friendly explanations", "text": "Explain the code in execution order. Refer to the actual names in the code. Distinguish input, derived values, state, and function responsibilities. Explain why a correction matters and list assumptions without claiming the result was tested when it was not."},
]

TOKEN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*|[.]+|[^\w\s]", re.UNICODE)
_embedding_cache: dict[str, list[float]] = {}


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN.findall(text) if t.strip()]


def _tfidf_rank(query: str, docs: list[dict], limit: int) -> list[tuple[dict, float]]:
    corpus = [_tokens(d["title"] + " " + d["text"]) for d in docs]
    query_tokens = _tokens(query)
    doc_freq = Counter(token for tokens in corpus for token in set(tokens))
    n = max(len(corpus), 1)
    scores = []
    for doc, tokens in zip(docs, corpus):
        counts = Counter(tokens)
        length_norm = 1 + math.log(max(len(tokens), 1))
        score = 0.0
        for token in query_tokens:
            if token in counts:
                idf = math.log(1 + n / (1 + doc_freq[token]))
                score += (1 + math.log(counts[token])) * idf / length_norm
        scores.append((doc, score))
    return sorted(scores, key=lambda item: item[1], reverse=True)[:limit]


def _ollama_embed_many(texts: list[str]) -> list[list[float]]:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    missing = [text for text in texts if model + "\0" + text not in _embedding_cache]
    if missing:
        body = json.dumps({"model": model, "input": missing}).encode("utf-8")
        request = urllib.request.Request(base + "/api/embed", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=8) as response:
            vectors = json.loads(response.read().decode("utf-8"))["embeddings"]
        if len(vectors) != len(missing):
            raise ValueError("Ollama returned a different number of embeddings than requested")
        for text, vector in zip(missing, vectors):
            _embedding_cache[model + "\0" + text] = vector
    return [_embedding_cache[model + "\0" + text] for text in texts]


def _ollama_embed(text: str) -> list[float]:
    return _ollama_embed_many([text])[0]


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    ln = math.sqrt(sum(a * a for a in left))
    rn = math.sqrt(sum(b * b for b in right))
    return dot / (ln * rn) if ln and rn else 0.0


def retrieve(query: str, limit: int = 4) -> dict:
    """Return relevant snippets plus an honest retrieval-method label."""
    try:
        documents = [doc["title"] + "\n" + doc["text"] for doc in KNOWLEDGE]
        vectors = _ollama_embed_many([query, *documents])
        query_vector, doc_vectors = vectors[0], vectors[1:]
        ranked = [(doc, _cosine(query_vector, vector)) for doc, vector in zip(KNOWLEDGE, doc_vectors)]
        ranked.sort(key=lambda item: item[1], reverse=True)
        method = "Ollama local embeddings"
    except (OSError, KeyError, IndexError, ValueError, urllib.error.URLError, TimeoutError):
        ranked = _tfidf_rank(query, KNOWLEDGE, limit)
        method = "local TF-IDF fallback"
    selected = [{**doc, "score": round(float(score), 4)} for doc, score in ranked[:limit]]
    return {"method": method, "items": selected}
