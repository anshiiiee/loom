import re

STATUS_RE = re.compile(r"HTTP_\d{3}_[A-Z_]+|status\s*=\s*\d{3}")


def _changed(diff_text):
    minus, plus = [], []
    for l in diff_text.splitlines():
        if l.startswith("+++") or l.startswith("---"):
            continue
        if l.startswith("-"):
            minus.append(l[1:].strip())
        elif l.startswith("+"):
            plus.append(l[1:].strip())
    return minus, plus


def detect_rule_findings(diff_text):
    """Deterministic findings. Each is a VERIFIED FACT about the diff, not a guess."""
    minus, plus = _changed(diff_text)
    findings = []

    old_codes = sorted({m for l in minus for m in STATUS_RE.findall(l)})
    new_codes = sorted({m for l in plus for m in STATUS_RE.findall(l)})
    if old_codes != new_codes and (old_codes or new_codes):
        findings.append({
            "title": "HTTP status code changed",
            "status": "VERIFIED FACT",
            "detail": "Removed: " + (", ".join(old_codes) or "none")
                      + " | Added: " + (", ".join(new_codes) or "none"),
            "why_it_matters": "Clients and tests that check this response code may now behave differently (API contract).",
            "verify": "Search the tests and API clients for the old status code and run them.",
        })

    if any("permission_classes" in l or "IsAuthenticated" in l or "AllowAny" in l
           for l in minus + plus):
        findings.append({
            "title": "Permission or authentication setting touched",
            "status": "VERIFIED FACT",
            "detail": "A changed line mentions permissions or authentication.",
            "why_it_matters": "Access to this endpoint may have been widened or narrowed.",
            "verify": "Confirm the intended access level and test with an unauthenticated request.",
        })

    return findings