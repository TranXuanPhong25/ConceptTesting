"""Unchanged vr13 tokenization and SQLite FTS5 BM25 helper."""
import re
import sqlite3

def tokens(text):
    # Public source names split at snake/camel boundaries; no generated bug summaries.
    text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)
    return re.findall(r"[^\W_]+", text.lower(), re.UNICODE)


class Lexical:
    """SQLite FTS5 BM25 over every supplied document, without structural eligibility."""
    def __init__(self, documents):
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE VIRTUAL TABLE docs USING fts5(id UNINDEXED,body)")
        self.db.executemany("INSERT INTO docs VALUES (?,?)", [(k, " ".join(tokens(v))) for k, v in documents.items()])

    def ranking(self, query):
        terms = list(dict.fromkeys(tokens(query)))[:128]
        if not terms:
            return []
        match = " OR ".join('"' + t + '"' for t in terms)
        return [(k, -float(s)) for k, s in self.db.execute(
            "SELECT id,bm25(docs) AS score FROM docs WHERE docs MATCH ? ORDER BY score,id", (match,))]

    def close(self):
        self.db.close()

