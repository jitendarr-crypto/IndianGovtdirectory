#!/usr/bin/env python3
"""
Daily checker for The India Directory.

For each tracked entity (a Union/State role, or a state's roster of MLAs),
this asks Claude -- with the web_search tool turned on -- to
verify who currently holds the post. Claude does the actual "reading the
messy news report / by-election result" work; this script just prompts it,
parses the structured reply, diffs it against what's stored, and writes
the result back to the data/ files.

Leadership files (chief + ministers) are considered low-volatility and are
safe to auto-update. MLA rosters are lower-volatility than an appointed
official's posting (five-year terms), but changes -- by-elections, deaths,
defections -- are politically sensitive, so they're still routed through the
PR the workflow opens for a human glance. See .github/workflows/daily-check.yml.

Run:
    ANTHROPIC_API_KEY=... python scripts/update.py
"""

import json
import os
import re
import sys
from datetime import date, datetime, timezone

import anthropic

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
TODAY = date.today().isoformat()

LEADERSHIP_FILES = [
    "union-leadership.json",
    "telangana-leadership.json",
    "andhra-leadership.json",
    "karnataka-leadership.json",
    "uttar_pradesh-leadership.json",
    "maharashtra-leadership.json",
    "bihar-leadership.json",
    "tamil_nadu-leadership.json",
    "madhya_pradesh-leadership.json",
]
MLA_FILES = [
    "telangana-mlas.json",
    "andhra-mlas.json",
    "karnataka-mlas.json",
    "uttar_pradesh-mlas.json",
    "maharashtra-mlas.json",
    "bihar-mlas.json",
    "tamil_nadu-mlas.json",
    "madhya_pradesh-mlas.json",
]
MP_FILES = [
    "mps-uttar_pradesh.json",
    "mps-maharashtra.json",
]

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

changes_log = []  # human-readable lines for the run summary / PR body


def path_for(filename):
    return os.path.join(DATA_DIR, filename)


def load(filename):
    with open(path_for(filename), "r", encoding="utf-8") as f:
        return json.load(f)


def save(filename, obj):
    with open(path_for(filename), "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def ask_claude(prompt):
    """Single-turn call with server-side web search enabled. Returns the
    model's final text (search happens inside this one call)."""
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}],
    )
    text_parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
    return "\n".join(text_parts)


def extract_json(text):
    """Pull a JSON array/object out of a reply that may include prose or
    ```json fences around it."""
    fenced = re.search(r"```(?:json)?\s*(\[.*\]|\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        return json.loads(fenced.group(1))
    bare = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if bare:
        return json.loads(bare.group(1))
    raise ValueError("No JSON found in model reply:\n" + text[:500])


# --------------------------------------------------------------------------
# Leadership (chief + ministers) -- low volatility, auto-applied
# --------------------------------------------------------------------------

def check_leadership(filename):
    data = load(filename)
    label = data.get("state", data.get("level", filename))

    people = [{"role": data["chief"]["role"], "name": data["chief"]["name"]}]
    people += [{"role": m["portfolio"], "name": m["name"]} for m in data["ministers"]]

    prompt = f"""You are verifying a civic directory for {label}, India.

Here is who the directory currently lists, one per line as "portfolio -- name":
{chr(10).join(f'- {p["role"]} -- {p["name"]}' for p in people)}

Use web search to check whether each of these is still accurate TODAY.
Only report a change if you find a credible, reasonably recent source
confirming a *different* person now holds that exact portfolio (e.g. a
cabinet reshuffle, resignation, or a new government). Do not report a
change based on a stale or ambiguous source, and do not invent portfolios
that were not listed above.

Reply with ONLY a JSON array (no prose, no markdown fences) of objects for
EVERY entry where the person has changed:
[
  {{"role": "<portfolio as given above>", "old_name": "<name as given above>",
    "new_name": "<current holder>", "source_url": "<url that supports this>",
    "confidence": "high|medium"}}
]
If nothing has changed, reply with an empty JSON array: []
"""
    reply = ask_claude(prompt)
    try:
        found_changes = extract_json(reply)
    except ValueError as e:
        print(f"[{filename}] could not parse model reply, skipping: {e}", file=sys.stderr)
        return

    applied = 0
    for ch in found_changes:
        if ch.get("confidence") != "high":
            changes_log.append(
                f"- SKIPPED (low confidence) {label}: {ch.get('role')} "
                f"'{ch.get('old_name')}' -> '{ch.get('new_name')}'"
            )
            continue

        if data["chief"]["role"] == ch.get("role"):
            target = data["chief"]
        else:
            target = next((m for m in data["ministers"] if m["portfolio"] == ch.get("role")), None)
        if target is None:
            continue

        if target["name"] != ch["new_name"]:
            changes_log.append(
                f"- UPDATED {label}: {ch.get('role')} "
                f"'{target['name']}' -> '{ch['new_name']}' "
                f"(source: {ch.get('source_url', 'n/a')})"
            )
            target["name"] = ch["new_name"]
            target["source_url"] = ch.get("source_url", target.get("source_url"))
            target["last_checked"] = TODAY
            target["confidence"] = "high"
            applied += 1

    if applied:
        save(filename, data)
    print(f"[{filename}] checked {len(people)} people, applied {applied} change(s)")


# --------------------------------------------------------------------------
# MLAs (elected representatives) -- lower volatility than appointed officials
# (five-year terms; changes only via by-elections, deaths, or defections),
# but still routed through a PR by the workflow since party-switch claims
# are politically sensitive and worth a human glance before publishing.
# --------------------------------------------------------------------------

def check_mlas(filename):
    data = load(filename)
    label = data["state"]
    items = data["items"]

    listing = "\n".join(
        f'- #{d["no"]} {d["constituency"]}: {d["name"]} ({d["party"] or "unknown party"})'
        for d in items
    )

    prompt = f"""You are verifying the sitting MLA (Member of the Legislative Assembly) for every
constituency of {label}, India.

Current directory state:
{listing}

Use web search to check each constituency. MLAs serve five-year terms so this
list should mostly be stable -- only flag a change if you find a credible,
specific source for one of these situations:
- A by-election has been held and a new MLA was declared winner
- The sitting MLA has died, resigned, or been disqualified
- The sitting MLA has formally defected to a different party (not just
  informal alignment/voting with another party -- an actual party switch
  reported as such)

Do not flag a change on rumor, speculation, or a single ambiguous source.
If nothing has changed for a constituency, leave it out of your reply.

Reply with ONLY a JSON array (no prose, no markdown fences):
[
  {{"constituency": "<constituency name exactly as listed above>",
    "name": "<current MLA>",
    "party": "<current party, or 'Independent'>",
    "note": "<short reason for the change, e.g. 'Won by-election Mar 2027'>",
    "source_url": "<url that supports this>",
    "confidence": "high|medium"}}
]
If you found nothing confidently for any constituency, reply with: []
"""
    reply = ask_claude(prompt)
    try:
        found = extract_json(reply)
    except ValueError as e:
        print(f"[{filename}] could not parse model reply, skipping: {e}", file=sys.stderr)
        return

    applied = 0
    for entry in found:
        target = next((d for d in items if d["constituency"] == entry.get("constituency")), None)
        if target is None or not entry.get("name"):
            continue
        if target.get("name") != entry["name"]:
            changes_log.append(
                f"- MLA UPDATE {label} / {target['constituency']}: "
                f"'{target.get('name')}' -> '{entry['name']}' "
                f"(confidence: {entry.get('confidence')}, source: {entry.get('source_url', 'n/a')})"
            )
            target["name"] = entry["name"]
            target["party"] = entry.get("party", target.get("party"))
            target["note"] = entry.get("note", target.get("note"))
            target["last_checked"] = TODAY
            target["confidence"] = entry.get("confidence", "medium")
            applied += 1

    if applied:
        save(filename, data)
    print(f"[{filename}] checked {len(items)} constituencies, applied {applied} change(s)")


def main():
    changes_log.append(f"# India Directory -- daily check, {datetime.now(timezone.utc).isoformat()}Z\n")

    for f in LEADERSHIP_FILES:
        check_leadership(f)
    for f in MLA_FILES:
        check_mlas(f)
    for f in MP_FILES:
        check_mlas(f)  # same shape (constituency/name/party), just a different chamber

    summary_path = os.path.join(DATA_DIR, "last-run-summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        if len(changes_log) == 1:
            f.write(changes_log[0] + "\nNo changes found today.\n")
        else:
            f.write("\n".join(changes_log) + "\n")

    print("\n".join(changes_log))


if __name__ == "__main__":
    main()
