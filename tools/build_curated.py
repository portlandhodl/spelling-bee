#!/usr/bin/env python3
"""Build words.json and defs.json from the hand-curated lists in tools/curated/*.json.

Each curated entry: {"w": word, "t": tier 1-3, "m": [misspellings], "r": reason, "d": definition}.
Definitions shown in the game come from WordNet (most common senses), falling back to the
curated "d" when WordNet doesn't know the word.

Usage: NLTK_DATA=/path/to/nltk_data python3 tools/build_curated.py [target]
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_definitions import definitions  # noqa: E402
from nltk.corpus import wordnet as wn  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 5000

# Notorious words that must survive trimming even though they're short tier-1 words.
CLASSICS = {
    "pharaoh", "colonel", "gauge", "queue", "yacht", "khaki", "choir", "aisle", "bizarre", "psalm", "myrrh",
    "accommodate", "accommodation", "achieve", "acquire", "address", "aggressive", "amateur",
    "apparent", "argument", "basically", "beginning", "believe", "business", "calendar",
    "caribbean", "cemetery", "changeable", "colleague", "coming", "committed", "committee",
    "completely", "conscience", "conscious", "consensus", "definitely", "desperate", "dilemma",
    "disappear", "disappoint", "discipline", "embarrass", "embarrassment", "environment",
    "especially", "exaggerate", "exceed", "existence", "experience", "familiar", "fascinate",
    "february", "fluorescent", "foreign", "forty", "friend", "government", "grammar", "guarantee",
    "harass", "height", "hierarchy", "humorous", "hygiene", "hypocrisy", "ignorance",
    "immediately", "independent", "indispensable", "inoculate", "intelligence", "irresistible",
    "jewelry", "judgment", "knowledge", "leisure", "liaison", "library", "license", "lightning",
    "maintenance", "maneuver", "medieval", "millennium", "miniature", "mischievous", "misspell",
    "necessary", "neighbor", "noticeable", "occasion", "occasionally", "occur", "occurred",
    "occurrence", "pastime", "perseverance", "personnel", "playwright", "possession", "potatoes",
    "precede", "privilege", "pronunciation", "publicly", "questionnaire", "receipt", "receive",
    "recommend", "reference", "referred", "relevant", "religious", "repetition", "restaurant",
    "rhyme", "rhythm", "schedule", "seize", "separate", "sergeant", "siege", "successful",
    "supersede", "surprise", "threshold", "tomorrow", "tongue", "truly", "twelfth", "tyranny",
    "until", "vacuum", "vicious", "wednesday", "weird", "whether", "withhold", "writing",
    "written", "yacht",
}


def main():
    with open("/usr/share/dict/words") as f:
        dictionary = {line.strip().lower() for line in f}

    entries, seen, problems = [], set(), []
    for path in sorted(glob.glob(os.path.join(ROOT, "tools", "curated", "*.json"))):
        with open(path) as f:
            for e in json.load(f):
                w = str(e.get("w", "")).strip().lower()
                if not re.fullmatch(r"[a-z]+", w):
                    problems.append(f"{os.path.basename(path)}: bad word {w!r}")
                    continue
                if w in seen:
                    continue
                seen.add(w)
                known = w in dictionary or bool(wn.synsets(w))
                misses = [m.lower() for m in e.get("m", []) if isinstance(m, str)]
                misses = [m for m in dict.fromkeys(misses) if m != w and m not in dictionary][:3]
                entries.append({
                    "w": w, "t": int(e.get("t", 2)), "m": misses,
                    "r": str(e.get("r", "")).strip(), "d": str(e.get("d", "")).strip(), "known": known,
                })

    unknown = [e["w"] for e in entries if not e["known"]]
    print(f"{len(entries)} unique words; {len(unknown)} not in dictionary or WordNet")
    if unknown:
        print("  unverified:", " ".join(unknown))
    for p in problems:
        print("  " + p)

    # Too many? Drop the easiest first: tier 1, shortest words (never the classics).
    if len(entries) > TARGET:
        excess = len(entries) - TARGET
        candidates = [e for e in entries if e["w"] not in CLASSICS]
        drop = sorted(candidates, key=lambda e: (e["t"], len(e["w"])))[:excess]
        dropped = {e["w"] for e in drop}
        entries = [e for e in entries if e["w"] not in dropped]
    elif len(entries) < TARGET:
        print(f"  short of target by {TARGET - len(entries)}")

    entries.sort(key=lambda e: e["w"])
    words = [{"w": e["w"], "m": e["m"], "r": e["r"], "t": e["t"]} for e in entries]
    defs = {}
    for e in entries:
        base, d = definitions(e["w"])
        if d:
            defs[e["w"]] = {"d": d, **({"b": base} if base else {})}
        elif e["d"]:
            defs[e["w"]] = {"d": [["", e["d"]]]}

    with open(os.path.join(ROOT, "words.json"), "w") as f:
        json.dump(words, f, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(ROOT, "defs.json"), "w") as f:
        json.dump(defs, f, separators=(",", ":"), ensure_ascii=False)
    tiers = {t: sum(1 for e in entries if e["t"] == t) for t in (1, 2, 3)}
    print(f"wrote {len(words)} words (tiers {tiers}), {len(defs)} definitions")


if __name__ == "__main__":
    main()
