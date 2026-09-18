# 03. Pipeline Execution Flow & Data Lifecycle

## 1. Overview
The ingestion pipeline follows a strict, deterministic 5-phase data lifecycle orchestrated by [`scripts/main.py`](file:///d:/Firedancerx/OneDrive/My%20Library%20-%202021/scripts/main.py).

```
   Raw Document Files (.pdf, .epub, .txt, .md)
                       │
                       ▼
       ┌───────────────────────────────┐
       │ Step 1: Scan, Hash & Queue    │ ──► output_taxonomy/task_list.json
       └───────────────────────────────┘ ──► output_taxonomy/intents/intent_*.md
                       │
                       ▼
       ┌───────────────────────────────┐
       │ Step 2: Ingest, Chunk & Embed │ ──► output_taxonomy/vector_store/vector_store.sqlite
       └───────────────────────────────┘
                       │
                       ▼
       ┌───────────────────────────────┐
       │ Step 3: Consolidate Taxonomy  │ ──► output_taxonomy/indices/master_taxonomy.md
       └───────────────────────────────┘ ──► output_taxonomy/indices/deprecated_taxonomy.md
                       │
                       ▼
       ┌───────────────────────────────┐
       │ Step 4: Semantic Cross-Link   │ ──► Bi-Directional Passage <-> Concept Maps
       └───────────────────────────────┘ ──► Semantic Triplets Extractor
                       │
                       ▼
       ┌───────────────────────────────┐
       │ Step 5: Render Markdown Pages │ ──► output_taxonomy/documents/*.md
       └───────────────────────────────┘ ──► output_taxonomy/triplets/semantic_triplets.md
                                         ──► output_taxonomy/summaries/*_summary.md
                                         ──► output_taxonomy/indices/taxonomy_yellow_pages.md
```

---

## 2. Detailed Step-by-Step Breakdown

### Step 1: Library Scanning, SHA-256 Hashing & Intent Declaration
1. Scans the root folder for supported file types (`.pdf`, `.epub`, `.txt`, `.md`).
2. Calculates the cryptographic SHA-256 hash of each file.
3. Consults `output_taxonomy/task_list.json` to verify completion status.
4. Generates an explicit Intent Declaration Markdown document in `output_taxonomy/intents/`.

### Step 2: Document Ingestion, Atomic Chunking & Vector Embedding
1. **PyMuPDF (`fitz`) / `ebooklib`**: Extracts clean text, removes formatting noise, headers, footers, and page numbers.
2. **Atomic Chunking**: Splits text into 400-word atomic passages with a 50-word sliding overlap.
3. **Dense Vector Computation**: Calculates 256-dimensional semantic vectors for every chunk.
4. **Persistence**: Commits chunks, metadata, and embeddings to `output_taxonomy/vector_store/vector_store.sqlite`.

### Step 3: Multi-Ngram Extraction & Master Taxonomy Consolidation
1. Extracts frequent 1-gram, 2-gram, 3-gram, and 4-gram domain terminology candidates.
2. Evaluates existing Master Taxonomy (`master_taxonomy.md`) for incremental delta merges.
3. Assigns discovered concepts into the 6-domain hierarchy.
4. Deprecates outdated or orphaned concept nodes, writing accuracy scores into `deprecated_taxonomy.md`.

### Step 4: Bi-Directional Semantic Cross-Linking & Triplet Extraction
1. Computes cosine similarity between document chunks and taxonomy nodes.
2. Builds two-way link indices (`passage_to_taxonomy` and `taxonomy_to_passages`).
3. Extracts Subject-Predicate-Object knowledge graph triples from passage sentences.

### Step 5: Markdown Rendering, AI Summaries & Yellow Pages
1. Formats document pages with breadcrumb navigation and frontmatter metadata.
2. Regex-replaces taxonomy technical terms with `[[Concept Name|Matched Word]]` wikilinks (longest phrases first).
3. Adds academic footnotes containing domain depth and cosine similarity scores.
4. Preserves user reflection notes in `# 📝 User Annotations`.
5. Prompts the DigitalOcean Serverless GenAI Agent for Executive Summaries and 5 Core Principles.
6. Writes the Ontology Yellow Pages directory.
