# Word Ladder

A `nanoagent.plugin/v0001` plugin, built with the structure of NanoAgent's reference plugin,
[arxiv-source](https://github.com/zeyuyang8/arxiv-source).

An agent gets a start word and an end word, both 4 letters. It must give the
shortest ladder from one to the other, changing one letter per step with every
word in the dictionary, or report that no ladder exists. A `neighbors` tool gives
each word's one-letter neighbors, but the agent plans the search itself: there is
no path or distance tool. A deterministic verifier, plain Python with no model,
checks the answer.

## Tools

| Tool | Does | Code |
|---|---|---|
| `neighbors` | For each of 1 to 25 dictionary words, gives every dictionary word one letter different from it, alphabetical | `src/plugin/neighbors.py` |
| `is_word` | Tells whether a word is in the puzzle dictionary (the 4-letter words of ENABLE) | `src/plugin/is_word.py` |
| `pin_puzzle` | Pins a frozen puzzle's answer key: whether it is solvable, and the length of a shortest ladder | `src/plugin/puzzles.py` |

`neighbors` takes `{"words": list[str]}` and returns
`{"results": [{"word": str, "neighbors": list[str]}, ...]}`, one entry per asked
word in the order asked. It refuses an empty call, a call of more than 25 words
(`MAX_NEIGHBOR_WORDS` in `contract.py`), and any word that is not 4 lowercase
letters or not in the dictionary, naming the bad word. Both the tool and the
verifier's input check (`verifier/neighbors.py`) refuse these, and the verifier
checks every answer against a brute-force scan of the dictionary.

### Tasks

| Task | Does | Runner |
|---|---|---|
| `solve-ladder` | Finds a shortest ladder from `start` to `end`, or reports that none exists | `agent`, with `is_word` and `neighbors`; reference `pin_puzzle` |

Input: `{"start": str, "end": str}`, shown to the agent in its first message.
Output: `{"solvable": bool, "ladder": list[str]}`, with `ladder` empty when
`solvable` is false.

The rules the agent is given:

- All words are lowercase ASCII letters.
- Each consecutive pair of words differs in exactly one position.
- No letters are added, removed, or rearranged.
- Every word, including start and end, must be in the dictionary.
- No word may repeat.
- The ladder includes both the start word and the end word.
- The ladder must be as short as possible.
- If no ladder exists, say so instead of giving one.

`pin_puzzle` is the task's reference tool. NanoAgent runs it before the agent
starts, so the agent never sees its output. It accepts only the 15 frozen
puzzles below and refuses any other pair.

### Search procedure

The instructions tell the agent not to search in its head, and give it a
two-sided breadth-first search to run with `neighbors`:

1. Call `neighbors` on `[start, end]`.
2. Each later call expands every *newest* word of both sides: the neighbors the
   side's last call found that the side had not seen before.
3. Stop when a word is on both sides. A word expanded on one side that shows up
   in the other side's new neighbors gives a ladder one word shorter than a word
   new on both sides, so the agent prefers it. It traces each half back through
   the word whose list named it.
4. If a side has no new words, its whole connected component has been seen
   without meeting the other side, so the puzzle is unsolvable.

Expanding every newest word, not a few, is what makes this breadth-first: after
call *k* each side knows every word within *k* steps of its end, so the first
meeting gives a shortest ladder. `two_sided_search` in
`src/plugin/generate_puzzles.py` is this procedure exactly. The generator and the
tests use it to check each live puzzle, and the gold scripted cases follow its
calls.

### Fitting the hosted limits

RUSH Lab runs plugin agents with `max_tokens` 2048 per response (hidden reasoning
included), `max_steps` 6, `token_limit` 65,536 and `cost_limit` $0.10, and a
plugin cannot change them. Before this design, the agent had only `is_word`,
searched in its head, spent its whole 2048-token response and never submitted.
Now:

- **Short responses.** The tool does the lookups, so each step's reasoning is
  only "which words are new, did the sides meet": a few hundred tokens.
- **Steps.** NanoAgent makes step 6 a forced final answer, so the tool calls fit
  in steps 1 to 5: at most 4 `neighbors` calls plus `submit`. Every live puzzle
  needs 1 to 3 calls, and every unsolvable one runs out within 2.
- **Words per call.** No call in a live puzzle's search needs more than 25 words,
  so the agent never has to split a frontier over two steps.
- **Tokens.** NanoAgent re-sends the whole transcript every step, so a tool
  result costs its size again on every later request. The generator estimates
  that re-sent total at 3 characters of JSON per token and keeps it under 20,000
  tokens per puzzle, well inside `token_limit`. The largest is about 3,000.

The generator samples puzzles with a fixed seed and keeps only the ones whose
search meets these limits. Longer or harder puzzles, such as `cold -> warm`,
`sods -> rows` and `kilt -> djin`, appear only as verifier test data.

### Puzzles

`src/plugin/data/puzzles.json` holds 15 puzzles: 12 with a ladder (three each of
3, 4, 5 and 6 words) and 3 without. `optimal_length` counts the words in a
shortest ladder, both ends included. The other columns are the simulated search:
its `neighbors` calls, the words in each call, the words in all results, and the
estimated re-sent tokens.

| start | end | optimal_length | calls | words per call | output words | est. tokens (re-sent) |
|---|---|---|---|---|---|---|
| jaws | vars | 3 | 1 | 2 | 40 | 256 |
| vamp | lame | 3 | 1 | 2 | 32 | 214 |
| mole | sone | 3 | 1 | 2 | 49 | 304 |
| sods | qoph | 4 | 2 | 2, 23 | 467 | 3,014 |
| gley | blet | 4 | 2 | 2, 12 | 134 | 1,027 |
| door | tout | 4 | 2 | 2, 19 | 246 | 1,757 |
| carp | guls | 5 | 2 | 2, 24 | 414 | 2,751 |
| clam | heat | 5 | 2 | 2, 25 | 401 | 2,699 |
| aper | knew | 5 | 2 | 2, 8 | 67 | 590 |
| isle | ells | 6 | 3 | 2, 7, 24 | 325 | 2,591 |
| emir | abos | 6 | 3 | 2, 7, 20 | 191 | 1,790 |
| eddy | ends | 6 | 3 | 2, 5, 15 | 157 | 1,425 |
| lies | jeux | no ladder (`jeux` has no neighbors) | 1 | 2 | 21 | 156 |
| epee | durn | no ladder (`epee` has no neighbors) | 1 | 2 | 10 | 98 |
| idyl | moly | no ladder (`idyl` is in a 3-word component) | 2 | 2, 13 | 206 | 1,427 |

### Verifier

`verify_task` (`verifier/ladder.py`) checks the following, in order, and stops at
the first failure with a reason:

1. NanoAgent has already built the output into `LadderOutput`. A missing field,
   a wrong type, `null` or an extra key fails the task there, before the
   verifier runs.
2. Unsolvable puzzle: it passes only if `solvable` is false and `ladder` is empty.
3. Solvable puzzle: it fails if `solvable` is false or `ladder` is empty.
4. The ladder starts with `start` and ends with `end`.
5. Every word is lowercase ASCII, has 4 letters and is in the dictionary.
6. Each consecutive pair differs in exactly one position.
7. No word repeats.
8. The ladder has exactly `optimal_length` words. A valid but longer ladder
   fails as "not shortest".

It accepts any ladder that meets these rules and never compares the answer to a
stored ladder. It reads the dictionary from `verifier/words.py`, generated from
the vendored list, because the sandboxed verifier may only import Python. The
tool checks also re-check each `is_word` answer against that dictionary, and
compare `pin_puzzle`'s answer key with a fresh BFS and each `neighbors` answer
with a brute-force scan. The task's verdict never depends on which tools the
agent called.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server: __main__.py, its IMPLEMENTATIONS, and the plugin's own modules
│   ├── dictionary.py        # the 4-letter ENABLE words and the ladder graph (BFS)
│   ├── is_word.py           # the is_word tool
│   ├── neighbors.py         # the neighbors tool
│   ├── puzzles.py           # the frozen puzzles and the pin_puzzle tool
│   ├── generate_puzzles.py  # the prescribed search; writes data/puzzles.json, verifier/words.py, tests/cases/
│   └── data/
│       ├── enable1.txt      # the ENABLE word list, vendored unchanged
│       └── puzzles.json     # the 15 frozen puzzles
├── tests/           # test_verifier.py (the verifier's cases), test_plugin.py (tools, data, generator, budget)
│   ├── cases/       # scripted runs: neighbors calls then a submit, and the verdict each must get
│   ├── replay.py    # plays a case through the real tools and verifier, with no model
│   └── test_cases.py
├── ui/              # how the page draws the outputs: drawn from their JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package (neighbors.py checks the tool); words.py is generated
```

### Dictionary: source and license

`src/plugin/data/enable1.txt` is the ENABLE (Enhanced North American Benchmark
LExicon) word list, 172,823 lowercase words, copied unchanged from
<https://github.com/dolph/dictionary/blob/master/enable1.txt>. Its sha256 is
`3f16130220645692ed49c7134e24a18504c2ca55b3c012f7290e3e77c63b1a89`, and
`tests/test_plugin.py` checks it. ENABLE is in the public domain. The puzzles
use its 3,903 four-letter words.

## Develop and run

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then, from
this folder:

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

`uv.lock` pins every dependency, and the plugin runs with `uv run --frozen`. The
plugin and verifier need no network and no environment variables.

To regenerate the frozen files (puzzles, the verifier's word list and the
scripted cases), run the following. It uses a fixed seed and gives the same
files byte for byte, which a test checks, and prints the puzzle table above:

```bash
uv run python -m plugin.generate_puzzles
```

To use the plugin, publish it on RUSH Lab, open it, and ask its chat for one of
the puzzles, for example "Find a word ladder from isle to ells". The result card
shows the verifier's verdict.

Publishing checks every plugin rule: push the plugin to a public GitHub
repository and run `rush publish <server> <github-url>`.
