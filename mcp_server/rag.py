"""Tiny RAG layer over the asset-doc corpus (D3: retrieval design choices).

Deliberately LEXICAL (hand-rolled BM25), not embeddings — the decision, and
when it flips, is the exam point (ADR 14):
- Corpus is 6 documents / ~40 chunks of domain-specific UK housing vocabulary.
  Queries share that vocabulary ("damp survey", "roof", "Awaab timescales"),
  so lexical retrieval is accurate, transparent (scores are explainable),
  dependency-free and costs nothing.
- Switch to embeddings (Voyage + a vector store) when any of: paraphrase-heavy
  queries from residents, corpus beyond a few hundred chunks, multilingual
  content, or cross-document semantic joins.

Chunking (ADR 13): markdown-heading sections, then paragraphs merged up to
~180 words per chunk. Section-aware chunks keep provenance (doc + heading)
attached to every hit — the citation story matters more than raw recall at
this corpus size. No overlap: heading boundaries are semantic boundaries in
survey-style documents.
"""
import math
import re
from dataclasses import dataclass
from pathlib import Path

DOCS_DIR = Path(__file__).resolve().parent / "data" / "asset_docs"
TARGET_WORDS = 180
_WORD = re.compile(r"[a-z0-9']+")


def _tokenise(text: str) -> list[str]:
    return _WORD.findall(text.lower())


@dataclass
class Chunk:
    doc: str
    section: str
    text: str
    tokens: list[str]


def _chunk_document(name: str, body: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    section = "(intro)"
    buf: list[str] = []

    def flush():
        if buf:
            text = "\n".join(buf).strip()
            if text:
                chunks.append(Chunk(name, section, text, _tokenise(text)))
            buf.clear()

    for block in body.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        heading = re.match(r"^(#{1,3})\s+(.*)", block)
        if heading:
            flush()
            section = heading.group(2).strip()
            # keep heading text inside the chunk for retrieval signal
            buf.append(block)
            continue
        if sum(len(b.split()) for b in buf) + len(block.split()) > TARGET_WORDS:
            flush()
            buf.append(f"## {section}" if section != "(intro)" else "")
        buf.append(block)
    flush()
    return chunks


class BM25Index:
    K1, B = 1.5, 0.75

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.doc_freq: dict[str, int] = {}
        for c in chunks:
            for term in set(c.tokens):
                self.doc_freq[term] = self.doc_freq.get(term, 0) + 1
        self.avg_len = (sum(len(c.tokens) for c in chunks) / len(chunks)) if chunks else 0.0
        self.n = len(chunks)

    def _idf(self, term: str) -> float:
        df = self.doc_freq.get(term, 0)
        return math.log(1 + (self.n - df + 0.5) / (df + 0.5))

    def search(self, query: str, k: int = 3) -> list[dict]:
        q_terms = _tokenise(query)
        scored = []
        for c in self.chunks:
            score = 0.0
            length = len(c.tokens)
            for term in q_terms:
                tf = c.tokens.count(term)
                if not tf:
                    continue
                denom = tf + self.K1 * (1 - self.B + self.B * length / self.avg_len)
                score += self._idf(term) * tf * (self.K1 + 1) / denom
            if score > 0:
                scored.append((score, c))
        scored.sort(key=lambda x: -x[0])
        return [{"doc": c.doc, "section": c.section,
                 "score": round(s, 3), "text": c.text}
                for s, c in scored[:k]]


_index: BM25Index | None = None


def get_index() -> BM25Index:
    global _index
    if _index is None:
        chunks: list[Chunk] = []
        for path in sorted(DOCS_DIR.glob("*.md")):
            chunks.extend(_chunk_document(path.name, path.read_text()))
        _index = BM25Index(chunks)
    return _index


def search(query: str, k: int = 3) -> list[dict]:
    return get_index().search(query, k)


def corpus_stats() -> dict:
    idx = get_index()
    return {"documents": len({c.doc for c in idx.chunks}),
            "chunks": idx.n,
            "avg_chunk_tokens": round(idx.avg_len, 1)}
