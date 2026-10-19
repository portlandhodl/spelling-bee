# spelling-bee

A bee-themed spelling trainer: a bee flies a word across the screen, a second bee wipes it away after a short pause (0.5 s by default, adjustable), and you type it from memory.

Play: https://portlandhodl.github.io/spelling-bee/

- 5,000 hard, hand-curated words across three tiers (everyday traps, advanced vocabulary, spelling-bee level), each with common misspellings and a reason it's tricky (`words.json`)
- Correct answers show common definitions (`defs.json`, from WordNet, with curated fallbacks)
- Score, streaks, history and missed words are kept in `sessionStorage`; missed words come back a few rounds later

## Rebuilding the word list

The curated source lists live in `tools/curated/*.json` (`w` word, `t` tier, `m` misspellings, `r` reason, `d` definition). To rebuild `words.json` and `defs.json` (needs `nltk` and the WordNet corpus):

    NLTK_DATA=/path/to/nltk_data python3 tools/build_curated.py 5000

If there are more curated words than the target, the shortest tier-1 words are trimmed first; well-known classics are always kept.
