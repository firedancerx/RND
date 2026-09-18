"""
===============================================================================
FILE: semantic_linker.py
===============================================================================
WHAT IS THIS FILE FOR? (Intent & Big Picture)
Imagine you are reading a book about economics, and you see the phrase
"Compound Interest" or "Cash Flow Statement". In a traditional physical library,
the book sits alone on a shelf. But in our digital Knowledge Management system,
we want every single paragraph in every book to automatically connect to a
central "concept map" (our Master Taxonomy) and even link concepts together!

This file acts as the "Smart Librarian" and "Detective" who reads paragraphs,
compares them against our Master Taxonomy using mathematical AI vectors (embeddings),
finds strong conceptual similarities, and extracts Subject-Predicate-Object triplets
(for example: "Assets" -- "generates" --> "Future Economic Benefits").

-------------------------------------------------------------------------------
KEY PROCESSES CARRIED OUT:
1. Vector Similarity Matching: Compares each document passage against all taxonomy
   concepts using high-dimensional cosine similarity.
2. Two-Way (Bi-Directional) Indexing:
   - Passage -> Taxonomy: "What concepts are discussed in this paragraph?"
   - Taxonomy -> Passages: "Which paragraphs across the entire library mention this concept?"
3. Semantic Triplet Extraction: Discovers subject-verb-object knowledge relationships.

COMPONENTS USED:
- BuiltinVectorDB (vector_store.py): Our embedded SQLite vector database.
- TaxonomyGenerator (generate_taxonomy.py): Used to extract grammar-based triplets.
- numpy: For vector math operations.

INPUTS:
- chunks: List of atomic text passages from ingested books.
- taxonomy_nodes: The master catalog of all validated knowledge concepts.

OUTPUTS:
- passage_to_taxonomy: Dictionary mapping chunk IDs to matching taxonomy concepts.
- taxonomy_to_passages: Dictionary mapping taxonomy IDs to all relevant book passages.
- triplets: List of extracted semantic knowledge triplets.

ERROR HANDLING & EDGE CASES:
- Handles empty chunk lists or empty taxonomy catalogs gracefully.
- Filters out weak or unrelated matches using a configurable similarity threshold.
===============================================================================
"""

import math
import json
import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

# Import our custom embedded vector store and taxonomy generator tools
from vector_store import BuiltinVectorDB
from generate_taxonomy import TaxonomyGenerator


class SemanticLinker:
    """
    The SemanticLinker is responsible for computing two-way links between book chunks
    and taxonomy topics, as well as extracting relational triplets from text.
    """

    def __init__(self, similarity_threshold: float = 0.25, vector_db: Optional[BuiltinVectorDB] = None):
        """
        INITIALIZATION:
        - similarity_threshold: Minimum cosine similarity score (0.0 to 1.0) needed
          for a paragraph to be officially connected to a taxonomy concept.
        - vector_db: Our SQLite database holding vectors for fast search.
        """
        # Store the minimum similarity cutoff score (default: 0.25)
        self.similarity_threshold = similarity_threshold
        # If no vector DB was passed in, initialize a default connection to our SQLite database
        self.vector_db = vector_db or BuiltinVectorDB()
        # Initialize the taxonomy helper for extracting semantic triplets
        self.tax_gen = TaxonomyGenerator()

    def compute_links(
        self,
        chunks: List[Dict[str, Any]],
        taxonomy_nodes: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """
        MAIN LINKING PROCESS:
        Takes all book chunks and taxonomy concepts, embeds them, calculates
        cross-similarities, and builds the two-way relationship maps.
        
        INPUTS:
        - chunks: List of dictionaries with book paragraphs and chunk IDs.
        - taxonomy_nodes: List of taxonomy concept dictionaries (id, name, keywords).
        
        OUTPUTS:
        - (passage_to_taxonomy, taxonomy_to_passages, triplets)
        """
        # Step 1: Ensure all current taxonomy nodes are saved and embedded in the Vector DB
        self.vector_db.save_taxonomy_nodes(taxonomy_nodes)

        # Step 2: Prepare empty containers for our two-way link maps
        # Map 1: For each passage ID, what taxonomy topics match it?
        passage_to_taxonomy = {c['chunk_id']: [] for c in chunks}
        # Map 2: For each taxonomy concept ID, what passages reference it?
        taxonomy_to_passages = {t['taxonomy_id']: [] for t in taxonomy_nodes}

        # Step 3: Loop through every chunk in the library
        for c in chunks:
            c_id = c['chunk_id']
            text = c['text']

            # Query the vector database for top matching concepts above our threshold
            matches = self.vector_db.query_similar_concepts(
                chunk_text=text,
                top_k=6,
                threshold=self.similarity_threshold
            )

            # Record each match in both directions
            for m in matches:
                # Forward link: Passage -> Concept
                passage_to_taxonomy[c_id].append({
                    "taxonomy_id": m['taxonomy_id'],
                    "taxonomy_name": m['taxonomy_name'],
                    "domain": m['domain'],
                    "depth": m['depth'],
                    "strength": m['strength']
                })

                # Reverse link: Concept -> Passage (if concept exists in our index)
                if m['taxonomy_id'] in taxonomy_to_passages:
                    taxonomy_to_passages[m['taxonomy_id']].append({
                        "chunk_id": c_id,
                        "doc_title": c.get('doc_title', 'Document'),
                        "section": c.get('section', 'Main'),
                        "snippet": text[:160] + "...",
                        "strength": m['strength']
                    })

        # Step 4: Extract grammar-based knowledge triplets (Subject -> Predicate -> Object)
        triplets = self.tax_gen.extract_semantic_triplets(chunks, taxonomy_nodes)

        # Return all three calculated link datasets
        return passage_to_taxonomy, taxonomy_to_passages, triplets
