from __future__ import annotations

import os
import re
from collections import Counter, defaultdict
from urllib.parse import urlparse

import httpx

from ..config import get_settings

try:
    import tldextract
    _HAS_TLDEXTRACT = True
except Exception:
    _HAS_TLDEXTRACT = False

# Rule-based host -> category mapping (registrable domain contains key)
_HOST_CATEGORY_MAP = {
    "lokos.in": "Education",
    "lokos": "Education",
    "google.com": "Work",
    "gmail": "Work",
    "facebook.com": "Social",
    "netflix.com": "Entertainment",
    "amazon": "Shopping",
    "flipkart": "Shopping",
    "bank": "Finance",
    "sbi": "Finance",
    "irctc": "Travel",
    "aicte": "Education",
    "nic.in": "Government",
    "gov.in": "Government",
    "edu": "Education",
}

_SYSTEM_CATEGORIES = ["Education", "Finance", "Work", "Government", "Health", "Shopping", "Social", "Other"]


def extract_host(url: str) -> str:
    if not url:
        return ""
    u = url.strip()
    if not u.startswith("http"):
        u = "https://" + u
    try:
        p = urlparse(u)
        h = (p.hostname or "").lower().strip()
        return h
    except Exception:
        return url.lower().strip()


def registrable_domain(host: str) -> str:
    if not host:
        return ""
    if _HAS_TLDEXTRACT:
        try:
            ext = tldextract.extract(host)
            if ext.domain and ext.suffix:
                return f"{ext.domain}.{ext.suffix}"
            return host
        except Exception:
            pass
    # fallback simple: last 2 labels (handles co.in as 3? we approximate)
    parts = host.split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "net", "org", "gov", "edu", "ac"):
        # e.g. aarani.el.r.appspot.com -> r.appspot.com? Actually appspot.com has 3 labels? Take last 2
        # For co.in, take last 3
        if len(parts) >= 3 and parts[-1] == "in" and parts[-2] in ("co", "ac", "gov", "net", "org"):
            return ".".join(parts[-3:])
        return ".".join(parts[-2:])
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


_MULTI_PART_SUFFIXES = {
    "co.in", "net.in", "org.in", "firm.in", "gen.in", "ac.in", "res.in", "gov.in",
    "co.uk", "org.uk", "ac.uk", "gov.uk",
    "com.au", "net.au", "org.au", "edu.au", "gov.au",
    "co.jp", "ne.jp", "or.jp", "ac.jp", "go.jp",
    "com.br", "com.mx", "com.ar", "com.cn", "com.sg", "co.nz", "co.za",
}

# well-known brand overrides (lowercase domain -> display name)
_BRAND_NAMES = {
    "google": "Google", "gmail": "Gmail", "youtube": "YouTube", "facebook": "Facebook",
    "instagram": "Instagram", "whatsapp": "WhatsApp", "amazon": "Amazon", "flipkart": "Flipkart",
    "microsoft": "Microsoft", "apple": "Apple", "linkedin": "LinkedIn", "twitter": "Twitter",
    "x": "X", "netflix": "Netflix", "github": "GitHub", "paypal": "PayPal",
    "irctc": "IRCTC", "sbi": "SBI", "hdfcbank": "HDFC Bank", "icicibank": "ICICI Bank",
    "axisbank": "Axis Bank", "kotak": "Kotak", "paytm": "Paytm", "phonepe": "PhonePe",
    "googlepay": "Google Pay", "razorpay": "Razorpay", "zoho": "Zoho", "slack": "Slack",
}


def display_name_for_domain(reg: str) -> str:
    """accounts.google.com -> Google, lokos.in -> Lokos"""
    if not reg or reg == "no-host":
        return reg
    labels = [l for l in reg.split(".") if l]
    if not labels:
        return reg
    if len(labels) >= 3 and f"{labels[-2]}.{labels[-1]}" in _MULTI_PART_SUFFIXES:
        core = labels[-3]
    elif len(labels) >= 2:
        core = labels[-2]
    else:
        core = labels[0]
    if core in _BRAND_NAMES:
        return _BRAND_NAMES[core]
    return core[:1].upper() + core[1:] if core else reg


def host_group_key_for(url: str) -> tuple[str, str, str]:
    h = extract_host(url)
    reg = registrable_domain(h)
    return (h, reg, reg or h)


def group_by_registrable(rows) -> list[dict]:
    """rows are ImportRow with title,url etc. Returns host_groups collapsed by registrable_domain."""
    groups: dict[str, dict] = {}
    for r in rows:
        h, reg, key = host_group_key_for(r.url)
        g = groups.setdefault(reg or h or "no-host", {"registrable_domain": reg or h or "no-host", "exact_hosts": set(), "count": 0, "sample_titles": [], "sample_usernames": []})
        g["exact_hosts"].add(h)
        g["count"] += 1
        if len(g["sample_titles"]) < 3:
            g["sample_titles"].append(r.title[:60])
            g["sample_usernames"].append(r.username[:40])
    out = []
    for reg, g in groups.items():
        out.append({
            "registrable_domain": reg,
            "display_name": display_name_for_domain(reg),
            "exact_hosts": sorted(g["exact_hosts"]),
            "count": g["count"],
            "sample_titles": g["sample_titles"],
        })
    # sort by count desc
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


def _rule_category_for(domain: str) -> str:
    d = domain.lower()
    for host_key, cat in _HOST_CATEGORY_MAP.items():
        if host_key in d:
            return cat
    # check android special: facebook, netflix etc handled above
    return "Other"


def propose_smart_groups(host_groups: list[dict], use_ai: bool = True) -> list[dict]:
    """Rule-based fallback always; AI enriches category names if key present and enabled."""
    # rule first
    smart = []
    for g in host_groups:
        reg = g["registrable_domain"]
        cat = _rule_category_for(reg)
        smart.append({
            "registrable_domain": reg,
            "display_name": display_name_for_domain(reg),
            "count": g["count"],
            "proposed_category": cat,
            "proposed_subcategory": None,
            "confidence": 0.7 if cat != "Other" else 0.4,
            "is_ai": False,
        })

    if not use_ai:
        return smart

    settings = get_settings()
    key = settings.opencode_api_key or os.getenv("OPENCODE_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    # also check temp file env
    if not key:
        # try reading from .env file manually? pydantic already loads
        key = getattr(settings, "opencode_api_key", "")
    if not key or len(key) < 10:
        return smart

    # AI assist: batch up to 30 domains
    try:
        return _ai_enrich(smart, host_groups, key, settings.opencode_api_base)
    except Exception:
        return smart


def _ai_enrich(smart: list[dict], host_groups: list[dict], api_key: str, base_url: str) -> list[dict]:
    # Build prompt
    payload_domains = []
    for g in host_groups[:30]:
        payload_domains.append(f"- {g['registrable_domain']} (count {g['count']}, samples: {', '.join(g['sample_titles'][:2])})")
    prompt = (
        "You are a vault admin assistant for an Indian government/education password manager. "
        "Given host groups (registrable domains) with counts, suggest a smart category for each. "
        "Categories must be one of: Education, Finance, Work, Government, Health, Shopping, Social, Travel, Other. "
        "Keep it simple, no subcategory. Return JSON array of objects {registrable_domain, proposed_category, confidence 0-1}.\n"
        "Groups:\n" + "\n".join(payload_domains) + "\nReturn JSON only."
    )
    # Call OpenAI compatible endpoint
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 800,
    }
    try:
        with httpx.Client(timeout=4.0) as client:
            resp = client.post(url, headers=headers, json=body)
            if resp.status_code != 200:
                return smart
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            # extract JSON array
            import json, re
            m = re.search(r"\[.*\]", content, re.DOTALL)
            if not m:
                return smart
            arr = json.loads(m.group(0))
            # map back
            mp = {x["registrable_domain"]: x for x in arr if "registrable_domain" in x}
            for s in smart:
                if s["registrable_domain"] in mp:
                    ai_cat = mp[s["registrable_domain"]].get("proposed_category", "")
                    if ai_cat in _SYSTEM_CATEGORIES:
                        s["proposed_category"] = ai_cat
                        s["confidence"] = float(mp[s["registrable_domain"]].get("confidence", 0.8))
                        s["is_ai"] = True
            return smart
    except Exception:
        return smart
