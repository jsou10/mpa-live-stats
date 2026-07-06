#!/usr/bin/env python3
"""
MPA Live Stats — pulls last-30-day totals (spend, leads, registrations,
purchases) across every ad account visible to the three Meta portfolio
tokens (SSS, MPA, CK) and writes stats.json.

Reliability rules:
- Any account that errors is skipped; if more than 25% of accounts error,
  or total spend comes back at zero, we EXIT NONZERO and publish nothing,
  so the last good stats.json stays live (stale beats wrong).
- Every Graph call retries 3x with backoff.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
TOKENS = {
    "SSS": os.environ.get("META_TOKEN_SSS", ""),
    "MPA": os.environ.get("META_TOKEN_MPA", ""),
    "CK": os.environ.get("META_TOKEN_CK", ""),
}


def get(url, tries=3):
    last = None
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001 - anything transient
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"graph call failed after {tries} tries: {last}")


def accounts_for(token):
    out = []
    url = f"{GRAPH}/me/adaccounts?fields=name&limit=200&access_token={token}"
    while url:
        d = get(url)
        out.extend(d.get("data", []))
        url = d.get("paging", {}).get("next")
    return out


def action_count(actions, *types):
    for t in types:  # first matching type wins (they overlap in Meta's list)
        for a in actions:
            if a.get("action_type") == t:
                return float(a.get("value", 0) or 0)
    return 0.0


def main():
    missing = [k for k, v in TOKENS.items() if not v]
    if missing:
        print(f"missing tokens: {missing}", file=sys.stderr)
        return 1

    # collect accounts, dedup across tokens (an account keeps its first token)
    accts = {}
    for name, tok in TOKENS.items():
        for a in accounts_for(tok):
            accts.setdefault(a["id"], tok)
    if not accts:
        print("no ad accounts visible", file=sys.stderr)
        return 1

    spend = leads = regs = purch = 0.0
    errors = 0
    for acct_id, tok in accts.items():
        q = urllib.parse.urlencode({
            "date_preset": "last_30d",
            "level": "account",
            "fields": "spend,actions",
            "access_token": tok,
        })
        try:
            rows = get(f"{GRAPH}/{acct_id}/insights?{q}").get("data", [])
        except Exception as e:  # noqa: BLE001
            print(f"skip {acct_id}: {e}", file=sys.stderr)
            errors += 1
            continue
        for row in rows:
            spend += float(row.get("spend", 0) or 0)
            actions = row.get("actions", []) or []
            leads += action_count(actions, "lead")
            regs += action_count(actions, "complete_registration")
            purch += action_count(actions, "omni_purchase", "purchase")

    if errors > len(accts) * 0.25:
        print(f"too many account errors ({errors}/{len(accts)}), not publishing", file=sys.stderr)
        return 1
    if spend <= 0:
        print("total spend is zero, refusing to publish", file=sys.stderr)
        return 1

    stats = {
        "window": "last_30d",
        "spend": round(spend),
        "leads": int(leads),
        "registrations": int(regs),
        "purchases": int(purch),
        "accounts": len(accts),
        "account_errors": errors,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    with open("stats.json", "w") as f:
        json.dump(stats, f, indent=1)
    print(json.dumps(stats))
    return 0


if __name__ == "__main__":
    sys.exit(main())
