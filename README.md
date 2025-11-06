# SpongeBob Episode Title Generator 

Generate silly, SpongeBob-style episode titles from the
[Kaggle episodes dataset](https://www.kaggle.com/datasets/myticalcat/spongebob-squarepants-episodes-dataset).

**What it does**
1. **Clean** the Kaggle CSV/JSON into one deduped list of real episode titles.
2. **Generate** new titles using a tiny 3-gram Markov model + “writer’s room” templates.
3. **Avoid** copying real titles with a simple similarity check.

---

## Project structure

.

├─ data/

│ ├─ spongebob_episodes.csv # put from Kaggle

│ ├─ spongebob_episodes.json # put from Kaggle

│ ├─ episode_titles_cleaned.csv # created by step 01

│ └─ generated_titles.csv # created by step 02

├─ src/

│ ├─ 01_spongebob_episodes.py # cleaner → builds episode_titles_cleaned.csv

│ └─ 02_title_gen.py # generator → makes new titles

├─ requirements.txt

├─ .gitignore

├─ LICENSE

└─ README.md


---

## Quickstart

### 0) Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

```

1) Generate new titles
```bash
python3 src/02_title_gen.py \
  --in_csv data/episode_titles_cleaned.csv \
  --num 20 \
  --seed "Squidward" \
  --temp 1.0 \
  --use_templates 0.45 \
  --no_vs \
  --max_the 1 \
  --max_phrase_repeat 1 \
  --max_word_repeat 1 \
  --out data/generated_titles.csv
```
You’ll see titles printed and saved to data/generated_titles.csv.

CLI options (most-used)

| Flag                  | What it does                                  | Example                 |
| --------------------- | --------------------------------------------- | ----------------------- |
| `--num`               | How many titles to generate                   | `--num 30`              |
| `--seed`              | Bias start word(s)                            | `--seed "Squidward"`    |
| `--temp`              | Creativity (lower = safer, higher = wilder)   | `--temp 0.8`            |
| `--use_templates`     | Fraction (0–1) using joke templates vs Markov | `--use_templates 0.6`   |
| `--no_vs`             | Avoid “vs.” pattern                           | `--no_vs`               |
| `--max_the`           | Limit “the” per title                         | `--max_the 1`           |
| `--max_phrase_repeat` | Cap “Operation/License/Makeover” per batch    | `--max_phrase_repeat 1` |
| `--max_word_repeat`   | Cap template nouns/events per batch           | `--max_word_repeat 1`   |

Run --help on either script to see all flags.


Example output

Patrick Trains Suds
Underpants Chronicles
License to Budget
Gary in Rock Bottom
The Krusty Krab Problems


**How it works**
Step 1 cleans the dataset into a simple list of episode titles.
Step 2 learns short word patterns from those titles (a tiny “next-word” model) and mixes them with a few hand-made templates like “License to ___”. A quick overlap check keeps results from being too similar to any real title.

**Troubleshooting
**
FileNotFoundError: make sure the Kaggle files are in data/ and you passed the correct --csv/--json paths.

UnicodeDecodeError: try pip install chardet and re-save the CSV as UTF-8, or open in Excel/Numbers and export.

No titles generated: lower the strictness by reducing the novelty check (use defaults) or increase --temp slightly.

Repetitive outputs: reduce --use_templates, or set --max_phrase_repeat 0 and --max_word_repeat 0.


