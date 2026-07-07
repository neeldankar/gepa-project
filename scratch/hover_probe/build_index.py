"""Part 1: download the DSPy wiki-abstracts corpus + build the bm25s index. $0, local.

Lifts the dspy multihop tutorial verbatim. Saves the index to ./bm25s_index/ for Part 3 reuse.
"""
import os, time, tarfile, urllib.request
import orjson, bm25s, Stemmer

URL = "https://huggingface.co/dspy/cache/resolve/main/wiki.abstracts.2017.tar.gz"
TGZ = "wiki.abstracts.2017.tar.gz"
JSONL = "wiki.abstracts.2017.jsonl"
INDEX_DIR = "bm25s_index"

t0 = time.time()
if not os.path.exists(JSONL):
    if not os.path.exists(TGZ):
        print("downloading corpus (~500MB)...", flush=True)
        urllib.request.urlretrieve(URL, TGZ)
    print(f"downloaded {os.path.getsize(TGZ)/1e6:.0f} MB in {time.time()-t0:.0f}s; extracting...", flush=True)
    with tarfile.open(TGZ) as t:
        t.extractall(".")
print(f"corpus jsonl size: {os.path.getsize(JSONL)/1e9:.2f} GB", flush=True)

t1 = time.time()
corpus = []
with open(JSONL) as f:
    for line in f:
        d = orjson.loads(line)
        corpus.append(f"{d['title']} | {' '.join(d['text'])}")
print(f"loaded {len(corpus)} docs in {time.time()-t1:.0f}s", flush=True)

t2 = time.time()
stemmer = Stemmer.Stemmer("english")
corpus_tokens = bm25s.tokenize(corpus, stopwords="en", stemmer=stemmer, show_progress=True)
retriever = bm25s.BM25(k1=0.9, b=0.4)
retriever.index(corpus_tokens)
print(f"indexed in {time.time()-t2:.0f}s", flush=True)

retriever.save(INDEX_DIR, corpus=corpus)
sz = sum(os.path.getsize(os.path.join(INDEX_DIR, f)) for f in os.listdir(INDEX_DIR)) / 1e9
print(f"saved index to {INDEX_DIR}/ ({sz:.2f} GB); total {time.time()-t0:.0f}s", flush=True)
print("BUILD_DONE", flush=True)
