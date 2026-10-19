# spelling-bee

A bee-themed spelling trainer: a bee flies a word across the screen, a second bee wipes it away after a short pause (0.5 s by default, adjustable), and you type it from memory.

Play: https://portlandhodl.github.io/spelling-bee/

- 5,000 commonly misspelled words, each with real misspellings and a reason it's tricky (`words.json`)
- Score, streaks, history and missed words are kept in `sessionStorage`; missed words come back a few rounds later

## Rebuilding the word list

`tools/build_words.py` merges Wikipedia's *Lists of common misspellings* (CC BY-SA), the Birkbeck spelling error corpus, and a word-frequency list for ranking. Download the sources into a data directory (see the script docstring), then:

    python3 -I tools/build_words.py /path/to/data words.json
