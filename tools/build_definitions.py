#!/usr/bin/env python3
"""Build defs.json: up to 3 common WordNet definitions for every word in words.json.

Needs nltk and the WordNet corpus (NLTK_DATA pointing at a dir containing corpora/wordnet).
Usage: NLTK_DATA=/path/to/nltk_data python tools/build_definitions.py words.json defs.json
"""
import json
import re
import sys

from nltk.corpus import wordnet as wn

POS_NAMES = {"n": "noun", "v": "verb", "a": "adjective", "s": "adjective", "r": "adverb"}
MAX_DEFS = 3


# WordNet has no entries for function words (prepositions, pronouns, conjunctions...).
MANUAL = {
    "against": [["preposition", "in opposition to; touching or leaning on"]],
    "albeit": [["conjunction", "even though; although"]],
    "although": [["conjunction", "in spite of the fact that"]],
    "among": [["preposition", "surrounded by; in the company of; shared between"]],
    "amongst": [["preposition", "among (chiefly British)"]],
    "anthropomorphization": [["noun", "the act of giving human traits or behavior to an animal, object or idea"]],
    "anybody": [["pronoun", "any person at all"]],
    "anyone": [["pronoun", "any person at all"]],
    "anything": [["pronoun", "a thing of any kind, no matter what"]],
    "because": [["conjunction", "for the reason that"]],
    "beside": [["preposition", "at the side of; next to"]],
    "cannot": [["verb", "can not; is unable to"]],
    "could": [["verb", "past tense of 'can'; used to show possibility or a polite request"]],
    "decidable": [["adjective", "able to be decided; (logic) having a procedure that always gives a yes-or-no answer"]],
    "disaggregate": [["verb", "to separate something into its component parts"]],
    "during": [["preposition", "throughout the course of; at some point in"]],
    "everybody": [["pronoun", "every person"]],
    "everyone": [["pronoun", "every person"]],
    "everything": [["pronoun", "all things; all that matters"]],
    "flagrancy": [["noun", "the quality of being shockingly obvious or blatant"]],
    "habeas": [["noun", "short for habeas corpus: a legal order to bring a detained person before a court"]],
    "herself": [["pronoun", "refers back to a female person already mentioned"]],
    "himself": [["pronoun", "refers back to a male person already mentioned"]],
    "hydrophile": [["noun", "a substance or molecule that is attracted to water"]],
    "hydrophobe": [["noun", "a substance or molecule that repels water"]],
    "incunabula": [["noun", "books printed in Europe before 1501; the earliest stages of something"]],
    "indisputably": [["adverb", "in a way that cannot be questioned or denied"]],
    "itself": [["pronoun", "refers back to a thing or animal already mentioned"]],
    "myself": [["pronoun", "refers back to the speaker"]],
    "nouveau": [["adjective", "newly arrived or fashionable (often in 'nouveau riche')"]],
    "omnivorously": [["adverb", "by eating both plants and animals; by taking in everything available"]],
    "oneself": [["pronoun", "refers back to a person in general"]],
    "orthogonally": [["adverb", "at right angles; in an independent or unrelated way"]],
    "others": [["pronoun", "other people or things"]],
    "ourselves": [["pronoun", "refers back to the speaker and others"]],
    "parallelly": [["adverb", "in a parallel way; side by side"]],
    "predominately": [["adverb", "mainly; for the most part"]],
    "should": [["verb", "used to say what is right, expected or advisable"]],
    "since": [["preposition", "from a past time until now"], ["conjunction", "because"]],
    "something": [["pronoun", "a thing that is not named or not known"]],
    "subcategories": [["noun", "smaller groups within a larger category"]],
    "subcategory": [["noun", "a smaller group within a larger category"]],
    "their": [["determiner", "belonging to them"]],
    "themselves": [["pronoun", "refers back to people or things already mentioned"]],
    "these": [["determiner", "plural of 'this'; the ones here"]],
    "those": [["determiner", "plural of 'that'; the ones there"]],
    "toward": [["preposition", "in the direction of"]],
    "towards": [["preposition", "in the direction of"]],
    "tracksuit": [["noun", "a loose, warm jacket and trousers worn for exercise"]],
    "undecidable": [["adjective", "not able to be decided; (logic) having no procedure that always gives a yes-or-no answer"]],
    "unless": [["conjunction", "except if"]],
    "unsurprisingly": [["adverb", "as might be expected"]],
    "until": [["preposition", "up to the time of"], ["conjunction", "up to the time that"]],
    "whenever": [["conjunction", "at any time that; every time that"]],
    "where": [["adverb", "in or to what place"]],
    "whereas": [["conjunction", "while on the other hand"]],
    "whereby": [["adverb", "by which; through which"]],
    "whether": [["conjunction", "used to introduce a choice between possibilities (whether or not)"]],
    "which": [["pronoun", "what one of a set; used to add information about a thing"]],
    "whoever": [["pronoun", "any person who"]],
    "without": [["preposition", "not having; in the absence of"]],
    "would": [["verb", "past tense of 'will'; used for imagined situations and polite requests"]],
    "yours": [["pronoun", "the one belonging to you"]],
}


def tidy(definition):
    definition = re.sub(r'"[^"]*"', "", definition)                        # embedded example quotes
    definition = re.sub(r"(?:;\s*|\s)-+\s*[A-Z][\w.' ]*(?=;|$)", "", definition)  # "; - Author" credits
    parts = [p.strip() for p in definition.split(";")]
    parts = [p for p in parts if p and '"' not in p]                          # empty bits, half-quoted examples
    return "; ".join(parts)


def sense_count(synset, word):
    """How often this sense is used in WordNet's tagged corpus (0 if unknown)."""
    base = {wn.morphy(word, synset.pos()) or word, word}
    return sum(l.count() for l in synset.lemmas() if l.name().lower() in base)


def definitions(word):
    """Most common senses first; first take the best sense of each part of speech, then fill up."""
    synsets = sorted(wn.synsets(word), key=lambda s: -sense_count(s, word))  # stable: ties keep WordNet order
    top = sense_count(synsets[0], word) if synsets else 0
    picked, seen_pos = [], set()
    for first_pass in (True, False):
        for s in synsets:
            pos = POS_NAMES[s.pos()]
            if len(picked) == MAX_DEFS:
                break
            # on the first pass, only add another part of speech if it's reasonably common
            if first_pass and (pos in seen_pos or (picked and sense_count(s, word) * 8 < top)):
                continue
            entry = [pos, tidy(s.definition())]
            if entry[1] and entry not in picked:
                picked.append(entry)
                seen_pos.add(pos)
    if not picked:
        return None, []
    base = wn.morphy(word) or word
    return (base if base != word else None), picked


def main():
    words_path, out = sys.argv[1], sys.argv[2]
    with open(words_path) as f:
        words = [e["w"] for e in json.load(f)]
    defs, missing = {}, []
    for w in words:
        base, d = (None, MANUAL[w]) if w in MANUAL else definitions(w)
        if d:
            defs[w] = {"d": d, **({"b": base} if base else {})}
        else:
            missing.append(w)
    with open(out, "w") as f:
        json.dump(defs, f, separators=(",", ":"), ensure_ascii=False)
    print(f"definitions for {len(defs)}/{len(words)} words; missing: {' '.join(missing)}")


if __name__ == "__main__":
    main()
