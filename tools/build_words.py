#!/usr/bin/env python3
"""Build words.json: ~5000 commonly misspelled English words with a reason.

Sources (download into DATA_DIR first):
  - Wikipedia "Lists of common misspellings" (wiki.txt, l_A.txt..l_Z.txt), CC BY-SA
  - Birkbeck spelling error corpus, Roger Mitton (bbk_missp/aspell/wikipedia.dat)
  - FrequencyWords en_50k.txt (hermitdave), used only for ranking

Usage: python3 -I tools/build_words.py /tmp/sb-data words.json
"""
import difflib
import glob
import json
import math
import os
import re
import sys
from collections import defaultdict

TARGET = 5000

# Hand-written reasons for the classic troublemakers. These always make the list.
CURATED = {
    "accommodate": "Big enough for double 'c' AND double 'm' — accommodate has room for both.",
    "accommodation": "Double 'c' and double 'm', just like accommodate.",
    "achieve": "'i' before 'e' except after 'c' — here there's no 'c' before the 'ie'.",
    "acquire": "The 'kw' sound is spelled 'cqu' — people forget the 'c'.",
    "address": "Double 'd' and double 's'.",
    "aggressive": "Double 'g' and double 's'.",
    "amateur": "Ends in French '-eur', not '-ure' or '-er'.",
    "apparent": "Double 'p', single 'r', and ends in '-ent'.",
    "argument": "The 'e' in 'argue' is dropped before '-ment'.",
    "basically": "Built from 'basic' + '-ally', not '-ly'.",
    "beginning": "Double 'n' — the stressed final consonant doubles before '-ing'.",
    "believe": "'i' before 'e' — and you can't beLIEve a LIE.",
    "business": "'busy' + '-ness': the 'y' becomes 'i' — the 'i' is silent.",
    "calendar": "Ends in '-ar', not '-er'.",
    "caribbean": "One 'r', double 'b'.",
    "cemetery": "Three 'e's and no 'a' — eee, like a scream in the cemetery.",
    "changeable": "Keep the 'e' after 'g' so it stays soft: change + able.",
    "colleague": "Double 'l', ends in '-league'.",
    "coming": "Drop the 'e' from 'come' before '-ing'; no double 'm'.",
    "committed": "Double 'm' and double 't'.",
    "committee": "Double 'm', double 't', double 'e'.",
    "completely": "Keep the 'e' from 'complete' before '-ly'.",
    "conscience": "'con' + 'science'.",
    "conscious": "The 'sh' sound is spelled 'sci'.",
    "consensus": "From 'consent', so it's 'sens', not 'cens'.",
    "definitely": "Look for the word 'finite' inside it — no 'a' anywhere.",
    "desperate": "Has an 'e' after the 'p' that's often heard as 'a' or swallowed.",
    "dilemma": "Double 'm', not 'mn'.",
    "disappear": "'dis' + 'appear': one 's', double 'p'.",
    "disappoint": "'dis' + 'appoint': one 's', double 'p'.",
    "discipline": "Silent 'c' after the 's'.",
    "embarrass": "Double 'r' and double 's' — you go Really Red and Smile Shyly.",
    "embarrassment": "Double 'r' and double 's'.",
    "environment": "Hidden 'n' before '-ment' — iron is in the environment.",
    "especially": "'especial' + '-ly': double 'l'.",
    "exaggerate": "Double 'g', single 'r'.",
    "exceed": "One of three '-ceed' words: exceed, proceed, succeed.",
    "existence": "Ends in '-ence', not '-ance'.",
    "experience": "Ends in '-ence'.",
    "familiar": "Ends in '-iar'.",
    "fascinate": "Silent 'c' after the 's'.",
    "february": "Silent first 'r' — Feb-RU-ary.",
    "fluorescent": "'fluor' (u before o) + 'escent' (silent 'c').",
    "foreign": "Breaks the i-before-e rule, plus a silent 'g'.",
    "forty": "Four loses its 'u' in forty.",
    "friend": "'i' before 'e' — a friend to the end.",
    "government": "Hidden 'n' from 'govern' before '-ment'.",
    "grammar": "Ends in '-ar', not '-er'.",
    "guarantee": "Silent 'u' after 'g'.",
    "harass": "One 'r', double 's'.",
    "height": "Breaks i-before-e; ends in '-ght', not '-th'.",
    "hierarchy": "'i' before 'e', then 'arch'.",
    "humorous": "American 'humor' + '-ous' — the 'u' of 'humour' is dropped.",
    "hygiene": "'y' then 'ie'.",
    "hypocrisy": "Ends in '-isy', not '-acy'.",
    "ignorance": "Ends in '-ance'.",
    "immediately": "Double 'm', and keep the 'e' before '-ly'.",
    "independent": "All 'e's — ends in '-ent', not '-ant'.",
    "indispensable": "Ends in '-able'.",
    "inoculate": "One 'n', one 'c'.",
    "intelligence": "Double 'l' and ends in '-ence'.",
    "irresistible": "Double 'r' and ends in '-ible'.",
    "jewelry": "'jewel' + '-ry' (British: jewellery).",
    "judgment": "No 'e' after the 'g' (judgement is the British variant).",
    "knowledge": "Silent 'k', and 'ledge' at the end.",
    "leisure": "Breaks the i-before-e rule.",
    "liaison": "Two 'i's — one either side of the 'a'.",
    "library": "Don't skip the first 'r' — li-BRAR-y.",
    "license": "'c' then 's' (US).",
    "lightning": "No 'e' — lightening means making lighter.",
    "maintenance": "'main' + 'ten' + 'ance' — not 'maintain'.",
    "maneuver": "US spelling: '-euver'.",
    "medieval": "'medi' + 'eval' — the middle ages.",
    "millennium": "Double 'l' and double 'n'.",
    "miniature": "Don't forget the 'a' after 'mini'.",
    "mischievous": "Only three syllables: mis-chie-vous — no extra 'i'.",
    "misspell": "'mis' + 'spell' — so double 's'.",
    "necessary": "One collar (c), two sleeves (ss).",
    "neighbor": "'ei' says 'ay', as in neighbor and weigh.",
    "noticeable": "Keep the 'e' so the 'c' stays soft.",
    "occasion": "Double 'c', single 's'.",
    "occasionally": "Double 'c', single 's', double 'l'.",
    "occur": "Double 'c', single 'r'.",
    "occurred": "Double 'c', and the 'r' doubles before '-ed'.",
    "occurrence": "Double 'c', double 'r', ends in '-ence'.",
    "pastime": "'pass' + 'time', but only one 's' and one 't'.",
    "perseverance": "'per' + 'severance' — no 'r' in the middle.",
    "personnel": "Double 'n', ends in '-el' (staff, not personal).",
    "playwright": "A 'wright' is a maker, not a writer.",
    "possession": "Two sets of double 's'.",
    "potatoes": "Plural of potato adds '-es'.",
    "precede": "'-cede', not '-ceed'.",
    "privilege": "No 'd' — and it's 'i', 'i', 'e'.",
    "pronunciation": "'pronounce' loses its 'o' — pro-NUN-ciation.",
    "publicly": "Just '-ly', not '-ally'.",
    "questionnaire": "Double 'n'.",
    "receipt": "'e' before 'i' after 'c', plus a silent 'p'.",
    "receive": "'e' before 'i' after 'c'.",
    "recommend": "One 'c', double 'm'.",
    "reference": "Single 'r' in the middle, ends in '-ence'.",
    "referred": "Stress on the last syllable, so the 'r' doubles.",
    "relevant": "'l' before 'v', ends in '-ant'.",
    "religious": "Ends in '-gious'.",
    "repetition": "'e' then 'e' — from 'repeat'.",
    "restaurant": "'restau' + 'rant'.",
    "rhyme": "Silent 'h' after 'r'.",
    "rhythm": "Rhythm Helps Your Two Hips Move.",
    "schedule": "'sch' at the start.",
    "seize": "Breaks the i-before-e rule.",
    "separate": "There's 'a rat' in sep-A-RAT-e.",
    "sergeant": "'ser' + 'geant'.",
    "siege": "'i' before 'e'.",
    "successful": "Double 'c', double 's', one 'l'.",
    "supersede": "The only English word ending in '-sede'.",
    "surprise": "Don't drop the first 'r' — SUR-prise.",
    "threshold": "Only one 'h' in the middle — thresh + old.",
    "tomorrow": "One 'm', double 'r'.",
    "tongue": "Ends in '-ngue'.",
    "truly": "'true' drops its 'e' before '-ly'.",
    "twelfth": "Don't forget the 'f' before 'th'.",
    "tyranny": "'y' after 't', double 'n'.",
    "until": "Only one 'l' (unlike 'till').",
    "vacuum": "One 'c', double 'u'.",
    "vicious": "'vic' + 'ious'.",
    "weird": "Weird breaks the i-before-e rule — that's what makes it weird.",
    "wednesday": "Silent 'd' — Wed-nes-day.",
    "whether": "Silent 'h' after 'w'.",
    "withhold": "'with' + 'hold': double 'h'.",
    "writing": "One 't' — 'write' just drops its 'e'.",
    "written": "Double 't' — the short 'i' sound doubles the consonant.",
    "yacht": "Silent 'ch' — from Dutch 'jacht'.",
}

BLOCK = {"larry", "youtube", "fuck", "shit", "cunt", "nigger", "bitch", "wank", "piss", "faggot", "slut", "whore"}
SILENT_CLUSTERS = ["kn", "gn", "wr", "mb", "mn", "ps", "rh", "gh", "sc", "bt", "stl", "wh", "gu", "bu", "ch"]
VOWELS = set("aeiou")
SUFFIX_PAIRS = [
    ("able", "ible"), ("ance", "ence"), ("ancy", "ency"), ("ant", "ent"), ("ary", "ery"),
    ("ise", "ize"), ("ceed", "cede"), ("sion", "tion"), ("ous", "us"), ("ally", "ly"),
    ("ar", "er"), ("or", "er"), ("cial", "tial"), ("ful", "full"),
]


def load_freq(path):
    freq = {}
    with open(path) as f:
        for i, line in enumerate(f):
            parts = line.split()
            if len(parts) == 2:
                freq[parts[0]] = (i + 1, int(parts[1]))
    return freq


def clean(s):
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\[[^\]]*\]", "", s)
    return s.strip()


def load_wiki(data_dir):
    """Yield (misspelling, correct) from the Wikipedia lists."""
    with open(os.path.join(data_dir, "wiki.txt")) as f:
        for line in f:
            if "->" in line:
                bad, good = line.strip().split("->", 1)
                goods = [g.strip() for g in good.split(",")]
                if len(goods) == 1:
                    yield bad.strip(), goods[0]
    for path in glob.glob(os.path.join(data_dir, "l_*.txt")):
        with open(path) as f:
            for line in f:
                m = re.match(r"\*\s*(?:\{\{search link\|\"?([^|\"]+)\"?\|[^}]*\}\}|([A-Za-z']+))\s*\((.*)\)", line)
                if not m:
                    continue
                bad = m.group(1) or m.group(2)
                good = clean(m.group(3))
                if "," in good or ";" in good or " " in good or "variant" in good:
                    continue
                yield bad.strip(), good


def load_bbk(path):
    correct = None
    with open(path, errors="replace") as f:
        for line in f:
            tok = line.split()
            if not tok:
                continue
            if tok[0].startswith("$"):
                correct = tok[0][1:]
            elif correct:
                yield tok[0].replace("_", " "), correct


def is_silent_drop(word, idx):
    for c in SILENT_CLUSTERS:
        start = max(0, idx - len(c) + 1)
        if c in word[start:idx + len(c)]:
            return c
    return None


def reason_for(word, bad):
    """Explain the trap using the difference between word and a typical misspelling."""
    w, b = word, bad.lower()
    if " " in b:
        return f"Written as one word: '{w}'."
    if len(w) == len(b):
        diffs = [i for i in range(len(w)) if w[i] != b[i]]
        if len(diffs) == 2 and diffs[1] == diffs[0] + 1 and w[diffs[0]] == b[diffs[1]] and w[diffs[1]] == b[diffs[0]]:
            pair = w[diffs[0]:diffs[0] + 2]
            if pair in ("ie", "ei"):
                if pair == "ei" and diffs[0] > 0 and w[diffs[0] - 1] == "c":
                    return "'i' before 'e' except after 'c' — this one follows the rule: 'ei' after 'c'."
                if pair == "ei":
                    return "Breaks the 'i before e' rule — it's 'ei' here."
                return "'i' before 'e' — this one follows the rule."
            return f"Letters get swapped: it's '{pair}', not '{pair[::-1]}'."
    for a, c in SUFFIX_PAIRS:
        for good, wrong in ((a, c), (c, a)):
            if w.endswith(good) and b.endswith(wrong) and w[:-len(good)] == b[:-len(wrong)]:
                return f"Ends in '-{good}', not '-{wrong}'."
    sm = difflib.SequenceMatcher(None, w, b, autojunk=False)
    ops = [op for op in sm.get_opcodes() if op[0] != "equal"]
    if len(ops) == 1:
        tag, i1, i2, j1, j2 = ops[0]
        if tag == "delete" and i2 - i1 == 1:
            ch = w[i1]
            if (i1 > 0 and w[i1 - 1] == ch) or (i1 + 1 < len(w) and w[i1 + 1] == ch):
                return f"Double '{ch}' — it's easy to write just one."
            sil = is_silent_drop(w, i1)
            if sil:
                return f"Silent '{ch}' in '{sil}' — you don't hear it, but it's there."
            if ch in VOWELS:
                return f"Don't swallow the '{ch}' — it's barely pronounced but it's there."
            return f"Easy to skip the '{ch}' — don't leave it out."
        if tag == "insert" and j2 - j1 == 1:
            ch = b[j1]
            if (j1 > 0 and b[j1 - 1] == ch) or (j1 + 1 < len(b) and b[j1 + 1] == ch):
                return f"Only one '{ch}' — don't double it."
            return f"No extra '{ch}' — it's spelled '{w}'."
        if tag == "replace":
            g, x = w[i1:i2], b[j1:j2]
            if len(g) == 1 and len(x) == 1 and g in VOWELS and x in VOWELS:
                return f"Vowel trap: it's '{g}' here, not '{x}'."
            sounds = {frozenset(("c", "s")): "soft 'c' sounds like 's'", frozenset(("c", "k")): "'c' and 'k' make the same sound",
                      frozenset(("ph", "f")): "'ph' makes the 'f' sound", frozenset(("g", "j")): "soft 'g' sounds like 'j'",
                      frozenset(("s", "z")): "'s' often sounds like 'z'", frozenset(("y", "i")): "'y' and 'i' can sound the same",
                      frozenset(("ck", "k")): "'ck' and 'k' sound the same", frozenset(("sh", "ti")): "'ti' can make the 'sh' sound",
                      frozenset(("sh", "ci")): "'ci' can make the 'sh' sound", frozenset(("ch", "tu")): "'tu' can make the 'ch' sound"}
            hint = sounds.get(frozenset((g, x)))
            if hint:
                return f"It's '{g}', not '{x}' — {hint}."
            return f"The tricky part is '{g}' (not '{x}')."
    if len(ops) == 2 and all(op[0] in ("delete", "insert") for op in ops):
        (t1, a1, a2, b1, b2), (t2, c1, c2, d1, d2) = ops
        if t1 == "delete" and t2 == "insert" and w[a1:a2] == b[d1:d2] and a2 - a1 == 1:
            return f"The '{w[a1]}' wanders — check exactly where it sits in '{w}'."
        if t1 == "insert" and t2 == "delete" and b[b1:b2] == w[c1:c2] and b2 - b1 == 1:
            return f"The '{w[c1]}' wanders — check exactly where it sits in '{w}'."
    doubles = sorted({w[i] for i in range(len(w) - 1) if w[i] == w[i + 1]})
    if doubles:
        return "Watch the doubles: " + " and ".join(f"'{d}{d}'" for d in doubles) + "."
    return f"Often written '{b}' — compare it letter by letter with '{w}'."



def main():
    data_dir, out = sys.argv[1], sys.argv[2]
    freq = load_freq(os.path.join(data_dir, "en_50k.txt"))
    with open("/usr/share/dict/words") as f:
        dictionary = {line.strip() for line in f}

    misses = defaultdict(lambda: defaultdict(int))  # word -> misspelling -> count
    sources = defaultdict(set)
    pairs = [("wiki", load_wiki(data_dir))]
    for name in ("missp", "aspell", "wikipedia"):
        pairs.append((name, load_bbk(os.path.join(data_dir, f"bbk_{name}.dat"))))
    for src, it in pairs:
        for bad, good in it:
            if not re.fullmatch(r"[a-z]+", good) or len(good) < 5 or good in BLOCK:
                continue
            if good not in dictionary and good not in freq:
                continue
            bad = bad.lower().strip()
            if bad == good or not re.fullmatch(r"[a-z ]+", bad) or bad in BLOCK:
                continue
            # A real word is a word-choice slip (band/bend), not a spelling error.
            if " " not in bad and (bad in dictionary or bad in freq):
                continue
            misses[good][bad] += 1
            sources[good].add(src)

    def score(w):
        rank = freq.get(w, (60000, 0))[0]
        commonness = max(0.0, 11 - math.log(rank)) * 0.6  # higher = more common
        evidence = 2.5 * len(sources[w]) + 3 * math.log1p(sum(misses[w].values())) + (1 if len(w) >= 7 else 0)
        return (w in CURATED, evidence + commonness)

    candidates = set(misses) | set(CURATED)
    ranked = sorted(candidates, key=score, reverse=True)[:TARGET]

    words = []
    for w in ranked:
        m = misses.get(w, {})
        # prefer misspellings that don't look like random typos (closest by ratio)
        common = sorted(m, key=lambda b: (-m[b], -difflib.SequenceMatcher(None, w, b).ratio()))[:3]
        reason = CURATED.get(w) or (reason_for(w, common[0]) if common else "")
        words.append({"w": w, "m": common, "r": reason})
    words.sort(key=lambda e: e["w"])
    with open(out, "w") as f:
        json.dump(words, f, separators=(",", ":"), ensure_ascii=False)
    print(f"{len(candidates)} candidates, wrote {len(words)} words to {out}")


if __name__ == "__main__":
    main()
