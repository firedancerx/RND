"""
===============================================================================
FILE: watch_folder.py
===============================================================================
Folder watcher service that monitors the input library directory for newly added books
and registers them into task_list.json using dynamic configuration.
===============================================================================
"""

import os
import sys
import time
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
    supported_files = []
    if not os.path.exists(root_dir):
        return supported_files

    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d.lower() not in IGNORE_DIRS and not d.startswith('.')]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in ('.pdf', '.epub', '.txt', '.md'):
                supported_files.append(os.path.normpath(os.path.join(dirpath, f)))

    return supported_files

def monitor_folder(
    watch_dir: str = None,
    task_file: str = None,
    check_interval_seconds: int = None,
    auto_process: bool = True
):
    cfg = get_config()
    watch_dir = watch_dir or cfg["input_dir"]
    output_dir = cfg["output_vault_dir"]
    task_file = task_file or os.path.join(output_dir, "task_list.json")
    check_interval_seconds = check_interval_seconds or cfg.get("folder_watch_interval_seconds", 5)

    print("=" * 70)
    print(f"STARTING RECURSIVE FOLDER WATCHER FOR: {watch_dir}")
    print(f"Task List File: {task_file}")
    print(f"Auto-process Pipeline: {auto_process}")
    print(f"Checking every {check_interval_seconds} seconds for new books...")
    print("=" * 70)

    os.makedirs(os.path.dirname(task_file), exist_ok=True)

    # Lazily import main runner if auto-process is requested
    run_pipeline = None
    if auto_process:
        try:
            from main import run_pipeline
        except ImportError:
            pass

    while True:
        try:
            tasks = {"books": {}}
            if os.path.exists(task_file):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        tasks = json.load(f)
                except Exception as e:
                    print(f"Error loading {task_file}: {e}")

            if "books" not in tasks:
                tasks["books"] = {}

            scan_targets = [watch_dir]
            if cfg.get("secondary_vault_dirs"):
                scan_targets.extend(cfg["secondary_vault_dirs"])

            all_supported = []
            for target in list(dict.fromkeys(scan_targets)):
                all_supported.extend(scan_supported_files(target))

            all_supported = list(dict.fromkeys(all_supported))

            new_count = 0
            for file_path in all_supported:
                norm_path = os.path.normpath(file_path)
                if norm_path not in tasks["books"]:
                    tasks["books"][norm_path] = {
                        "file_name": os.path.basename(norm_path),
                        "status": "pending",
                        "detected_at": datetime.now().isoformat()
                    }
                    new_count += 1
                    print(f" [NEW BOOK DETECTED] -> Added to queue: {os.path.basename(norm_path)}")

            if new_count > 0:
                with open(task_file, 'w', encoding='utf-8') as f:
                    json.dump(tasks, f, indent=2)
                print(f"Updated {task_file} with {new_count} new pending books.")

            # Check if any tasks are in 'pending' status
            pending_count = sum(1 for b in tasks["books"].values() if b.get("status") == "pending")
            if pending_count > 0 and auto_process and run_pipeline:
                print(f"\n[Watcher Worker] Found {pending_count} pending books. Triggering batch run...")
                run_pipeline(
                    input_dir=watch_dir,
                    output_dir=output_dir,
                    max_books=cfg.get("max_books_per_batch", 20)
                )

        except Exception as e:
            print(f"Watcher error: {e}")

        time.sleep(check_interval_seconds)


if __name__ == "__main__":
    cfg = get_config()
    parser = argparse.ArgumentParser(description="Recursive Folder Watcher & Background Pipeline Worker")
    parser.add_argument("--watch-dir", type=str, default=cfg["input_dir"], help="Target library directory to monitor")
    parser.add_argument("--interval", type=int, default=cfg.get("folder_watch_interval_seconds", 5), help="Check interval in seconds")
    parser.add_argument("--auto-process", action="store_true", default=False, help="Automatically process pending tasks in background")
    args = parser.parse_args()

    task_json = os.path.join(cfg["output_vault_dir"], "task_list.json")
    monitor_folder(
        watch_dir=args.watch_dir,
        task_file=task_json,
        check_interval_seconds=args.interval,
        auto_process=args.auto_process
    )

