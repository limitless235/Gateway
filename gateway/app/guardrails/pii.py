from __future__ import annotations

import re
from dataclasses import dataclass

# Deliberately simple demo patterns — good for screenshots / pressure tests.
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CC_RE = re.compile(r"\b(?:\d[ -]*?){13,19}\b")


@dataclass
class PIIResult:
    text: str
    redacted: bool
    findings: list[str]


def redact_pii(text: str) -> PIIResult:
    findings: list[str] = []
    out = text

    def _sub(pattern: re.Pattern[str], label: str, replacement: str) -> None:
        nonlocal out
        matches = pattern.findall(out)
        if matches:
            findings.append(f"{label}:{len(matches)}")
            out = pattern.sub(replacement, out)

    _sub(EMAIL_RE, "email", "[REDACTED_EMAIL]")
    _sub(PHONE_RE, "phone", "[REDACTED_PHONE]")
    _sub(SSN_RE, "ssn", "[REDACTED_SSN]")

    # Credit-card-like: only flag dense digit runs that look card-ish
    cc_matches = CC_RE.findall(out)
    real_ccs = []
    for m in cc_matches:
        digits = re.sub(r"\D", "", m)
        if 13 <= len(digits) <= 19:
            real_ccs.append(m)
    if real_ccs:
        findings.append(f"credit_card:{len(real_ccs)}")
        for m in real_ccs:
            out = out.replace(m, "[REDACTED_CC]", 1)

    return PIIResult(text=out, redacted=bool(findings), findings=findings)