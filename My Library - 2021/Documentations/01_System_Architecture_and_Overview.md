# 01. System Architecture & Overview

## 1. Executive Summary
The **Universal Knowledge Management & Semantic Taxonomy Ingestion System** is an enterprise-grade, offline-first digital library processing platform. It ingests heterogenous document collections (PDF, EPUB, TXT, MD), computes mathematical semantic embeddings, discovers multi-word technical concepts, organizes a dynamic 6-domain ontology, and generates Obsidian-ready chained Markdown files enriched with multi-word `[[Wikilinks]]`, academic footnotes, AI Executive Summaries, and an Ontology Yellow Pages directory.

---

## 2. High-Resolution Architectural Schematic

![System Architecture Schematic](./images/system_architecture_schematic.jpg)

---

## 3. Technology Stack & Component Catalog

The system integrates local embedded engines with secure cloud generative AI services:

| Component Tier | Software / Library | Version | Role & Technical Responsibility |
| :--- | :--- | :--- | :--- |
| **Runtime Environment** | **Python (CPython)** | `v3.14.7` | Core script execution, multithreading, and process coordination. |
| **Document Parser** | **PyMuPDF (`fitz`)** | `v1.25.x` | High-fidelity PDF layout analysis, clean text stream extraction, and document metadata reading. |
| **EPUB Parser** | **`ebooklib`** | `v0.18` | EPUB container parsing, HTML item traversal, and spine extraction. |
| **HTML Sanitizer** | **`beautifulsoup4`** | `v4.13.x` | Strips script, style, and navigation noise from EPUB XHTML passages. |
| **Math & Embeddings** | **`numpy`** | `v2.2.x` | Vector normalization, linear algebra, and fast array-level cosine similarity computation. |
| **Local Storage & Vector DB** | **`sqlite3` Engine** | `v3.45.x` | Embedded relational and dense vector storage (`vector_store.sqlite`) with BLOB vector persistence. |
| **Cloud GenAI Agent** | **DigitalOcean Serverless GenAI** | `DO-Agent-v1` (`d139564c-a122-11f1-aee4-4e013e2ddde4`) | Cloud-hosted LLM agent endpoint for Executive Summaries and Core Principle synthesis. |
| **File System Watcher** | **Standard Library (`glob`, `time`)** | Built-in | Continuous polling daemon monitoring incoming library additions every 5 seconds. |
| **Windows Automation** | **PowerShell & WScript.Shell COM** | `PS 5.1+` | Automatic desktop shortcut `.lnk` creation and Windows shell icon binding. |

---

## 4. Architectural Layers & Data Flow Topology

### Layer 1: Input Ingestion Layer
- **Source Documents**: Scans the root library directory for `.pdf`, `.epub`, `.txt`, and `.md` files.
- **SHA-256 Hashing**: Calculates cryptographic hash fingerprints of every input file to ensure idempotency and prevent redundant reprocessing.
- **Atomic Passage Chunking**: Slices documents into 400-word atomic chunks with a 50-word sliding overlap to preserve cross-boundary context.

### Layer 2: Local Vector Database & Storage Layer
- **Dense Embedding Engine**: Generates 256-dimensional semantic dense vectors using a deterministically hashed token frequency algorithm.
- **SQLite Vector Store**: Persists document passages, metadata, taxonomy nodes, and user reflection notes in `output_taxonomy/vector_store/vector_store.sqlite`.
- **Cosine Similarity Engine**: Computes high-dimensional vector alignment scores between text chunks and taxonomy concepts.

### Layer 3: Taxonomy & Ontology Consolidation Layer
- **Multi-Ngram Phrase Extractor**: Extracts 1-gram, 2-gram, 3-gram, and 4-gram domain terminology candidates from book text.
- **Dynamic 6-Domain Hierarchy**: Organizes all concepts under 6 broad root domains:
  1. `DOM_ACC_FIN`: Financial & Management Accounting
  2. `DOM_BUS_MGT`: Business Administration & Leadership
  3. `DOM_PSY_BEH`: Psychological Science & Behavioral Economics
  4. `DOM_TECH_AI`: Artificial Intelligence & Information Systems
  5. `DOM_PHIL_HIST`: Philosophy, History & Humanistic Governance
  6. `DOM_LIT_ARTS`: Creative Arts, Literature & Musicology
- **Deprecation Catalog**: Evaluates concept longevity and archives inactive nodes with percentage-point confidence scoring into `deprecated_taxonomy.md`.

### Layer 4: Cloud Generative AI Layer
- **DigitalOcean Serverless GenAI Agent**: Communicates over secure HTTPS (`urllib.request`) with timeout fallbacks to synthesize executive-level chapter briefs and 5 foundational heuristics.

### Layer 5: Semantic Linking & Triplet Extraction Layer
- **Bi-Directional Indexing**: Maps passages to concepts (`passage_to_taxonomy`) and concepts to all referencing library passages (`taxonomy_to_passages`).
- **Semantic Triplets Registry**: Discovers Subject-Predicate-Object triples (e.g. `[[Cash Flow]]` -- `evaluates` --> `[[Liquidity]]`) linked to source passages.

### Layer 6: Output Knowledge Ecosystem Layer
- **Universal Chained Markdown**: Writes paginated `.md` documents with breadcrumb navigation headers (`[<< Previous] | [Master Index] | [Next >>]`).
- **Dense Wikilinking**: Enriches text with Obsidian-compatible `[[Concept Name|Text]]` links and academic footnotes.
- **Master Taxonomy**: Persisted exclusively in clean Markdown (`output_taxonomy/indices/master_taxonomy.md`).
- **Ontology Yellow Pages**: Directory listing concept depth, occurrences, and top corpus links (`output_taxonomy/indices/taxonomy_yellow_pages.md`).
