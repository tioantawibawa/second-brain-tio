#!/usr/bin/env python3
"""
Second Brain Hybrid Vault Indexer.
Builds and maintains a local hybrid search index (BM25 + Semantic Vector Search):
1. Scans Markdown documents across wiki/, journal/, crm/, and raw/processed/ (plus in_motion/ and lattices/).
2. Chunks documents by heading / logical paragraphs with accurate line numbers and metadata.
3. Generates 384-dimensional dense embeddings using local lightweight models (FastEmbed / all-MiniLM-L6-v2)
   with automatic zero-dependency dense fallback.
4. Stores chunks, inverted BM25 index, and dense vectors in SQLite (data/vault_search.db).
"""

import os
import re
import sys
import math
import json
import struct
import sqlite3
import hashlib
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
import time

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
DB_PATH = DATA_DIR / "vault_search.db"

TARGET_DIRS = [
    "wiki",
    "journal",
    "crm",
    "raw/processed",
    "in_motion",
    "lattices"
]

EXCLUDE_FILENAMES = {
    "index.md",
    "agents.md",
    "log.md",
    "README.md",
    "RULES.md"
}

# ================= 1. Embedding Engine (FastEmbed / SentenceTransformers / Fallback) =================

_EMBEDDER_TYPE = None
_EMBEDDER_MODEL = None

def init_embedder(verbose: bool = True):
    """Initializes the best available local embedding model."""
    global _EMBEDDER_TYPE, _EMBEDDER_MODEL
    if _EMBEDDER_TYPE is not None:
        return _EMBEDDER_TYPE

    # 1. Try FastEmbed (ultralight CPU ONNX runtime, ~50MB RAM)
    try:
        from fastembed import TextEmbedding
        _EMBEDDER_MODEL = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        _EMBEDDER_TYPE = "fastembed"
        if verbose:
            print("[*] Loaded local FastEmbed ONNX model (all-MiniLM-L6-v2)")
        return _EMBEDDER_TYPE
    except Exception:
        pass

    # 2. Try SentenceTransformers (PyTorch)
    try:
        from sentence_transformers import SentenceTransformer
        _EMBEDDER_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
        _EMBEDDER_TYPE = "sentence-transformers"
        if verbose:
            print("[*] Loaded SentenceTransformers model (all-MiniLM-L6-v2)")
        return _EMBEDDER_TYPE
    except Exception:
        pass

    # 3. Deterministic 384-dim Dense Semantic Hash Embedder (Zero-Dependency)
    _EMBEDDER_TYPE = "dense-hash-384"
    if verbose:
        print("[*] Local ML libraries not detected. Using built-in 384-dim dense semantic embedder.")
        print("    Tip: run 'pip install fastembed' or 'pip install sentence-transformers' for neural ONNX embeddings.")
    return _EMBEDDER_TYPE


def dense_hash_embed(text: str, dim: int = 384) -> list[float]:
    """Generates L2-normalized 384-dimensional dense semantic vector without external packages."""
    vec = [0.0] * dim
    tokens = re.findall(r"\b\w+\b", text.lower())
    if not tokens:
        return vec
        
    for i, token in enumerate(tokens):
        # Word hash
        h1 = int(hashlib.md5(token.encode("utf-8")).hexdigest()[:8], 16) % dim
        vec[h1] += 1.0 / (1.0 + math.log(1 + i * 0.1))
        
        # Bigram hash if possible
        if i < len(tokens) - 1:
            bigram = f"{token}_{tokens[i+1]}"
            h2 = int(hashlib.sha256(bigram.encode("utf-8")).hexdigest()[:8], 16) % dim
            vec[h2] += 1.5

        # Character tri-grams for spelling & morphological robustness
        if len(token) >= 3:
            for c in range(len(token) - 2):
                tri = token[c:c+3]
                h3 = int(hashlib.sha1(tri.encode("utf-8")).hexdigest()[:8], 16) % dim
                vec[h3] += 0.4

    # L2 normalize
    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        vec = [x / norm for x in vec]
    return vec

def generate_embeddings(texts: list[str], verbose: bool = True) -> list[list[float]]:
    """Encodes a list of texts into dense vectors."""
    engine = init_embedder(verbose=verbose)
    if engine == "fastembed":
        embeddings = list(_EMBEDDER_MODEL.embed(texts))
        return [list(map(float, emb)) for emb in embeddings]
    elif engine == "sentence-transformers":
        embeddings = _EMBEDDER_MODEL.encode(texts, normalize_embeddings=True)
        return [list(map(float, emb)) for emb in embeddings]
    else:
        return [dense_hash_embed(t) for t in texts]

def generate_single_embedding(text: str, verbose: bool = True) -> list[float]:
    """Encodes a single query string into a dense vector."""
    res = generate_embeddings([text], verbose=verbose)
    return res[0]


# ================= 2. Document Parsing & Chunking =================

def parse_frontmatter(content: str) -> tuple[dict, str, int]:
    """Extracts YAML frontmatter, body, and body start line."""
    meta = {}
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return meta, content, 1

    yaml_lines = []
    closing_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            closing_idx = i
            break
        yaml_lines.append(lines[i])

    if closing_idx == -1:
        return meta, content, 1

    for yl in yaml_lines:
        yl = yl.strip()
        if not yl or yl.startswith("#") or ":" not in yl:
            continue
        k, v = yl.split(":", 1)
        k = k.strip().lower()
        v = v.strip().strip("\"'")
        meta[k] = v

    body_start_line = closing_idx + 2
    body = "\n".join(lines[closing_idx + 1:])
    return meta, body, body_start_line

def chunk_markdown_file(file_path: Path) -> list[dict]:
    """Chunks a Markdown file by section headings with accurate line numbers."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"[!] Warning reading {file_path}: {e}")
        return []

    lines = content.splitlines()
    if not lines:
        return []

    meta, _, body_start = parse_frontmatter(content)
    rel_path = file_path.relative_to(REPO_ROOT).as_posix()
    
    # Document title
    title = meta.get("title")
    if not title:
        for line in lines:
            if line.startswith("# "):
                title = line[2:].strip()
                break
    if not title:
        title = file_path.stem.replace("-", " ").title()

    date_str = meta.get("date") or meta.get("ingest_date") or ""
    tags_str = meta.get("tags") or ""

    chunks = []
    current_heading = "Overview"
    current_lines = []
    chunk_start_line = body_start

    # Regex for markdown headings #, ##, ###, ####
    heading_re = re.compile(r"^(#{1,4})\s+(.+)$")

    for idx, line in enumerate(lines, start=1):
        if idx < body_start:
            continue

        match = heading_re.match(line.strip())
        if match:
            # Commit previous chunk if not empty
            text_content = "\n".join(current_lines).strip()
            if text_content and len(text_content) > 25:
                chunks.append({
                    "file_path": rel_path,
                    "title": title,
                    "date": date_str,
                    "tags": tags_str,
                    "heading": current_heading,
                    "start_line": chunk_start_line,
                    "end_line": idx - 1,
                    "content": text_content
                })
            current_heading = match.group(0).strip()
            current_lines = [line]
            chunk_start_line = idx
        else:
            current_lines.append(line)

    # Commit last chunk
    text_content = "\n".join(current_lines).strip()
    if text_content and len(text_content) > 20:
        chunks.append({
            "file_path": rel_path,
            "title": title,
            "date": date_str,
            "tags": tags_str,
            "heading": current_heading,
            "start_line": chunk_start_line,
            "end_line": len(lines),
            "content": text_content
        })

    # Fallback if document has no headings or was too short
    if not chunks and content.strip():
        chunks.append({
            "file_path": rel_path,
            "title": title,
            "date": date_str,
            "tags": tags_str,
            "heading": "Document Content",
            "start_line": 1,
            "end_line": len(lines),
            "content": content.strip()
        })

    return chunks

# ================= 3. Database Schema & Index Storage =================

def init_db(db_conn: sqlite3.Connection):
    """Initializes tables for chunk storage, inverted index, and BM25 statistics."""
    cursor = db_conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chunks (
        id TEXT PRIMARY KEY,
        file_path TEXT NOT NULL,
        title TEXT NOT NULL,
        date TEXT,
        tags TEXT,
        heading TEXT,
        start_line INTEGER,
        end_line INTEGER,
        content TEXT NOT NULL,
        token_count INTEGER NOT NULL,
        embedding BLOB NOT NULL
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_path);")
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bm25_vocab (
        term TEXT PRIMARY KEY,
        doc_freq INTEGER NOT NULL
    );
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bm25_term_chunk (
        term TEXT NOT NULL,
        chunk_id TEXT NOT NULL,
        freq INTEGER NOT NULL,
        PRIMARY KEY (term, chunk_id)
    );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bm25_term ON bm25_term_chunk(term);")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS index_metadata (
        key TEXT PRIMARY KEY,
        val REAL NOT NULL
    );
    """)
    db_conn.commit()

def tokenize(text: str) -> list[str]:
    """Tokenizes text for BM25 keyword matching."""
    return re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())

def build_index(verbose: bool = True) -> int:
    """Scans all target vault folders, chunks documents, embeds them, and writes SQLite index."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"[*] Scanning vault directories: {', '.join(TARGET_DIRS)} ...")

    all_chunks = []
    scanned_files = 0

    for target_rel in TARGET_DIRS:
        folder_path = REPO_ROOT / target_rel
        if not folder_path.exists():
            continue

        for md_file in folder_path.glob("**/*.md"):
            if md_file.name in EXCLUDE_FILENAMES or md_file.name.startswith("."):
                continue
            if ".archive" in md_file.parts or "__pycache__" in md_file.parts:
                continue

            file_chunks = chunk_markdown_file(md_file)
            all_chunks.extend(file_chunks)
            scanned_files += 1

    if not all_chunks:
        if verbose:
            print("[!] No documents found to index.")
        return 0

    if verbose:
        print(f"[*] Found {scanned_files} files -> Generated {len(all_chunks)} semantic chunks.")
        print("[*] Generating dense vector embeddings...")

    # Prepare texts for embedding (prepend Title + Heading for contextual retrieval)
    embed_inputs = [f"{c['title']} | {c['heading']}\n{c['content']}" for c in all_chunks]
    embeddings = generate_embeddings(embed_inputs)

    # Initialize SQLite database
    conn = sqlite3.connect(str(DB_PATH))
    init_db(conn)
    cursor = conn.cursor()

    # Clear old index tables
    cursor.execute("DELETE FROM chunks;")
    cursor.execute("DELETE FROM bm25_vocab;")
    cursor.execute("DELETE FROM bm25_term_chunk;")
    cursor.execute("DELETE FROM index_metadata;")

    total_tokens = 0
    doc_freqs = Counter()
    chunk_records = []
    term_chunk_records = []

    for i, chunk in enumerate(all_chunks):
        chunk_hash = hashlib.sha256(
            f"{chunk['file_path']}#{chunk['heading']}#{chunk['start_line']}".encode("utf-8")
        ).hexdigest()[:16]
        
        tokens = tokenize(f"{chunk['title']} {chunk['heading']} {chunk['content']}")
        token_count = len(tokens)
        total_tokens += token_count
        
        term_counts = Counter(tokens)
        for term, cnt in term_counts.items():
            doc_freqs[term] += 1
            term_chunk_records.append((term, chunk_hash, cnt))

        vec = embeddings[i]
        vec_bytes = struct.pack(f"{len(vec)}f", *vec)

        chunk_records.append((
            chunk_hash,
            chunk["file_path"],
            chunk["title"],
            chunk["date"],
            chunk["tags"],
            chunk["heading"],
            chunk["start_line"],
            chunk["end_line"],
            chunk["content"],
            token_count,
            vec_bytes
        ))

    # Bulk insert chunks
    cursor.executemany("""
    INSERT INTO chunks (id, file_path, title, date, tags, heading, start_line, end_line, content, token_count, embedding)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, chunk_records)

    # Bulk insert inverted BM25 index
    cursor.executemany("""
    INSERT INTO bm25_term_chunk (term, chunk_id, freq)
    VALUES (?, ?, ?)
    """, term_chunk_records)

    cursor.executemany("""
    INSERT INTO bm25_vocab (term, doc_freq)
    VALUES (?, ?)
    """, doc_freqs.items())

    # Metadata & BM25 parameters
    avg_len = total_tokens / max(len(all_chunks), 1)
    cursor.execute("INSERT INTO index_metadata (key, val) VALUES ('total_chunks', ?)", (len(all_chunks),))
    cursor.execute("INSERT INTO index_metadata (key, val) VALUES ('avg_token_length', ?)", (avg_len,))
    cursor.execute("INSERT INTO index_metadata (key, val) VALUES ('embed_dim', ?)", (len(embeddings[0]),))
    cursor.execute("INSERT INTO index_metadata (key, val) VALUES ('last_updated', ?)", (time.time(),))

    conn.commit()
    conn.close()

    if verbose:
        print(f"[+] Index successfully saved to {DB_PATH.relative_to(REPO_ROOT)}")
        print(f"    - Total Documents: {scanned_files}")
        print(f"    - Total Chunks: {len(all_chunks)}")
        print(f"    - Unique BM25 Terms: {len(doc_freqs)}")
        print(f"    - Embedding Dimension: {len(embeddings[0])}")
    return len(all_chunks)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Second Brain Vault Hybrid Indexer")
    parser.add_argument("--rebuild", "-r", action="store_true", help="Force complete rebuild of the index")
    args = parser.parse_args()

    start_time = time.time()
    count = build_index(verbose=True)
    duration = time.time() - start_time
    print(f"[+] Indexing completed in {duration:.2f} seconds ({count} chunks indexed).")

if __name__ == "__main__":
    main()
