# Word Ladder

A `nanoagent.plugin/v0001` plugin, built with the structure of NanoAgent's reference plugin,
[arxiv-source](https://github.com/zeyuyang8/arxiv-source).

An agent gets a start word and an end word, both 4 letters. It must give the
shortest ladder from one to the other, changing one letter per step with every
word in the dictionary, or report that no ladder exists. Its only tool looks
words up. A deterministic verifier, plain Python with no model, checks the
answer.

## Tools

| Tool | Does | Code |
|---|---|---|
| `is_word` | Tells whether a word is in the puzzle dictionary (the 4-letter words of ENABLE) | `src/plugin/is_word.py` |
| `pin_puzzle` | Pins a frozen puzzle's answer key: whether it is solvable, and the length of a shortest ladder | `src/plugin/puzzles.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `solve-ladder` | Finds a shortest ladder from `start` to `end`, or reports that none exists | `agent`, with `is_word`; reference `pin_puzzle` |

Input: `{"start": str, "end": str}`. Output: `{"solvable": bool, "ladder": list[str]}`,
with `ladder` empty when `solvable` is false.

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
starts, so the agent never sees its output. It accepts only the 20 frozen
puzzles below and refuses any other pair. The agent gets only `is_word`. It has
no neighbors or solver tool.

### Puzzles

`src/plugin/data/puzzles.json` holds 20 puzzles. 17 have a ladder: one each of
2 and 3 words, then three each of 4, 5, 6, 7 and 8 words. 3 have no ladder.
`optimal_length` counts the words in a shortest ladder, both ends included.

| start | end | optimal_length |
|---|---|---|
| jaws | yaws | 2 |
| vamp | lame | 3 |
| mole | tory | 4 |
| sods | qoph | 4 |
| duke | wake | 4 |
| gley | bras | 5 |
| door | dubs | 5 |
| carp | guls | 5 |
| fins | obes | 6 |
| clam | kefs | 6 |
| aper | revs | 6 |
| baby | huff | 7 |
| blaw | dugs | 7 |
| bads | nevi | 7 |
| wand | trow | 8 |
| acre | gips | 8 |
| ruth | club | 8 |
| kilt | djin | no ladder (`djin` has no neighbors) |
| huic | tale | no ladder (`huic` has no neighbors) |
| umbo | hewn | no ladder (`umbo` is in a 3-word component) |

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
compare `pin_puzzle`'s answer key with a fresh BFS.

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
│   ├── puzzles.py           # the frozen puzzles and the pin_puzzle tool
│   ├── generate_puzzles.py  # writes data/puzzles.json and verifier/words.py, once
│   └── data/
│       ├── enable1.txt      # the ENABLE word list, vendored unchanged
│       └── puzzles.json     # the 20 frozen puzzles
├── tests/           # test_verifier.py (the verifier's cases) and test_plugin.py (tools, data, generator)
├── ui/              # how the page draws the outputs: drawn from their JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package; words.py is generated
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

To regenerate the frozen files, run the following. It uses a fixed seed and
gives the same files byte for byte, which a test checks:

```bash
uv run python -m plugin.generate_puzzles
```

To use the plugin, publish it on RUSH Lab, open it, and ask its chat for one of
the puzzles, for example "Find a word ladder from duke to wake". The result card
shows the verifier's verdict.

Publishing checks every plugin rule: push the plugin to a public GitHub
repository and run `rush publish <server> <github-url>`.
