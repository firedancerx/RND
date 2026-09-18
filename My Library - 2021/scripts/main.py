"""
===============================================================================
FILE: main.py
===============================================================================
WHAT IS THIS FILE FOR? (Intent & Big Picture)
Master Orchestrator for the Universal Knowledge Management Pipeline.

Zero Hardcoding:
All input book directories, output vault directories, vector database paths,
and API credentials are dynamically resolved via config_loader.py (config.json,
.env, or CLI flags).
===============================================================================
"""

import os
import sys
import glob
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any

# Ensure Windows terminal handles arbitrary Unicode characters in book titles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from config_loader import get_config
from chunk_chain_manager import ChunkChainManager
from vector_store import BuiltinVectorDB
from ingest_and_chunk import DocumentChunker
from generate_taxonomy import TaxonomyGenerator
from consolidate_taxonomy import GlobalTaxonomyConsolidator
from semantic_linker import SemanticLinker
from format_markdown_output import MarkdownFormatter


class TaskManager:
    def __init__(self, task_file: str):
        self.task_file = task_file
        self.chain_mgr = ChunkChainManager()
        self.tasks = self._load_tasks()

    def _load_tasks(self) -> Dict[str, Any]:
        if os.path.exists(self.task_file):
            data = self.chain_mgr.read_chained_json(self.task_file)
            if data and "books" in data:
                return data
            elif data:
                return {"books": data}
        return {"books": {}}

    def save(self):
        try:
            self.chain_mgr.write_chained_json(
                target_dir=os.path.dirname(self.task_file),
                base_filename=os.path.basename(self.task_file),
                records_dict=self.tasks.get("books", {})
            )
        except Exception as e:
            print(f"[Warning] Task registry save warning (non-fatal): {e}")

    def is_completed(self, file_path: str, file_hash: str) -> bool:
        norm_key = os.path.abspath(file_path)
        books = self.tasks.get('books', {})
        task = books.get(norm_key) or books.get(file_path)
        if task and task.get("status") == "completed":
            if task.get("file_hash") == file_hash:
                return True
        return False

    def mark_started(self, file_path: str):
        norm_key = os.path.abspath(file_path)
        if "books" not in self.tasks:
            self.tasks["books"] = {}
        self.tasks["books"][norm_key] = {
            "file_name": os.path.basename(file_path),
            "status": "in_progress",
            "started_at": datetime.now().isoformat()
        }
        self.save()

    def mark_completed(self, file_path: str, doc_id: str, file_hash: str, num_chunks: int, metadata: Dict[str, Any]):
        norm_key = os.path.abspath(file_path)
        if "books" not in self.tasks:
            self.tasks["books"] = {}
        self.tasks["books"][norm_key] = {
            "file_name": os.path.basename(file_path),
            "doc_id": doc_id,
            "file_hash": file_hash,
            "status": "completed",
            "num_chunks": num_chunks,
            "metadata": metadata,
            "completed_at": datetime.now().isoformat()
        }
        self.save()

    def mark_failed(self, file_path: str, error_msg: str):
        norm_key = os.path.abspath(file_path)
        if "books" not in self.tasks:
            self.tasks["books"] = {}
        self.tasks["books"][norm_key] = {
            "file_name": os.path.basename(file_path),
            "status": "failed",
            "error": error_msg,
            "failed_at": datetime.now().isoformat()
        }
        self.save()


def log_explicit_intent(output_dir: str, pending_files: List[str], max_books: int) -> str:
    intents_dir = os.path.join(output_dir, "intents")
    os.makedirs(intents_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"intent_{timestamp}.md"
    path = os.path.join(intents_dir, filename)

    lines = [
        f"# Explicit Knowledge Management Intent: Batch {timestamp}\n",
        "> 📋 **Pre-Execution Intent Declaration** before mutating task registries and ontologies.\n",
        "---\n",
        f"- **Planned Batch Size**: `{len(pending_files)}` books (Max Limit: `{max_books}`)",
        f"- **Execution Timestamp**: `{datetime.now().isoformat()}`",
        "- **Transformation Objectives**:",
        "  1. Ingest documents with full bibliographic metadata & SHA-256 versioning.",
        "  2. Embed chunks into Built-in SQLite Vector Database.",
        "  3. Consolidate deep multi-tier taxonomy directly into `Master Taxonomy Markdown`.",
        "  4. Cross-link passages with dense Wikilinks and extract Semantic Triplets.",
        "  5. Synthesize Executive Summaries and preserve User Annotations.\n",
        "## Target Documents in this Batch:\n"
    ]
    for gfile in pending_files:
        lines.append(f"- `{os.path.basename(gfile)}`")

    lines.append("\n---\n")
    with open(path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"[Intent] Logged explicit intent record at: {path}")
    return path


def run_pipeline(
    input_dir: str = None,
    output_dir: str = None,
    threshold: float = None,
    max_books: int = None,
    force_reprocess: bool = False
):
    cfg = get_config()
    input_dir = input_dir or cfg["input_dir"]
    output_dir = output_dir or cfg["output_vault_dir"]
    threshold = threshold if threshold is not None else cfg["similarity_threshold"]
    max_books = max_books if max_books is not None else cfg["max_books_per_batch"]

    print("=" * 75)
    print("STARTING ENHANCED UNIVERSAL KM & SEMANTIC TAXONOMY PIPELINE")
    print("=" * 75)
    print(f"Input Directory  : {input_dir}")
    print(f"Output Vault Dir : {output_dir}")
    print(f"Dense Threshold  : {threshold}")
    print(f"Max Books / Run  : {max_books}")

    os.makedirs(output_dir, exist_ok=True)
    vector_db = BuiltinVectorDB(db_path=cfg.get("vector_db_path", os.path.join(output_dir, "vector_store", "vector_store.sqlite")))
    task_file = os.path.join(output_dir, "task_list.json")
    task_manager = TaskManager(task_file)
    chunker = DocumentChunker(target_chunk_size=cfg.get("chunk_size_words", 400), overlap=cfg.get("chunk_overlap_words", 50))

    IGNORE_DIRS = {
        '.git', '__pycache__', 'output_taxonomy', 'vector_store',
        'indices', 'summaries', 'triplets', 'notes', 'intents', '.obsidian', 'node_modules'
    }

    print(f"\n[Step 1/5] Scanning task queue and library recursively...")

    pending = []
    seen = set()

    # Check existing pending tasks in task_list.json first
    for fpath, info in task_manager.tasks.get("books", {}).items():
        if info.get("status") == "pending" or force_reprocess:
            if os.path.exists(fpath) and fpath not in seen:
                seen.add(fpath)
                pending.append(fpath)
                if max_books > 0 and len(pending) >= max_books:
                    break

    # Recursively scan input directories if quota remains
    if max_books == 0 or len(pending) < max_books:
        scan_roots = [input_dir]
        if cfg.get("secondary_vault_dirs"):
            scan_roots.extend(cfg["secondary_vault_dirs"])

        for root in scan_roots:
            if not os.path.exists(root):
                continue
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [d for d in dirnames if d.lower() not in IGNORE_DIRS and not d.startswith('.')]
                for f in filenames:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in ('.pdf', '.epub', '.txt', '.md'):
                        fpath = os.path.normpath(os.path.join(dirpath, f))
                        if fpath not in seen:
                            seen.add(fpath)
                            fhash = chunker.get_file_hash(fpath)
                            if force_reprocess or not task_manager.is_completed(fpath, fhash):
                                pending.append(fpath)
                                if max_books > 0 and len(pending) >= max_books:
                                    break
                if max_books > 0 and len(pending) >= max_books:
                    break

    print(f" -> Found {len(pending)} files pending processing in this batch.")

    if not pending and not force_reprocess:
        print("All books are up to date and fully processed according to task_list.json!")
        return

    log_explicit_intent(output_dir, pending, max_books)

    all_chunks = []
    doc_chunks_map = {}

    print(f"\n[Step 2/5] Ingesting & Embedding {len(pending)} books...")
    for f in pending:
        base = os.path.basename(f)
        print(f" -> Ingesting: {base}")
        task_manager.mark_started(f)
        try:
            chunks, meta = chunker.process_file(f)
            if chunks:
                doc_id = chunks[0]['doc_id']
                all_chunks.extend(chunks)
                doc_chunks_map[doc_id] = {
                    "title": base,
                    "metadata": meta,
                    "chunks": chunks
                }
                vector_db.save_document_chunks(doc_id, base, meta, chunks)
                task_manager.mark_completed(f, doc_id, meta['file_hash'], len(chunks), meta)
            else:
                task_manager.mark_failed(f, "No text extracted")
        except Exception as e:
            print(f"    [Error] Runtime issue on {base}: {e}")
            task_manager.mark_failed(f, str(e))

    if not all_chunks:
        print("No active chunks extracted. Exiting.")
        return

    print(f"\n[Step 3/5] Extracting Concepts & Consolidating Master Taxonomy Markdown...")
    tax_gen = TaxonomyGenerator(do_agent_id=cfg.get("do_agent_id"))
    candidates = tax_gen.extract_multi_ngrams(all_chunks, top_n=60)

    consolidator = GlobalTaxonomyConsolidator(output_dir)
    master_taxonomy = consolidator.consolidate_delta_hierarchy(
        new_candidates=candidates,
        doc_titles=[d.get('title', '') for d in doc_chunks_map.values()]
    )

    flat_taxonomy_nodes = []
    for dom in master_taxonomy.get("hierarchy", []):
        flat_taxonomy_nodes.extend(dom.get("concept_nodes", []))

    print(f"\n[Step 4/5] Dense Vector Cross-Linking & Semantic Triplet Extraction...")
    linker = SemanticLinker(similarity_threshold=threshold, vector_db=vector_db)
    p, t, triplets = linker.compute_links(all_chunks, flat_taxonomy_nodes)

    print(f"\n[Step 5/5] Rendering Densely Wikilinked Markdown, Triplets, Yellow Pages, & Executive Summaries...")
    formatter = MarkdownFormatter(output_dir)

    for doc_id, data in doc_chunks_map.items():
        user_notes = vector_db.get_user_notes(doc_id)
        formatter.generate_document_markdown(
            doc_id=doc_id,
            doc_title=data['title'],
            chunks=data['chunks'],
            passage_links=p,
            taxonomy_nodes=flat_taxonomy_nodes,
            metadata=data['metadata'],
            user_notes=user_notes
        )

        matches = vector_db.query_similar_concepts(data['chunks'][0]['text'], top_k=8, threshold=0.20)
        formatter.generate_executive_summary(doc_id, data['title'], data['chunks'], matches)

    formatter.generate_semantic_triplets_md(triplets)
    formatter.generate_taxonomy_yellow_pages(master_taxonomy, t)

    summary_path = os.path.join(output_dir, "pipeline_summary.json")
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            "updated_at": datetime.now().isoformat(),
            "total_books_in_queue": len(task_manager.tasks.get('books', {})),
            "total_chunks_processed": len(all_chunks),
            "total_domains": master_taxonomy.get('total_domains', 0),
            "total_concept_nodes": len(flat_taxonomy_nodes),
            "total_semantic_triplets": len(triplets)
        }, f, indent=2)

    print("\n" + "=" * 75)
    print(f"PIPELINE COMPLETED! Master Taxonomy & Yellow Pages persisted at: {output_dir}/indices/")
    print("=" * 75)


if __name__ == "__main__":
    cfg = get_config()
    parser = argparse.ArgumentParser(description="Enhanced KM Taxonomy & Embeddings Pipeline")
    parser.add_argument("--input-dir", type=str, default=cfg["input_dir"], help="Input books directory")
    parser.add_argument("--output-dir", type=str, default=cfg["output_vault_dir"], help="Output vault directory")
    parser.add_argument("--threshold", type=float, default=cfg["similarity_threshold"], help="Dense similarity threshold")
    parser.add_argument("--max-books", type=int, default=cfg["max_books_per_batch"], help="Max books per run")
    parser.add_argument("--force", action="store_true", help="Force reprocessing of completed books")
    args = parser.parse_args()

    run_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        threshold=args.threshold,
        max_books=args.max_books,
        force_reprocess=args.force
    )
