from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from math import log
from pathlib import Path
import re


TOKEN_PATTERN = re.compile(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+")
HEADING_PATTERN = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)
SUPPORTED_EXTENSIONS = {".md", ".txt"}
TURKISH_ASCII_MAP = str.maketrans(
    {
        "ç": "c",
        "ğ": "g",
        "ı": "i",
        "ö": "o",
        "ş": "s",
        "ü": "u",
    }
)

TURKISH_STOPWORDS = {
    "acaba", "ama", "ancak", "artık", "aslında", "az", "bazı", "belki", "ben",
    "bile", "bir", "biraz", "birçok", "biz", "bu", "buna", "bunda", "bundan",
    "bunu", "çok", "çünkü", "da", "daha", "de", "defa", "diye", "eğer", "en",
    "gibi", "hem", "hep", "hepsi", "her", "hiç", "için", "ile", "ise", "kez",
    "ki", "kim", "mı", "mi", "mu", "mü", "nasıl", "ne", "neden", "nerde",
    "nerede", "nereye", "niçin", "niye", "o", "sanki", "şey", "siz", "şu",
    "tüm", "ve", "veya", "ya", "yani",
}
STOPWORDS = TURKISH_STOPWORDS | {word.translate(TURKISH_ASCII_MAP) for word in TURKISH_STOPWORDS}


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    title: str
    path: str
    text: str
    tokens: tuple[str, ...]


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float


def tokenize(text: str) -> list[str]:
    normalized = text.replace("İ", "i").replace("I", "ı").lower()
    tokens: list[str] = []
    for token in TOKEN_PATTERN.findall(normalized):
        if token in STOPWORDS or len(token) <= 1:
            continue
        tokens.append(token)
        folded = token.translate(TURKISH_ASCII_MAP)
        if folded != token and folded not in STOPWORDS:
            tokens.append(folded)
    return tokens


def _clean_markdown(text: str) -> str:
    text = re.sub(r"`{1,3}.*?`{1,3}", " ", text, flags=re.DOTALL)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_>#-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _split_into_chunks(path: Path, text: str, max_chars: int = 900) -> list[DocumentChunk]:
    title = path.stem.replace("_", " ").title()
    first_heading = HEADING_PATTERN.search(text)
    if first_heading:
        title = first_heading.group(1).strip()

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[DocumentChunk] = []
    buffer: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        cleaned = _clean_markdown(paragraph)
        if not cleaned:
            continue
        if current_len + len(cleaned) > max_chars and buffer:
            chunk_text = " ".join(buffer)
            chunk_id = f"{path.as_posix()}#{len(chunks) + 1}"
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    title=title,
                    path=path.as_posix(),
                    text=chunk_text,
                    tokens=tuple(tokenize(f"{title} {chunk_text}")),
                )
            )
            buffer = []
            current_len = 0
        buffer.append(cleaned)
        current_len += len(cleaned)

    if buffer:
        chunk_text = " ".join(buffer)
        chunk_id = f"{path.as_posix()}#{len(chunks) + 1}"
        chunks.append(
            DocumentChunk(
                id=chunk_id,
                title=title,
                path=path.as_posix(),
                text=chunk_text,
                tokens=tuple(tokenize(f"{title} {chunk_text}")),
            )
        )
    return chunks


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path) -> None:
        self.knowledge_dir = knowledge_dir
        self.chunks: list[DocumentChunk] = []
        self._doc_freq: dict[str, int] = {}
        self._term_freqs: dict[str, Counter[str]] = {}
        self._avg_doc_len = 1.0
        self.load()

    def load(self) -> None:
        self.chunks = []
        if not self.knowledge_dir.exists():
            self.knowledge_dir.mkdir(parents=True, exist_ok=True)

        for path in sorted(self.knowledge_dir.rglob("*")):
            if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            text = path.read_text(encoding="utf-8")
            self.chunks.extend(_split_into_chunks(path, text))

        self._build_index()

    def _build_index(self) -> None:
        doc_freq: defaultdict[str, int] = defaultdict(int)
        term_freqs: dict[str, Counter[str]] = {}
        total_len = 0

        for chunk in self.chunks:
            counts = Counter(chunk.tokens)
            term_freqs[chunk.id] = counts
            total_len += sum(counts.values())
            for token in counts:
                doc_freq[token] += 1

        self._doc_freq = dict(doc_freq)
        self._term_freqs = term_freqs
        self._avg_doc_len = total_len / max(len(self.chunks), 1)

    def search(self, query: str, top_k: int = 4) -> list[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens or not self.chunks:
            return []

        results: list[SearchResult] = []
        total_docs = len(self.chunks)
        k1 = 1.5
        b = 0.75

        for chunk in self.chunks:
            counts = self._term_freqs[chunk.id]
            doc_len = sum(counts.values()) or 1
            score = 0.0
            for token in query_tokens:
                term_count = counts.get(token, 0)
                if term_count == 0:
                    continue
                df = self._doc_freq.get(token, 0)
                idf = log(1 + (total_docs - df + 0.5) / (df + 0.5))
                denominator = term_count + k1 * (1 - b + b * doc_len / self._avg_doc_len)
                score += idf * (term_count * (k1 + 1)) / denominator

            title_tokens = set(tokenize(chunk.title))
            if title_tokens.intersection(query_tokens):
                score *= 1.12

            if score > 0:
                results.append(SearchResult(chunk=chunk, score=round(score, 4)))

        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]
