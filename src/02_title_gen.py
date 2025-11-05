#!/usr/bin/env python3
import pandas as pd
import re, random, math, argparse
from collections import defaultdict, Counter
from pathlib import Path

# Utils: tokenize / casing
SMALL_WORDS = {"and","or","the","of","in","to","a","an","for","on","at","by","with"}

def tokenize(t: str):
    t = re.sub(r"[“”’‘]", "'", t or "")
    t = re.sub(r"[^A-Za-z0-9:&?!'\"()\-\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t.split()

def detokenize(tokens):
    s = " ".join(tokens)
    s = re.sub(r"\s+([:;,.!?])", r"\1", s)
    s = re.sub(r'\s+"', ' "', s)
    s = re.sub(r'"\s+', '" ', s)
    s = re.sub(r"\s+—\s+", " — ", s)
    s = re.sub(r"\s+-\s+", " - ", s)
    return s.strip()

def titlecase_segment(seg: str) -> str:
    words = seg.split()
    out = []
    for i,w in enumerate(words):
        lw = w.lower()
        if i==0 or i==len(words)-1 or lw not in SMALL_WORDS:
            out.append(w[:1].upper()+w[1:])
        else:
            out.append(lw)
    return " ".join(out)

def smart_titlecase(s: str) -> str:
    parts = re.split(r"(:|—)", s)
    for i in range(0, len(parts), 2):
        parts[i] = titlecase_segment(parts[i])
    return "".join(parts)

def limit_the(title: str, max_the: int):
    words = title.split()
    count = 0
    out = []
    for w in words:
        if w.lower() == "the":
            count += 1
            if count > max_the:
                continue
        out.append(w)
    return " ".join(out)

def postprocess(title: str, max_the: int):
    if not title: return ""
    title = re.sub(r"\b(\d)\s+(\d)\b", r"\1\2", title)
    title = re.sub(r"\s+", " ", title).strip()
    title = limit_the(title, max_the=max_the)
    title = smart_titlecase(title)
    title = re.sub(r"\s+[A-Za-z]$", "", title)
    return title.strip()

# Novelty filter (vs real titles)

def tokens_for_similarity(s: str):
    s = re.sub(r"[^a-z0-9\s]", " ", s.lower())
    s = re.sub(r"\s+", " ", s).strip()
    words = s.split()
    bigrams = list(zip(words, words[1:]))
    return set(words), set(bigrams)

def jaccard(a: set, b: set) -> float:
    if not a and not b: return 0.0
    return len(a & b) / max(len(a | b), 1)

def too_similar(candidate: str, corpus_lower, uni_sets, bi_sets,
                max_uni=0.55, max_bi=0.40) -> bool:
    cu, cb = tokens_for_similarity(candidate)
    if candidate.lower() in corpus_lower: return True
    for U,B in zip(uni_sets, bi_sets):
        if jaccard(cu, U) > max_uni: return True
        if jaccard(cb, B) > max_bi: return True
    return False

# Markov 3-gram model

class NGramModel:
    def __init__(self, n=3):
        self.n = n
        self.counts = defaultdict(Counter)
        self.starts = Counter()

    def fit(self, titles):
        for t in titles:
            toks = ["<s>"]*(self.n-1) + tokenize(t) + ["</s>"]
            if len(toks) < self.n: continue
            self.starts[tuple(toks[:self.n-1])] += 1
            for i in range(self.n-1, len(toks)):
                ctx = tuple(toks[i-self.n+1:i])
                self.counts[ctx][toks[i]] += 1

    def sample_next(self, ctx, temperature=0.9):
        freq = self.counts.get(tuple(ctx))
        if not freq: return "</s>"
        words, counts = zip(*freq.items())
        logits = [math.log(c+1e-9)/max(temperature,1e-6) for c in counts]
        m = max(logits)
        probs = [math.exp(l-m) for l in logits]
        probs = [p/sum(probs) for p in probs]
        r = random.random(); acc = 0.0
        for w,p in zip(words, probs):
            acc += p
            if r <= acc: return w
        return words[-1]

    def generate(self, seed=None, max_len=9, temperature=0.9, ensure_spongebob=False, max_the=1):
        if seed:
            seed_t = tokenize(seed)
            ctx = ["<s>"]*(self.n-1-len(seed_t)) + seed_t[-(self.n-1):]
        else:
            if not self.starts: return ""
            ctx = list(random.choice(list(self.starts.keys())))
        out = []
        for _ in range(max_len+10):
            nxt = self.sample_next(ctx, temperature)
            if nxt == "</s>": break
            out.append(nxt); ctx = ctx[1:] + [nxt]
        text = detokenize(out)
        if ensure_spongebob and "spongebob" not in text.lower():
            text = ("SpongeBob " + text).strip()
        return postprocess(text, max_the=max_the)

# Humor/pun templates with batch-aware diversity

CHARS     = ["SpongeBob","Patrick","Squidward","Mr. Krabs","Plankton","Sandy","Gary"]
PLACES    = ["Bikini Bottom","Rock Bottom","The Krusty Krab","The Chum Bucket","Goo Lagoon","Boating School"]
NOUNS     = ["Barnacle","Bubble","Bucket","Clarinet","Coupon","Jellyfish","Kelp","Patty","Pineapple","Plankton","Suds","Underpants","Tartar","Lagoon","Mustard"]
VERBS_BASE= ["Bake","Fry","Prank","Apologize","Hide","Pay","Pose","Quit","Resign","Recycle","Budget","Invest","Compost","Skate","Cook","Train"]
VERBS_3S  = ["Bakes","Fries","Pranks","Apologizes","Hides","Pays","Poses","Quits","Resigns","Recycles","Budgets","Invests","Composts","Skates","Cooks","Trains"]
EVENTS    = ["Crisis","Capers","Chronicles","Debacle","Dilemma","Day","Night","Makeover","Mystery","Mission","Meltdown","Mix-Up","Misadventure","Audit","Heist"]
ADJ       = ["Suspicious","Wiggly","Nautical","Crunchy","Heroic","Dubious"]
ADJ_PROB  = 0.25  # keeping the adjectives modest

# Phrase keys to limit within a batch
PHRASE_KEYS = {
    "MAKEOVER": lambda t: "makeover" in t.lower(),
    "OPERATION": lambda t: t.lower().startswith("operation "),
    "LICENSE": lambda t: t.lower().startswith("license to "),
}

def maybe_adj() -> str:
    return (random.choice(ADJ) + " ") if random.random() < ADJ_PROB else ""

def sample_unique(pool, used_counter: Counter, max_repeat: int):
    # Trying to pick something not exceeding max_repeat in this batch
    random.shuffle(pool)
    candidates = [w for w in pool if used_counter[w] < max_repeat]
    if candidates:
        choice = random.choice(candidates)
    else:
        # Fallback: pick the least used to avoid infinite loops
        least = min(pool, key=lambda w: used_counter[w])
        choice = least
    used_counter[choice] += 1
    return choice

def humor_template(used_words: Counter, used_phrases: Counter, no_vs=True, max_the=1, max_word_repeat=1, max_phrase_repeat=1):
    c = random.choice(CHARS)
    p = random.choice(PLACES)
    n = sample_unique(NOUNS, used_words, max_word_repeat)
    v = random.choice(VERBS_BASE)
    v3= random.choice(VERBS_3S)
    e = sample_unique(EVENTS, used_words, max_word_repeat)

    # Candidate patterns (none with "vs" unless allowed)
    patterns = [
        (f"{c}'s {n} {e}", "GEN"),                 
        (f"{c} Learns to {v}", "LEARN"),
        (f"{p} Problems", "PROBLEMS"),
        (f"Operation {n}", "OPERATION"),
        (f"License to {v}", "LICENSE"),
        (f"{c} and {n} {e}", "AND"),
        (f"{c} {v3} {n}", "DOES"),
        (f"{maybe_adj()}{n} {e}", "ADJ"),
        (f"{c} in {p}", "IN"),
        (f"{n} Makeover", "MAKEOVER"),
    ]
    if not no_vs:
        patterns.append((f"{c} vs {n} {e}", "VS"))

    # shuffle and pick the first whose phrase key isn't over the cap
    random.shuffle(patterns)
    for text, key in patterns:
        # map to phrase limit keys when applicable
        phrase_key = None
        if key in ("OPERATION","LICENSE","MAKEOVER"):
            phrase_key = key
        # phrase usage check
        if phrase_key and used_phrases[phrase_key] >= max_phrase_repeat:
            continue
        out = postprocess(text, max_the=max_the)
        # final phrase gate (string-level, e.g., "Operation " also caught)
        blocked = False
        for ph_key, fn in PHRASE_KEYS.items():
            if fn(out) and used_phrases[ph_key] >= max_phrase_repeat:
                blocked = True
                break
        if blocked:
            continue
        # accept
        if phrase_key:
            used_phrases[phrase_key] += 1
        # also bump generic detections (help both routes)
        for ph_key, fn in PHRASE_KEYS.items():
            if fn(out):
                used_phrases[ph_key] += 1
        return out

    # if all blocked, produce a very plain fallback
    fallback = f"{c} and {n} {e}"
    return postprocess(fallback, max_the=max_the)


# Main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in_csv", default="/Users/ismailperacha/Downloads/clean_titles.csv",
                    help="Path to clean_titles.csv from 01 script")
    ap.add_argument("--num", type=int, default=20)
    ap.add_argument("--seed", default="")
    ap.add_argument("--temp", type=float, default=0.9)
    ap.add_argument("--max_len", type=int, default=9)
    ap.add_argument("--force_spongebob", action="store_true")
    ap.add_argument("--out", default="/Users/ismailperacha/Downloads/generated_titles.csv")
    # Style controls
    ap.add_argument("--use_templates", type=float, default=0.40, help="Chance to use humor template [0-1]")
    ap.add_argument("--no_vs", action="store_true", help="Avoid 'vs' in templates")
    ap.add_argument("--max_the", type=int, default=1, help="Max 'the' allowed in a title")
    ap.add_argument("--max_phrase_repeat", type=int, default=1, help="Max repeats of phrase patterns (Makeover/Operation/License) per batch")
    ap.add_argument("--max_word_repeat", type=int, default=1, help="Max repeats of template nouns/events per batch (e.g., no 'Suds' x2)")
    args = ap.parse_args()

    in_path = Path(args.in_csv)
    if not in_path.exists():
        raise SystemExit(f"Input not found: {in_path}. Run 01_clean_titles.py first.")

    df = pd.read_csv(in_path)
    if "title" not in df.columns or df.empty:
        raise SystemExit("No titles in clean_titles.csv. Re-run cleaner with correct inputs.")

    titles = df["title"].dropna().astype(str).tolist()
    print(f"Loaded {len(titles)} titles.")

    corpus_lower = [t.lower() for t in titles]
    uni_sets, bi_sets = zip(*[tokens_for_similarity(t) for t in titles])

    model = NGramModel(n=3)
    model.fit(titles)

    generated, seen, tries = [], set(corpus_lower), 0
    template_prob = max(0.0, min(1.0, args.use_templates))

    # batch-level diversity trackers
    used_words = Counter()    # counts picks from NOUNS/EVENTS
    used_phrases = Counter()  # counts phrase keys like MAKEOVER/OPERATION/LICENSE

    while len(generated) < args.num and tries < args.num * 150:
        tries += 1
        if random.random() < template_prob:
            g = humor_template(
                used_words=used_words,
                used_phrases=used_phrases,
                no_vs=args.no_vs,
                max_the=args.max_the,
                max_word_repeat=args.max_word_repeat,
                max_phrase_repeat=args.max_phrase_repeat
            )
        else:
            g = model.generate(seed=(args.seed or None),
                               max_len=args.max_len,
                               temperature=args.temp,
                               ensure_spongebob=args.force_spongebob,
                               max_the=args.max_the)
        if not g:
            continue
        if g.lower() in seen:
            continue
        if too_similar(g, corpus_lower, uni_sets, bi_sets):
            continue
        generated.append(g); seen.add(g.lower())

    print("\n--- Generated SpongeBob Episode Titles ---")
    for i,t in enumerate(generated, 1):
        print(f"{i:02d}. {t}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"generated_title": generated}).to_csv(args.out, index=False)
    print(f"\nSaved {len(generated)} titles -> {args.out}")

if __name__ == "__main__":
    main()
