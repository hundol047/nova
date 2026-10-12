"""Organizer guideline corpus (N.O.V.A. 2026 진료지침 코퍼스) at runtime: a lightweight, license-aware lexical index.

The official evaluation and sample-validation containers mount the full corpus READ-ONLY at /opt/nova/guidelines and
point NOVA_GUIDELINES_DIR at it (15,904 Markdown documents with YAML metadata, plus catalog.csv). Nothing from the
corpus is packaged, downloaded or written anywhere: prepare() builds an in-memory metadata index (title,
organization, document type, filename -- never full text), and consult() lazily opens the few best-matching
documents and keeps a short excerpt only in memory for the Doctor prompt. Every excerpt keeps its title,
organization, year, license and source_url. When the directory is absent (local development) every call degrades to
an empty result and the engine's own knowledge is used unchanged.

Licensing: the corpus mixes public domain, CC BY / BY-SA / BY-NC / BY-NC-SA / BY-ND / BY-NC-ND, 공공누리 0/4 and
society-permission documents. This module never persists or redistributes text, translations or summaries of them;
excerpts exist only inside one encounter's process memory.
"""
from __future__ import annotations

import csv
import math
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_WORD = re.compile(r"[a-z][a-z0-9\-]{2,}|[가-힣]{2,}|\d{2,}")
_STOP = frozenset("the and for with from that this are was were has have not but you your can may will its into "
                  "about which when what who how than then also such other more most some any all per via use used "
                  "guideline guidelines recommendation recommendations review clinical practice patient patients "
                  "management treatment diagnosis disease disorder 진료지침 권고 환자 치료 진단 질환".split())
_MAX_READ_BYTES = 400_000
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)


def tokens(text: str) -> List[str]:
    """Lower-cased English words, Hangul words and their character bigrams (Korean has no spaces inside compounds)."""
    out: List[str] = []
    for word in _WORD.findall((text or "").lower()):
        if word in _STOP:
            continue
        out.append(word)
        if re.match(r"[가-힣]", word) and len(word) > 2:
            out.extend(word[i:i + 2] for i in range(len(word) - 1))
    return out


@dataclass
class GuidelineDoc:
    path: str
    title: str = ""
    organization: str = ""
    year: str = ""
    language: str = ""
    doc_type: str = ""
    license: str = ""
    source_url: str = ""

    def meta(self) -> dict:
        return {"title": self.title, "organization": self.organization, "year": self.year, "language": self.language,
                "document_type": self.doc_type, "license": self.license, "source_url": self.source_url}


@dataclass
class GuidelineIndex:
    root: Optional[Path]
    docs: List[GuidelineDoc] = field(default_factory=list)
    postings: Dict[str, List[int]] = field(default_factory=dict)
    build_seconds: float = 0.0
    skipped: int = 0
    source: str = "none"

    @property
    def available(self) -> bool:
        return bool(self.docs)

    def stats(self) -> dict:
        return {"available": self.available, "documents": len(self.docs), "terms": len(self.postings),
                "build_seconds": round(self.build_seconds, 3), "skipped": self.skipped, "source": self.source}

    # --- retrieval -------------------------------------------------------------------------------------------------
    def search(self, query: str, k: int = 3) -> List[GuidelineDoc]:
        if not self.docs:
            return []
        n = len(self.docs)
        scores: Dict[int, float] = {}
        for term in set(tokens(query)):
            hits = self.postings.get(term)
            if not hits:
                continue
            idf = math.log(1 + n / len(hits))
            for doc_id in hits:
                scores[doc_id] = scores.get(doc_id, 0.0) + idf
        ranked = sorted(scores.items(), key=lambda kv: (-kv[1], self.docs[kv[0]].path))
        return [self.docs[i] for i, _ in ranked[:k]]

    def excerpt(self, doc: GuidelineDoc, query: str, max_chars: int = 900) -> str:
        """The paragraphs of one document that share the most query terms, at most ``max_chars`` (in memory only)."""
        path = self._resolve(doc.path)
        if path is None:
            return ""
        try:
            with open(path, "rb") as handle:
                text = handle.read(_MAX_READ_BYTES).decode("utf-8", errors="replace")
        except OSError:
            return ""
        text = _FRONT_MATTER.sub("", text, count=1)
        wanted = set(tokens(query))
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 40]
        scored = sorted(((len(wanted & set(tokens(p))), -i, p) for i, p in enumerate(paragraphs)), reverse=True)
        picked, used = [], 0
        for score, _, para in scored:
            if score == 0 or used >= max_chars:
                break
            piece = re.sub(r"\s+", " ", para)[: max_chars - used]
            picked.append(piece)
            used += len(piece)
        return "\n".join(picked)

    def _resolve(self, relative: str) -> Optional[Path]:
        if self.root is None:
            return None
        candidate = (self.root / relative)
        try:
            if candidate.is_symlink() or any(p.is_symlink() for p in candidate.parents if p != self.root.parent):
                return None
            resolved = candidate.resolve()
            resolved.relative_to(self.root.resolve())
        except (OSError, ValueError):
            return None
        return resolved if resolved.is_file() else None


def _norm_header(name: str) -> str:
    return re.sub(r"[\s_\-]+", "", (name or "").strip().lower())


_CATALOG_FIELDS = {
    "path": ("filename", "file", "path", "filepath", "파일명"),
    "title": ("title", "제목"),
    "organization": ("organization", "organisation", "org", "기관", "발행기관"),
    "year": ("year", "연도"),
    "language": ("language", "lang", "언어"),
    "doc_type": ("documenttype", "doctype", "type", "문서유형", "유형"),
    "license": ("license", "licence", "라이선스", "이용허락"),
    "source_url": ("sourceurl", "source", "url", "출처", "원문url"),
}


def _parse_front_matter(head: str) -> dict:
    match = _FRONT_MATTER.match(head)
    if not match:
        return {}
    out = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.startswith((" ", "\t")):
            out[key.strip().lower()] = value.strip().strip("'\"")
    return out


def build_index(root: Optional[str] = None, time_budget_seconds: float = 240.0, max_documents: int = 30_000) -> GuidelineIndex:
    """Metadata index of the organizer corpus. Never raises: a missing/unreadable directory gives an empty index."""
    started = time.monotonic()
    root_value = root if root is not None else os.environ.get("NOVA_GUIDELINES_DIR", "")
    base = Path(root_value) if root_value else None
    index = GuidelineIndex(root=base if base and base.is_dir() and not base.is_symlink() else None)
    if index.root is None or max_documents <= 0 or time_budget_seconds <= 0:
        return index
    catalog = index.root / "catalog.csv"
    rows: List[dict] = []
    if catalog.is_file() and not catalog.is_symlink():
        try:
            with open(catalog, newline="", encoding="utf-8-sig") as handle:
                reader = csv.DictReader(handle)
                header = {_norm_header(h): h for h in (reader.fieldnames or [])}
                lookup = {k: next((header[c] for c in v if c in header), None) for k, v in _CATALOG_FIELDS.items()}
                for row in reader:
                    if time.monotonic() - started > time_budget_seconds:
                        break
                    rows.append({k: (row.get(col) or "").strip() if col else "" for k, col in lookup.items()})
                    if len(rows) >= max_documents:
                        break
            index.source = "catalog.csv"
        except (OSError, csv.Error, UnicodeError):
            rows = []
    if not rows:
        index.source = "front_matter"
        for dirpath, dirnames, filenames in os.walk(index.root, followlinks=False):
            if len(rows) >= max_documents or time.monotonic() - started > time_budget_seconds:
                break
            dirnames[:] = sorted(d for d in dirnames if not (Path(dirpath) / d).is_symlink())
            for name in sorted(filenames):
                if not name.endswith(".md") or time.monotonic() - started > time_budget_seconds:
                    continue
                path = Path(dirpath) / name
                if path.is_symlink():
                    index.skipped += 1
                    continue
                try:
                    with open(path, "rb") as handle:
                        meta = _parse_front_matter(handle.read(4096).decode("utf-8", errors="replace"))
                except OSError:
                    index.skipped += 1
                    continue
                rows.append({"path": str(path.relative_to(index.root)), "title": meta.get("title", ""),
                             "organization": meta.get("organization", ""), "year": meta.get("year", ""),
                             "language": meta.get("language", ""), "doc_type": meta.get("document_type", meta.get("type", "")),
                             "license": meta.get("license", ""), "source_url": meta.get("source_url", "")})
                if len(rows) >= max_documents:
                    break
    for row in rows:
        if time.monotonic() - started > time_budget_seconds:
            break
        relative = row.get("path", "")
        if not relative or relative.startswith(("/", "\\")) or ".." in Path(relative).parts:
            index.skipped += 1
            continue
        if index._resolve(relative) is None or any(len(str(v)) > 4096 for v in row.values()):
            index.skipped += 1
            continue
        doc = GuidelineDoc(path=relative, title=row.get("title", ""), organization=row.get("organization", ""),
                           year=row.get("year", ""), language=row.get("language", ""), doc_type=row.get("doc_type", ""),
                           license=row.get("license", ""), source_url=row.get("source_url", ""))
        doc_id = len(index.docs)
        index.docs.append(doc)
        stem = re.sub(r"[_\-.]+", " ", Path(relative).stem)
        for term in sorted(set(tokens(f"{doc.title} {stem}")))[:128]:
            index.postings.setdefault(term, []).append(doc_id)
    index.build_seconds = time.monotonic() - started
    return index


def retrieve(index: Optional[GuidelineIndex], query: str, k: int = 3, max_chars: int = 900) -> List[dict]:
    """Up to ``k`` excerpts with their metadata for the Doctor prompt; [] when no corpus is mounted."""
    if index is None or not index.available or not (query or "").strip():
        return []
    out = []
    for doc in index.search(query, k=k * 2):
        text = index.excerpt(doc, query, max_chars=max_chars)
        if text:
            out.append({**doc.meta(), "excerpt": text})
        if len(out) >= k:
            break
    return out
