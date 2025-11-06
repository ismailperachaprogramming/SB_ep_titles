#!/usr/bin/env python3
import pandas as pd, re, argparse
from pathlib import Path

CANDIDATE_TITLE_COLS = [
    "title", "Title", "episode_title", "name",
    "title_csv", "Episode Title", "EPISODE_TITLE"
]

def pick_title_col(df):
    for c in CANDIDATE_TITLE_COLS:
        if c in df.columns:
            return c
    # Trying fuzzy pick: any col named like 'title'
    for c in df.columns:
        if re.search(r"title", c, re.I):
            return c
    return None

def clean_title(t: str) -> str:
    if pd.isna(t): return ""
    t = str(t).strip()
    t = re.sub(r"\s+", " ", t)
    return t

def load_titles_from_csv(path: str):
    p = Path(path)
    if not p.exists(): return []
    df = pd.read_csv(p)
    col = pick_title_col(df)
    if not col: return []
    return [clean_title(x) for x in df[col].dropna().tolist()]

def load_titles_from_json(path: str):
    p = Path(path)
    if not p.exists(): return []
    try:
        df = pd.read_json(p, lines=False)
    except ValueError:
        # try jsonl
        df = pd.read_json(p, lines=True)
    col = pick_title_col(df)
    if not col: return []
    return [clean_title(x) for x in df[col].dropna().tolist()]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="/Users/ismailperacha/Downloads/spongebob_episodes.csv")
    ap.add_argument("--json", required=True, help="/Users/ismailperacha/Desktop/spongebob_episodes.json")
    ap.add_argument("--out", default="/Users/ismailperacha/Downloads/episode_titles_cleaned.csv")
    args = ap.parse_args()

    csv_titles  = load_titles_from_csv(args.csv)
    json_titles = load_titles_from_json(args.json)

    titles = [t for t in set(csv_titles + json_titles) if t]
    titles = sorted(titles)

    if not titles:
        print("No titles found. Check --csv/--json paths and that a title column exists.")
        return

    out_df = pd.DataFrame({"title": titles})
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False)
    print(f"Saved {len(titles)} titles -> {args.out}")

if __name__ == "__main__":
    main()
