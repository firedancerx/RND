"""
===============================================================================
FILE: add_all_to_queue.py
===============================================================================
One-shot library scanner utility that registers all unindexed books into task_list.json
using dynamic configuration paths.
===============================================================================
"""

import os
import sys
import glob
import json
import argparse
from datetime import datetime

# Ensure Windows terminal handles arbitrary Unicode characters
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
from config_loader import get_config

IGNORE_DIRS = {
    '.git', '__pycache__', 'output_taxonomy', 'vector_store',
    'indices', 'summaries', 'triplets', 'notes', 'intents', '.obsidian', 'node_modules'
}

def scan_supported_files(root_dir: str) -> list:
    """Recursively scans directory for supported book and markdown files."""
    supported_files = []
    if not os.path.exists(root_dir):
        return supported_files

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Modify dirnames in-place to skip ignored directories
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORE_DIRS and not d.startswith('.')]
        
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.pdf', '.epub', '.txt', '.md'):
                supported_files.append(os.path.normpath(os.path.join(dirpath, f)))

    return supported_files

def populate_queue(reset_all_to_pending: bool = False, extra_dirs: list = None):
    cfg = get_config()
    primary_input = os.path.abspath(cfg["input_dir"])
    output_dir = os.path.abspath(cfg["output_vault_dir"])
    os.makedirs(output_dir, exist_ok=True)

    task_file = os.path.join(output_dir, "task_list.json")

    tasks = {"books": {}}
    if os.path.exists(task_file):
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
        except Exception as e:
            print(f"Loading existing task file note: {e}")

    if "books" not in tasks:
        tasks["books"] = {}

    scan_targets = [primary_input]
    if extra_dirs:
        scan_targets.extend(extra_dirs)
    if cfg.get("secondary_vault_dirs"):
        scan_targets.extend(cfg["secondary_vault_dirs"])

    # Remove duplicates
    scan_targets = list(dict.fromkeys(os.path.abspath(d) for d in scan_targets if os.path.exists(d)))

    all_files = []
    for target in scan_targets:
        print(f"Recursively scanning target directory: {target}")
        found = scan_supported_files(target)
        print(f" -> Discovered {len(found)} supported files in {target}")
        all_files.extend(found)

    # De-duplicate file list
    all_files = list(dict.fromkeys(all_files))

    added_count = 0
    reset_count = 0

    for file_path in all_files:
        norm_path = os.path.normpath(file_path)
        if norm_path not in tasks["books"]:
            tasks["books"][norm_path] = {
                "file_name": os.path.basename(norm_path),
                "status": "pending",
                "added_at": datetime.now().isoformat()
            }
            added_count += 1
        elif reset_all_to_pending:
            tasks["books"][norm_path]["status"] = "pending"
            tasks["books"][norm_path]["requeued_at"] = datetime.now().isoformat()
            reset_count += 1

    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, indent=2)

    print("\n" + "=" * 65)
    print(f"TASK QUEUE UPDATE COMPLETE:")
    print(f"  Target File: {task_file}")
    print(f"  New Books Added    : {added_count}")
    if reset_all_to_pending:
        print(f"  Re-queued for Re-run: {reset_count}")
    print(f"  Total Books in Queue: {len(tasks['books'])}")
    print("=" * 65)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Recursively scan library files and populate task_list.json")
    parser.add_argument("--reset-all", action="store_true", help="Reset all files to pending for a complete re-run")
    parser.add_argument("--extra-dir", action="append", help="Additional directories to scan recursively")
    args = parser.parse_args()

    populate_queue(reset_all_to_pending=args.reset_all, extra_dirs=args.extra_dir)

