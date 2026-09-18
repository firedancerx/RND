# 06. Component & API Reference

## 1. Module Catalog

| Module | Primary Class / Function | Purpose |
| :--- | :--- | :--- |
| [`scripts/chunk_chain_manager.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/chunk_chain_manager.py) | `ChunkChainManager` | Markdown and JSON pagination and breadcrumb chaining. |
| [`scripts/vector_store.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/vector_store.py) | `BuiltinVectorDB`, `DenseEmbeddingEngine` | Embedded SQLite vector database & 256-dim embedding math. |
| [`scripts/ingest_and_chunk.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/ingest_and_chunk.py) | `DocumentChunker` | PDF/EPUB/TXT extraction & 400-word atomic chunking. |
| [`scripts/generate_taxonomy.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/generate_taxonomy.py) | `TaxonomyGenerator` | Multi-ngram term discovery, LLM API client, & semantic triples. |
| [`scripts/consolidate_taxonomy.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/consolidate_taxonomy.py) | `GlobalTaxonomyConsolidator` | 6-domain taxonomy hierarchy & `master_taxonomy.md` writer. |
| [`scripts/semantic_linker.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/semantic_linker.py) | `SemanticLinker` | Two-way vector cross-linker (Passage $\leftrightarrow$ Concept). |
| [`scripts/format_markdown_output.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/format_markdown_output.py) | `MarkdownFormatter` | Obsidian `[[Wikilinks]]`, footnotes, Executive Summaries, Yellow Pages. |
| [`scripts/taxonomy_hygiene.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/taxonomy_hygiene.py) | `TaxonomyHygieneAuditor` | Audit tool measuring network density & orphan concepts. |
| [`scripts/main.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/main.py) | `TaskManager`, `run_pipeline` | Master 5-step pipeline coordinator & intent logger. |
| [`scripts/watch_folder.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/watch_folder.py) | `monitor_folder` | Live background directory watcher daemon. |
| [`scripts/add_all_to_queue.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/add_all_to_queue.py) | Top-level script | One-shot scanner registering all books into `task_list.json`. |

---

## 2. Key Class Specifications

### `DenseEmbeddingEngine` (`vector_store.py`)
- `compute_dense_vector(text: str, dim: int = 256) -> np.ndarray`: Computes normalized 256-dim embedding vector.
- `cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float`: Calculates dot product similarity between two unit vectors.

### `BuiltinVectorDB` (`vector_store.py`)
- `save_document_chunks(doc_id, doc_title, metadata, chunks)`: Inserts chunks and BLOB vectors into SQLite.
- `save_taxonomy_nodes(taxonomy_nodes)`: Inserts taxonomy concepts and embeddings into SQLite.
- `query_similar_concepts(chunk_text, top_k=6, threshold=0.25)`: Returns top matching concepts exceeding the similarity threshold.
- `save_user_note(doc_id, content, chunk_id=None)`: Stores tacit reflection notes.
- `get_user_notes(doc_id)`: Retrieves all user notes attached to a document.

### `GlobalTaxonomyConsolidator` (`consolidate_taxonomy.py`)
- `consolidate_delta_hierarchy(new_candidates, doc_titles)`: Merges new candidate terms into 6-domain hierarchy and deprecates outdated concepts.
- `write_master_taxonomy_markdown(master_data)`: Persists hierarchy exclusively into `output_taxonomy/indices/master_taxonomy.md`.

### `MarkdownFormatter` (`format_markdown_output.py`)
- `generate_document_markdown(doc_id, doc_title, chunks, passage_links, taxonomy_nodes, metadata, user_notes)`: Renders chained document pages with multi-word `[[Wikilinks]]` and footnotes.
- `generate_semantic_triplets_md(triplets)`: Writes Knowledge Graph Triples registry.
- `generate_executive_summary(doc_id, doc_title, chunks, taxonomy_matches)`: Synthesizes executive summary and core principles.
- `generate_taxonomy_yellow_pages(master_data, taxonomy_to_passages)`: Writes Yellow Pages index.
