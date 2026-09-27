"""Optional, remote Judge0 adapter for explicitly requested code execution.

Generated code is not uploaded or run automatically. A user must enable a
Judge0 endpoint and explicitly confirm in the UI before /execute is called.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


TARGET_ALIASES = {
    "python": ("python",),
    "javascript": ("javascript",),
    "typescript": ("typescript",),
    "c": ("c (", "c gcc", "c clang"),
    "c++": ("c++",),
    "c#": ("c#", "c sharp", "csharp"),
    "c# / .net": ("c#", "c sharp", "csharp"),
    "java": ("java ", "java("),
    "go": ("go ", "go ("),
    "rust": ("rust",),
    "php": ("php",),
    "ruby": ("ruby",),
    "bash": ("bash",),
    "swift": ("swift",),
    "kotlin": ("kotlin",),
}


class CompilerError(Exception):
    """A safe-to-display compiler configuration or provider error."""


def _base_url() -> str:
    value = os.getenv("JUDGE0_BASE_URL", "").strip().rstrip("/")
    if value:
        return value
    if os.getenv("JUDGE0_API_KEY"):
        value = "https://judge0-ce.p.rapidapi.com"
        return value
    # Shared public Judge0 CE is a zero-setup starter. Users can override this
    # with a personal provider or self-hosted endpoint for steadier capacity.
    return "https://ce.judge0.com"


def is_configured() -> bool:
    return bool(_base_url())


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    api_key = os.getenv("JUDGE0_API_KEY", "").strip()
    api_host = os.getenv("JUDGE0_API_HOST", "judge0-ce.p.rapidapi.com").strip()
    auth_token = os.getenv("JUDGE0_AUTH_TOKEN", "").strip()
    if api_key:
        headers["X-RapidAPI-Key"] = api_key
        headers["X-RapidAPI-Host"] = api_host
    if auth_token:
        headers["X-Auth-Token"] = auth_token
    return headers


def _request(path: str, body: dict | None = None, timeout: float = 12) -> dict | list:
    base = _base_url()
    if not base:
        raise CompilerError("Online compiler is not configured. See README.md to configure Judge0.")
    url = base + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method="POST" if body is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in {401, 403}:
            raise CompilerError("Judge0 rejected its credentials. Check the compiler API key or auth token.") from exc
        if exc.code == 429:
            raise CompilerError("The online compiler rate limit was reached. Try again later.") from exc
        raise CompilerError(f"Judge0 returned HTTP {exc.code}. Check the endpoint and plan.") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise CompilerError("Could not reach Judge0. Check the compiler endpoint and your internet connection.") from exc


def get_languages() -> list[dict]:
    if not is_configured():
        return []
    result = _request("/languages", timeout=10)
    if not isinstance(result, list):
        raise CompilerError("Judge0 returned an unexpected languages response.")
    return [item for item in result if isinstance(item, dict) and isinstance(item.get("id"), int) and isinstance(item.get("name"), str) and not item.get("is_archived", False)]


def connection_status() -> dict:
    """Probe the configured Judge0 host and report the languages it exposes."""
    base = _base_url()
    try:
        languages = get_languages()
    except CompilerError as exc:
        return {"configured": False, "provider": base, "error": str(exc), "languages": []}
    targets = []
    for target in TARGET_ALIASES:
        try:
            _language_id(target, languages)
            targets.append(target)
        except CompilerError:
            continue
    return {
        "configured": bool(languages),
        "provider": base,
        "languages": [item["name"] for item in languages],
        "supported_targets": targets,
        "error": "Judge0 returned no active languages." if not languages else "",
    }


def _language_id(target: str, languages: list[dict]) -> int:
    key = target.strip().lower()
    aliases = TARGET_ALIASES.get(key)
    if not aliases:
        raise CompilerError("The online compiler does not support this target. Choose a compilable language such as Python, JavaScript, C++, or C#.")
    candidates = []
    for item in languages:
        name = item["name"].lower()
        if any(name.startswith(alias) for alias in aliases):
            candidates.append(item)
    if not candidates:
        raise CompilerError(f"No {target} runtime is enabled by the configured Judge0 provider.")
    # Judge0 usually lists preferred active versions first; use that stable order.
    return candidates[0]["id"]


def execute(source_code: str, target: str, stdin: str = "") -> dict:
    if not isinstance(source_code, str) or not source_code.strip():
        raise CompilerError("There is no generated code to compile.")
    if len(source_code.encode("utf-8")) > 48_000:
        raise CompilerError("Code is too large for one compiler submission (48 KB maximum).")
    if not isinstance(stdin, str) or len(stdin.encode("utf-8")) > 8_000:
        raise CompilerError("Program input must be 8 KB or smaller.")

    language_id = _language_id(target, get_languages())
    submission = {
        "source_code": source_code,
        "language_id": language_id,
        "stdin": stdin,
        "cpu_time_limit": 2,
        "cpu_extra_time": 1,
        "wall_time_limit": 5,
        "memory_limit": 65536,
        "stack_limit": 16384,
        "max_processes_and_or_threads": 15,
        "enable_per_process_and_thread_time_limit": True,
    }
    created = _request("/submissions/?base64_encoded=false&wait=false", submission, timeout=12)
    token = created.get("token") if isinstance(created, dict) else None
    if not token:
        raise CompilerError("Judge0 did not return a submission token.")

    query = urllib.parse.urlencode({"base64_encoded": "false", "fields": "stdout,stderr,compile_output,message,status,time,memory"})
    deadline = time.monotonic() + 25
    result = {}
    while time.monotonic() < deadline:
        result = _request(f"/submissions/{urllib.parse.quote(token, safe='')}?{query}", timeout=10)
        status_id = result.get("status", {}).get("id") if isinstance(result, dict) else None
        if status_id not in {1, 2}:
            break
        time.sleep(0.5)
    else:
        raise CompilerError("The online compiler did not finish within 25 seconds.")
    if not isinstance(result, dict):
        raise CompilerError("Judge0 returned an unexpected execution response.")
    return {
        "status": result.get("status", {}).get("description", "Unknown"),
        "stdout": str(result.get("stdout") or "")[:20_000],
        "stderr": str(result.get("stderr") or "")[:20_000],
        "compile_output": str(result.get("compile_output") or "")[:20_000],
        "message": str(result.get("message") or "")[:2_000],
        "time": result.get("time"),
        "memory": result.get("memory"),
    }
