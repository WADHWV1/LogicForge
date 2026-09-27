"""Deterministic, non-executing checks used before a conversion is returned."""
from __future__ import annotations

import ast
import re

KEYWORDS = set("def if else elif for while return class function const let var int float string bool true false null None and or not in is async await public private static void new using namespace event listener else elif try catch finally import from as pass break continue".split())
ASSIGNMENT = re.compile(r"\b(?:def|function|func|fn)\s+([A-Za-z_]\w*)\s*\(|\b(?:public\s+|private\s+|static\s+|const\s+|let\s+|var\s+|int\s+|float\s+|double\s+|bool\s+|string\s+|String\s+)?([A-Za-z_]\w*)\s*(?:[:=]|\+=|-=)")


def extract_code(text: str) -> tuple[str, str]:
    match = re.search(r"```([\w+#.-]*)\s*([\s\S]*?)```", text)
    return (match.group(2).strip(), match.group(1)) if match else (text.strip(), "")


def requested_identifiers(text: str) -> list[str]:
    names = []
    for match in ASSIGNMENT.finditer(text):
        name = match.group(1) or match.group(2)
        if name and name.lower() not in KEYWORDS and name not in names:
            names.append(name)
    return names[:30]


def run_static_checks(code: str, language: str, original_input: str) -> list[dict[str, str]]:
    checks = []
    names = requested_identifiers(original_input)
    missing = [name for name in names if not re.search(rf"(?<![\w]){re.escape(name)}(?![\w])", code)]
    checks.append({
        "name": "Requested identifiers",
        "status": "PASS" if not missing else "REVIEW",
        "detail": "All detected variable/function names appear in the output." if not missing else "Names not found: " + ", ".join(missing),
    })
    if language.lower() == "python":
        try:
            ast.parse(code)
            checks.append({"name": "Python syntax", "status": "PASS", "detail": "Python AST parser accepted the code; this does not validate runtime behavior."})
        except SyntaxError as error:
            checks.append({"name": "Python syntax", "status": "FAIL", "detail": f"Line {error.lineno}: {error.msg}"})
    else:
        checks.append({"name": "Syntax parser", "status": "NOT RUN", "detail": f"No non-executing {language or 'target-language'} parser is configured."})
    checks.append({"name": "Code execution", "status": "NOT RUN", "detail": "Not run automatically during conversion; use the online compiler only after reviewing and confirming the code."})
    return checks


def format_check_report(checks: list[dict[str, str]], retrieval: dict, reviewer: dict) -> str:
    lines = ["", "Pre-final checks", f"- Retrieval: {retrieval['method']}; references: " + (", ".join(i["title"] for i in retrieval["items"]) or "none"), f"- Independent review: {reviewer.get('verdict', 'UNAVAILABLE')}"]
    for finding in reviewer.get("findings", [])[:6]:
        lines.append(f"  - Review note: {finding}")
    for check in checks:
        lines.append(f"- {check['name']}: {check['status']} — {check['detail']}")
    return "\n".join(lines)
