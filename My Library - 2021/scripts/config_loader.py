"""
===============================================================================
FILE: config_loader.py
===============================================================================
WHAT IS THIS FILE FOR? (Intent & Big Picture)
No directory paths, database locations, API keys, or vault paths should ever
be hardcoded! Different machines, different users, or different library vaults
(e.g., "My Library - 2021", "My Library - 2025", or custom Obsidian Vaults)
might have different storage paths.

This module is the Central Configuration Hub. It loads and merges settings from:
1. System Environment Variables (e.g. KM_OUTPUT_VAULT_DIR, KM_INPUT_DIR)
2. `.env` file (if present)
3. `config.json` configuration file
4. Safe, relative fallback defaults

Every script in the system imports `get_config()` from this module to dynamically
resolve directory paths, vector database paths, and API parameters.
===============================================================================
"""

import os
import json
from typing import Dict, Any

_CACHED_CONFIG = None


def load_env_file(env_path: str):
    """Loads key-value pairs from a .env file into os.environ if not already set."""
    if os.path.exists(env_path):
        try:
            with open(env_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k not in os.environ:
                            os.environ[k] = v
        except Exception:
            pass


def get_config(config_path: str = None) -> Dict[str, Any]:
    """
    Returns the resolved configuration dictionary with zero hardcoded paths.
    """
    global _CACHED_CONFIG
    if _CACHED_CONFIG is not None and config_path is None:
        return _CACHED_CONFIG

    # Determine project root directory dynamically
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) if os.path.basename(script_dir) == "scripts" else script_dir

    # 1. Load .env if present
    load_env_file(os.path.join(project_root, ".env"))

    # 2. Base defaults (dynamic relative paths)
    default_config = {
        "input_dir": project_root,
        "output_vault_dir": os.path.join(project_root, "output_taxonomy"),
        "secondary_vault_dirs": [],
        "vector_db_path": os.path.join(project_root, "output_taxonomy", "vector_store", "vector_store.sqlite"),
        "similarity_threshold": 0.25,
        "max_books_per_batch": 50,
        "chunk_size_words": 400,
        "chunk_overlap_words": 50,
        "do_agent_id": "d139564c-a122-11f1-aee4-4e013e2ddde4",
        "folder_watch_interval_seconds": 5
    }

    # 3. Merge config.json if present
    cfg_file = config_path or os.path.join(project_root, "config.json")
    if os.path.exists(cfg_file):
        try:
            with open(cfg_file, 'r', encoding='utf-8') as f:
                file_cfg = json.load(f)
                default_config.update(file_cfg)
        except Exception as e:
            print(f"[Warning] Could not read {cfg_file}: {e}")

    # 4. Environment variable overrides (highest precedence)
    if "KM_INPUT_DIR" in os.environ:
        default_config["input_dir"] = os.environ["KM_INPUT_DIR"]
    if "KM_OUTPUT_VAULT_DIR" in os.environ:
        default_config["output_vault_dir"] = os.environ["KM_OUTPUT_VAULT_DIR"]
    if "KM_VECTOR_DB_PATH" in os.environ:
        default_config["vector_db_path"] = os.environ["KM_VECTOR_DB_PATH"]
    if "KM_SIMILARITY_THRESHOLD" in os.environ:
        try:
            default_config["similarity_threshold"] = float(os.environ["KM_SIMILARITY_THRESHOLD"])
        except ValueError:
            pass
    if "KM_MAX_BOOKS" in os.environ:
        try:
            default_config["max_books_per_batch"] = int(os.environ["KM_MAX_BOOKS"])
        except ValueError:
            pass
    if "DO_AGENT_ID" in os.environ:
        default_config["do_agent_id"] = os.environ["DO_AGENT_ID"]
    if "KM_WATCH_INTERVAL" in os.environ:
        try:
            default_config["folder_watch_interval_seconds"] = int(os.environ["KM_WATCH_INTERVAL"])
        except ValueError:
            pass

    _CACHED_CONFIG = default_config
    return default_config
