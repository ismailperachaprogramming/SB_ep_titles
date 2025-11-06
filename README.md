# SpongeBob Episode Title Generator

Fun data project using the
[SpongeBob SquarePants Episodes](https://www.kaggle.com/datasets/myticalcat/spongebob-squarepants-episodes-dataset)
dataset. What was done?

1. **Cleaned** the CSV/JSON to get a single list of real episode titles.
2. **Generated** new SpongeBob-style titles using a tiny Markov model +
   some “writer’s room” templates.
3. **Prevented copies** of real titles with a simple similarity filter.

---

## Quickstart

### 0) Setup

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

1) Clean the titles
python3 src/01_spongebob_episodes.py \
  --csv  data/spongebob_episodes.csv \
  --json data/spongebob_episodes.json \
  --out  data/episode_titles_cleaned.csv

2) Generate new episode titles
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

