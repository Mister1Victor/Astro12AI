import os
import pickle

CACHE_FILE = "cache/knowledge.pkl"


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None

    with open(CACHE_FILE, "rb") as f:
        return pickle.load(f)


def save_cache(split_docs):
    os.makedirs("cache", exist_ok=True)

    with open(CACHE_FILE, "wb") as f:
        pickle.dump(split_docs, f)