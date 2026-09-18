"""
===============================================================================
FILE: vector_store.py
===============================================================================
WHAT IS THIS FILE FOR? (THE INTENT):
Imagine you walk into a giant library and ask: "Where can I read about managing
debt and money?" A basic search engine might look only for the exact word "debt".
If a book talks about "loans", "liabilities", or "credit", a dumb search engine
would miss it completely!

This file provides our "Semantic Brain" and "Vector Database". It translates words
and sentences into mathematical arrows (vectors) in 256-dimensional space.
Concepts with similar meanings (like "cash" and "liquidity") point in almost the
exact same direction. We use SQLite to store these vectors on your hard drive
without needing any heavy external servers or complex cloud databases.

HOW IT WORKS IN SIMPLE TERMS:
1. `DenseEmbeddingEngine`:
   - Takes a piece of text (e.g., "Corporate Capital and Cash Flows").
   - Cleans it up by removing useless filler words like "the", "a", "is" (called stop-words).
   - Generates 256 numbers representing the semantic flavor of the text using
     word n-grams, sub-word letter hashes, and special keyword boosts.
   - Normalizes the arrow so its length is exactly 1 (L2 normalization).

2. `BuiltinVectorDB`:
   - Creates an SQLite database file (`vector_store.sqlite`).
   - Tables:
     * `documents`: Stores document titles, authors, and metadata.
     * `chunks`: Stores each text paragraph along with its vector blob.
     * `taxonomy_nodes`: Stores each concept in our master hierarchy with its vector.
     * `user_notes`: Stores personal student/reader annotations so they are searchable.
     * `similarity_cache`: Caches math calculations for speed.
   - Computes Cosine Similarity (the angle between two vectors). If the similarity
     score is high (e.g. >= 0.30), it knows the passage and concept are deeply related!

INPUTS:
- Text chunks from books.
- Taxonomy concept names and descriptions.
- User notes and annotations.

OUTPUTS:
- Numerical similarity scores between 0.0 (unrelated) and 1.0 (identical meaning).
- Top-K most relevant taxonomy concepts for any given passage.

ERROR HANDLING:
- Safely handles empty texts by returning zero-vectors.
- Automatically handles database connections and transactions safely using `with sqlite3.connect`.
===============================================================================
"""

import os
import re
import json
import math
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import numpy as np


class DenseEmbeddingEngine:
    """
    Transforms plain English text into 256-dimensional dense numerical vectors
    that capture semantic relationships and meaning.
    """

    def __init__(self, dim: int = 256):
        """
        Initialize the embedding engine.
        
        Args:
            dim: The number of dimensions for each vector (default: 256).
        """
        self.dim = dim
        # Stop-words: Common filler words that carry very little unique meaning
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
            'which', 'what', 'where', 'when', 'who', 'how', 'all', 'any', 'both',
            'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will',
            'just', 'should', 'now', 'also', 'as', 'if', 'may', 'would', 'could'
        }

    def _hash_token(self, token: str) -> int:
        """
        Helper method: Takes a word or sub-word and maps it deterministically to an
        index between 0 and 255 using MD5 hashing.
        """
        h = hashlib.md5(token.encode('utf-8')).hexdigest()
        return int(h, 16) % self.dim

    def encode(self, text: str, extra_weight_terms: Optional[List[str]] = None) -> np.ndarray:
        """
        Encodes a string into a normalized 256-dimensional NumPy vector.

        Args:
            text: The sentence or paragraph to encode.
            extra_weight_terms: Optional list of priority keywords to boost in the vector.

        Returns:
            np.ndarray of shape (256,) with unit length (L2 norm = 1.0).
        """
        # If text is empty, return a blank vector of zeros
        if not text:
            return np.zeros(self.dim, dtype=np.float32)

        # Step 1: Tokenize by extracting lowercase words of length >= 3
        tokens = [w for w in re.findall(r'\b[a-z]{3,}\b', text.lower()) if w not in self.stop_words]
        vec = np.zeros(self.dim, dtype=np.float32)

        if not tokens:
            return vec

        # Step 2: Accumulate individual words and 3-character sub-words (catches word stems)
        for t in tokens:
            idx = self._hash_token(t)
            vec[idx] += 1.0
            for i in range(len(t) - 2):
                sub = t[i:i+3]
                sub_idx = self._hash_token(sub)
                vec[sub_idx] += 0.25

        # Step 3: Accumulate adjacent 2-word pairs (bi-grams like 'capital_budgeting')
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]}_{tokens[i+1]}"
            b_idx = self._hash_token(bigram)
            vec[b_idx] += 1.5

        # Step 4: Apply extra weight multiplier to special domain keywords
        if extra_weight_terms:
            for kw in extra_weight_terms:
                for kw_t in re.findall(r'\b[a-z]{3,}\b', kw.lower()):
                    if kw_t not in self.stop_words:
                        idx = self._hash_token(kw_t)
                        vec[idx] += 3.0

        # Step 5: Normalize the vector so its length is exactly 1.0 (Unit Sphere)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.astype(np.float32)


class BuiltinVectorDB:
    """
    An embedded, serverless SQLite Vector Database storing document chunks,
    taxonomy vectors, and user notes for fast semantic retrieval.
    """

    def __init__(self, db_path: str = "output_taxonomy/vector_store/vector_store.sqlite"):
        """
        Initialize the database connection and tables.
        
        Args:
            db_path: File path on disk for the SQLite database.
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.embedder = DenseEmbeddingEngine(dim=256)
        self._init_db()

    def _init_db(self):
        """
        Creates all required relational tables if they do not already exist.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT,
                    metadata_json TEXT,
                    chunk_count INTEGER,
                    updated_at TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT,
                    section TEXT,
                    text TEXT,
                    word_count INTEGER,
                    vector_blob BLOB,
                    FOREIGN KEY(doc_id) REFERENCES documents(doc_id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS taxonomy_nodes (
                    taxonomy_id TEXT PRIMARY KEY,
                    name TEXT,
                    keywords_json TEXT,
                    description TEXT,
                    domain TEXT,
                    depth INTEGER,
                    vector_blob BLOB
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_notes (
                    note_id TEXT PRIMARY KEY,
                    doc_id TEXT,
                    taxonomy_id TEXT,
                    content TEXT,
                    vector_blob BLOB,
                    created_at TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS similarity_cache (
                    cache_key TEXT PRIMARY KEY,
                    score REAL,
                    updated_at TEXT
                )
            ''')
            conn.commit()

    def save_document_chunks(self, doc_id: str, title: str, metadata: Dict[str, Any], chunks: List[Dict[str, Any]]):
        """
        Saves document information and converts every passage chunk into a dense vector blob in SQLite.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute(
                "INSERT OR REPLACE INTO documents (doc_id, title, metadata_json, chunk_count, updated_at) VALUES (?, ?, ?, ?, ?)",
                (doc_id, title, json.dumps(metadata), len(chunks), now)
            )

            for c in chunks:
                c_id = c['chunk_id']
                text = c['text']
                vec = self.embedder.encode(text)
                vec_blob = vec.tobytes()
                cursor.execute(
                    "INSERT OR REPLACE INTO chunks (chunk_id, doc_id, section, text, word_count, vector_blob) VALUES (?, ?, ?, ?, ?, ?)",
                    (c_id, doc_id, c.get('section', 'Main'), text, c.get('word_count', len(text.split())), vec_blob)
                )
            conn.commit()

    def save_taxonomy_nodes(self, nodes: List[Dict[str, Any]]):
        """
        Saves taxonomy concepts and embeds their titles, keywords, and descriptions into vector blobs.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            for n in nodes:
                t_id = n['taxonomy_id']
                name = n['name']
                kw = n.get('keywords', [])
                desc = n.get('description', '')
                domain = n.get('domain', 'General')
                depth = n.get('depth', 1)

                full_text = f"{name} {' '.join(kw)} {desc}"
                vec = self.embedder.encode(full_text, extra_weight_terms=kw)
                vec_blob = vec.tobytes()

                cursor.execute(
                    "INSERT OR REPLACE INTO taxonomy_nodes (taxonomy_id, name, keywords_json, description, domain, depth, vector_blob) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (t_id, name, json.dumps(kw), desc, domain, depth, vec_blob)
                )
            conn.commit()

    def save_user_note(self, doc_id: str, taxonomy_id: Optional[str], content: str) -> str:
        """
        Saves a personal user note/reflection and indexes it into the vector database.
        """
        note_id = f"NOTE_{doc_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        vec = self.embedder.encode(content)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO user_notes (note_id, doc_id, taxonomy_id, content, vector_blob, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (note_id, doc_id, taxonomy_id, content, vec.tobytes(), datetime.now().isoformat())
            )
            conn.commit()
        return note_id

    def get_user_notes(self, doc_id: str) -> List[Dict[str, Any]]:
        """
        Retrieves all saved user notes for a specific document.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT note_id, taxonomy_id, content, created_at FROM user_notes WHERE doc_id = ? ORDER BY created_at ASC", (doc_id,))
            rows = cursor.fetchall()
            return [{"note_id": r[0], "taxonomy_id": r[1], "content": r[2], "created_at": r[3]} for r in rows]

    def compute_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Computes the mathematical Cosine Similarity between two vectors:
        Cosine_Similarity = (A . B) / (||A|| * ||B||)
        Returns a score between 0.0 (completely different) and 1.0 (identical).
        """
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def get_all_taxonomy_vectors(self) -> List[Dict[str, Any]]:
        """
        Loads all stored taxonomy concept vectors from the database into memory.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT taxonomy_id, name, keywords_json, description, domain, depth, vector_blob FROM taxonomy_nodes")
            rows = cursor.fetchall()
            results = []
            for r in rows:
                vec = np.frombuffer(r[6], dtype=np.float32) if r[6] else np.zeros(256, dtype=np.float32)
                results.append({
                    "taxonomy_id": r[0],
                    "name": r[1],
                    "keywords": json.loads(r[2]) if r[2] else [],
                    "description": r[3],
                    "domain": r[4],
                    "depth": r[5],
                    "vector": vec
                })
            return results

    def query_similar_concepts(self, chunk_text: str, top_k: int = 5, threshold: float = 0.30) -> List[Dict[str, Any]]:
        """
        Given a paragraph of text, finds the top matching taxonomy concepts whose
        semantic similarity score meets or exceeds the threshold.

        Args:
            chunk_text: The passage to compare against the taxonomy.
            top_k: Maximum number of closest concepts to return.
            threshold: Minimum required similarity score (e.g., 0.25 - 0.30).

        Returns:
            List of matching concept dictionaries sorted from highest score to lowest.
        """
        tax_nodes = self.get_all_taxonomy_vectors()
        if not tax_nodes:
            return []

        chunk_vec = self.embedder.encode(chunk_text)
        scored = []
        for node in tax_nodes:
            sim = self.compute_similarity(chunk_vec, node['vector'])
            score = round(max(0.0, min(1.0, sim)), 3)
            if score >= threshold:
                scored.append({
                    "taxonomy_id": node['taxonomy_id'],
                    "taxonomy_name": node['name'],
                    "domain": node['domain'],
                    "depth": node['depth'],
                    "strength": score
                })

        scored.sort(key=lambda x: x['strength'], reverse=True)
        return scored[:top_k]
