"""
===============================================================================
FILE: diagnose_services.py
===============================================================================
Diagnostic and self-healing tool for Windows background processes, database locks,
and toast notifications with dynamic configuration resolution.
===============================================================================
"""

import os
import sys
import subprocess
import sqlite3
import json
from datetime import datetime
from config_loader import get_config

cfg = get_config()
LIBRARY_DIR = os.path.abspath(cfg["input_dir"])
OUTPUT_DIR = os.path.abspath(cfg["output_vault_dir"])
DB_PATH = cfg.get("vector_db_path", os.path.join(OUTPUT_DIR, "vector_store", "vector_store.sqlite"))
TASK_PATH = os.path.join(OUTPUT_DIR, "task_list.json")


def run_diagnostics():
    print("=" * 70)
    print("  WINDOWS BACKGROUND SERVICES & NOTIFICATIONS DIAGNOSTIC SUITE")
    print("=" * 70)
    print(f"Input Library Dir : {LIBRARY_DIR}")
    print(f"Output Vault Dir  : {OUTPUT_DIR}")
    print(f"Vector Database   : {DB_PATH}")
    print(f"Timestamp         : {datetime.now().isoformat()}\n")

    print("[1/4] Checking Running Background Processes...")
    try:
        proc_output = subprocess.check_output('tasklist /FI "IMAGENAME eq python*"', shell=True, text=True)
        print(proc_output.strip())
    except Exception as e:
        print(f"      [Warning] Could not inspect process table: {e}")

    print("\n[2/4] Checking SQLite Vector Store & Journal Locks...")
    if os.path.exists(DB_PATH):
        wal_path = DB_PATH + "-wal"
        shm_path = DB_PATH + "-shm"
        wal_exists = os.path.exists(wal_path)
        shm_exists = os.path.exists(shm_path)
        print(f"      Database File: {os.path.basename(DB_PATH)} (Found, {os.path.getsize(DB_PATH):,} bytes)")
        print(f"      Active WAL Journal: {'YES (Active Locks)' if wal_exists else 'NO (Clean)'}")
        print(f"      Shared Memory SHM : {'YES' if shm_exists else 'NO'}")

        try:
            conn = sqlite3.connect(DB_PATH, timeout=3.0)
            res = conn.execute("PRAGMA integrity_check;").fetchall()
            print(f"      SQLite Integrity Check: {res[0][0] if res else 'OK'}")
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"      [ERROR] Database is LOCKED: {e}")
    else:
        print(f"      Database not yet created at: {DB_PATH}")

    print("\n[3/4] Checking Ingestion Task Queue...")
    if os.path.exists(TASK_PATH):
        try:
            with open(TASK_PATH, 'r', encoding='utf-8') as f:
                tdata = json.load(f)
            books = tdata.get("books", {})
            pending = sum(1 for b in books.values() if b.get("status") == "pending")
            completed = sum(1 for b in books.values() if b.get("status") == "completed")
            failed = sum(1 for b in books.values() if b.get("status") == "failed")
            print(f"      Total Books Registered: {len(books)}")
            print(f"      - Pending   : {pending}")
            print(f"      - Completed : {completed}")
            print(f"      - Failed    : {failed}")
        except Exception as e:
            print(f"      [Error] Could not parse {TASK_PATH}: {e}")
    else:
        print(f"      Task list not found at: {TASK_PATH}")

    print("\n[4/4] Testing Windows Toast Notification Subsystem...")
    ps_toast_cmd = (
        "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null; "
        "$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
        "$textNodes = $template.GetElementsByTagName('text'); "
        "$textNodes.Item(0).AppendChild($template.CreateTextNode('KM Library System - Diagnostic Test')) | Out-Null; "
        "$textNodes.Item(1).AppendChild($template.CreateTextNode('Windows Toast Notification is 100% OPERATIONAL!')) | Out-Null; "
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Windows PowerShell').Show($toast);"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_toast_cmd], check=True)
        print("      [SUCCESS] Dispatched test toast notification to Windows Action Center!")
    except Exception as e:
        print(f"      [FAILED] Toast notification error: {e}")

    print("\n" + "=" * 70)
    print("  DIAGNOSTICS COMPLETED!")
    print("=" * 70)


if __name__ == "__main__":
    run_diagnostics()
