#!/usr/bin/env python3
"""
Second Brain Hybrid Vault Search CLI.
Combines exact BM25 keyword matching with dense semantic vector search:
1. Loads pre-computed chunks and inverted index from SQLite (data/vault_search.db).
2. Computes BM25 keyword scores with document length normalization.
3. Computes Cosine Similarity against dense vector embeddings.
4. Fuses rankings using Reciprocal Rank Fusion (RRF) and normalized weighted scoring.
5. Returns formatted text chunks with exact file path, line numbers, and section headings.
"""

import os
import re
import sys
import math
import json
import struct
import sqlite3
import argparse
from pathlib import Path

# UTF-8 stdout protection across OS terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = REPO_ROOT / "data"
DB_PATH = DATA_DIR / "vault_search.db"

# Import embedder from indexer
sys.path.insert(0, str(REPO_ROOT / "tools"))
try:
    import indexer
except ImportError:
    indexer = None

def ensure_index_exists():
    """Builds index automatically if not yet present."""
    if not DB_PATH.exists():
        print("[!] Index database not found. Building index automatically now...")
        if indexer:
            indexer.build_index(verbose=True)
        else:
            raise RuntimeError(f"Index database not found at {DB_PATH} and tools/indexer.py is missing.")

def tokenize(text: str) -> list[str]:
    """Basic alphanumeric tokenizer for search query."""
    return re.findall(r"\b[a-zA-Z0-9_-]{2,}\b", text.lower())

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    dot = 0.0
    norm1 = 0.0
    norm2 = 0.0
    for a, b in zip(v1, v2):
        dot += a * b
        norm1 += a * a
        norm2 += b * b
    if norm1 <= 0.0 or norm2 <= 0.0:
        return 0.0
    return dot / (math.sqrt(norm1) * math.sqrt(norm2))

def search_vault(
    query: str,
    top_k: int = 5,
    mode: str = "hybrid",
    alpha: float = 0.5,
    verbose: bool = True
) -> list[dict]:
    """
    Executes hybrid search across the vault:
    - mode: 'hybrid', 'bm25', 'vector'
    - alpha: weight for BM25 (1.0 = pure BM25, 0.0 = pure vector, 0.5 = balanced)
    """
    ensure_index_exists()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Load metadata
    cursor.execute("SELECT key, val FROM index_metadata")
    meta = dict(cursor.fetchall())
    total_chunks = int(meta.get("total_chunks", 1))
    avg_len = float(meta.get("avg_token_length", 50.0))

    query_tokens = tokenize(query)

    # 1. BM25 Scoring
    bm25_scores = {}
    if mode in ("hybrid", "bm25") and query_tokens:
        k1 = 1.5
        b = 0.75
        
        # Query matching terms
        placeholders = ",".join("?" for _ in query_tokens)
        cursor.execute(f"SELECT term, doc_freq FROM bm25_vocab WHERE term IN ({placeholders})", query_tokens)
        term_df = dict(cursor.fetchall())

        cursor.execute(f"""
        SELECT tc.term, tc.chunk_id, tc.freq, c.token_count
        FROM bm25_term_chunk tc
        JOIN chunks c ON tc.chunk_id = c.id
        WHERE tc.term IN ({placeholders})
        """, query_tokens)
        postings = cursor.fetchall()

        for term, chunk_id, freq, doc_len in postings:
            df = term_df.get(term, 1)
            idf = math.log((total_chunks - df + 0.5) / (df + 0.5) + 1.0)
            tf_component = (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * (doc_len / max(avg_len, 1.0))))
            score = idf * tf_component
            bm25_scores[chunk_id] = bm25_scores.get(chunk_id, 0.0) + score

    # 2. Dense Vector Scoring
    vector_scores = {}
    if mode in ("hybrid", "vector"):
        query_vec = indexer.generate_single_embedding(query, verbose=verbose)

        cursor.execute("SELECT id, embedding FROM chunks")
        rows = cursor.fetchall()

        for chunk_id, emb_blob in rows:
            dim = len(emb_blob) // 4
            chunk_vec = struct.unpack(f"{dim}f", emb_blob)
            sim = cosine_similarity(query_vec, chunk_vec)
            if sim > 0:
                vector_scores[chunk_id] = sim

    # 3. Hybrid Fusion via Reciprocal Rank Fusion (RRF) & Normalized Score
    # Fetch all candidate chunk records
    all_candidate_ids = set(bm25_scores.keys()) | set(vector_scores.keys())
    if not all_candidate_ids:
        conn.close()
        return []

    # Sort ranks for RRF
    sorted_bm25 = sorted(bm25_scores.items(), key=lambda x: x[1], reverse=True)
    bm25_ranks = {cid: rank for rank, (cid, _) in enumerate(sorted_bm25, start=1)}

    sorted_vector = sorted(vector_scores.items(), key=lambda x: x[1], reverse=True)
    vector_ranks = {cid: rank for rank, (cid, _) in enumerate(sorted_vector, start=1)}

    max_bm25 = max(bm25_scores.values()) if bm25_scores else 1.0
    max_vector = max(vector_scores.values()) if vector_scores else 1.0

    fused_results = []
    for cid in all_candidate_ids:
        b_score = bm25_scores.get(cid, 0.0)
        v_score = vector_scores.get(cid, 0.0)

        # Normalized scores [0, 1]
        norm_b = (b_score / max_bm25) if max_bm25 > 0 else 0.0
        norm_v = (v_score / max_vector) if max_vector > 0 else 0.0

        if mode == "bm25":
            final_score = norm_b
        elif mode == "vector":
            final_score = norm_v
        else:
            # Weighted hybrid score
            weighted_score = (alpha * norm_b) + ((1.0 - alpha) * norm_v)
            
            # Reciprocal Rank Fusion (RRF) boost
            rrf_b = 1.0 / (60.0 + bm25_ranks.get(cid, 1000))
            rrf_v = 1.0 / (60.0 + vector_ranks.get(cid, 1000))
            rrf_score = rrf_b + rrf_v
            
            final_score = (weighted_score * 0.7) + (rrf_score * 30.0 * 0.3)

        fused_results.append({
            "chunk_id": cid,
            "final_score": final_score,
            "bm25_score": b_score,
            "vector_score": v_score,
            "bm25_rank": bm25_ranks.get(cid, None),
            "vector_rank": vector_ranks.get(cid, None)
        })

    fused_results.sort(key=lambda x: x["final_score"], reverse=True)
    top_candidates = fused_results[:top_k]

    # Load chunk details from SQLite
    top_ids = [c["chunk_id"] for c in top_candidates]
    placeholders = ",".join("?" for _ in top_ids)
    cursor.execute(f"""
    SELECT id, file_path, title, date, tags, heading, start_line, end_line, content
    FROM chunks
    WHERE id IN ({placeholders})
    """, top_ids)
    chunk_map = {row[0]: row for row in cursor.fetchall()}
    conn.close()

    results = []
    for cand in top_candidates:
        c_data = chunk_map.get(cand["chunk_id"])
        if not c_data:
            continue
        results.append({
            "file_path": c_data[1],
            "title": c_data[2],
            "date": c_data[3],
            "tags": c_data[4],
            "heading": c_data[5],
            "start_line": c_data[6],
            "end_line": c_data[7],
            "content": c_data[8],
            "final_score": cand["final_score"],
            "bm25_score": cand["bm25_score"],
            "vector_score": cand["vector_score"],
            "bm25_rank": cand["bm25_rank"],
            "vector_rank": cand["vector_rank"]
        })

    return results

def format_terminal_output(query: str, results: list[dict], mode: str):
    """Prints a beautiful, executive-ready terminal search report."""
    print("=" * 80)
    print(f"[*] SECOND BRAIN HYBRID SEARCH ({mode.upper()} MODE)")
    print(f"   Query: \"{query}\"")
    print(f"   Matches Found: {len(results)}")
    print("=" * 80)

    if not results:
        print("\n[!] No matching chunks found in vault.")
        print("    Tip: Try broader keywords or run 'python tools/indexer.py' to refresh the index.")
        return

    for rank, res in enumerate(results, start=1):
        loc_str = f"{res['file_path']}#L{res['start_line']}-L{res['end_line']}"
        print(f"\n[{rank}] Score: {res['final_score']:.4f}  |  File: {loc_str}")
        print(f"    Title:   {res['title']}")
        print(f"    Section: {res['heading']}")
        
        score_breakdown = []
        if res.get('bm25_rank'):
            score_breakdown.append(f"BM25 Rank #{res['bm25_rank']} ({res['bm25_score']:.2f})")
        if res.get('vector_rank'):
            score_breakdown.append(f"Vector Rank #{res['vector_rank']} ({res['vector_score']:.3f})")
        if score_breakdown:
            print(f"    Signals: {' | '.join(score_breakdown)}")

        print("    " + "-" * 72)
        
        # Snippet preview (first 4 lines or up to 280 chars)
        lines = res["content"].splitlines()
        preview_lines = lines[:4]
        for l in preview_lines:
            if l.strip():
                print(f"    | {l}")
        if len(lines) > 4:
            print(f"    | ... ({len(lines) - 4} more lines)")

    print("\n" + "=" * 80)

def main():
    parser = argparse.ArgumentParser(description="Second Brain Hybrid Vault Search (BM25 + Semantic Vector)")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of top chunks to return (default: 5)")
    parser.add_argument("--mode", "-m", choices=["hybrid", "bm25", "vector"], default="hybrid", help="Search mode")
    parser.add_argument("--alpha", "-a", type=float, default=0.5, help="BM25 vs Vector weight balance [0.0 - 1.0]")
    parser.add_argument("--json", "-j", action="store_true", help="Output results as JSON for programmatic consumption")
    parser.add_argument("--rebuild", "-r", action="store_true", help="Force rebuild index before searching")

    args = parser.parse_args()

    if args.rebuild and indexer:
        indexer.build_index(verbose=not args.json)

    results = search_vault(
        query=args.query,
        top_k=args.top_k,
        mode=args.mode,
        alpha=args.alpha,
        verbose=not args.json
    )


    if args.json:
        # Clean output for programmatic consumption
        clean_json = []
        for r in results:
            clean_json.append({
                "file_path": r["file_path"],
                "title": r["title"],
                "heading": r["heading"],
                "start_line": r["start_line"],
                "end_line": r["end_line"],
                "final_score": round(r["final_score"], 4),
                "bm25_score": round(r["bm25_score"], 2),
                "vector_score": round(r["vector_score"], 4),
                "content": r["content"]
            })
        print(json.dumps(clean_json, indent=2, ensure_ascii=False))
    else:
        format_terminal_output(args.query, results, args.mode)

if __name__ == "__main__":
    main()
