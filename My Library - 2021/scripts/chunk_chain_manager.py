"""
===============================================================================
FILE: chunk_chain_manager.py
===============================================================================
WHAT IS THIS FILE FOR? (THE INTENT):
Imagine you are reading a 500-page textbook. If you tried to fit the entire book
onto one single giant sheet of paper, it would be too heavy to hold, hard to read,
and your computer would freeze trying to open it!

This file is our "Smart Book Binder". It takes huge Markdown (.md) documents and
massive JSON (.json) task lists and neatly chops them into bite-sized chapters
(called "parts"). Even better, it glues "Previous Part" and "Next Part" buttons
(breadcrumbs) at the top and bottom of each piece so you never get lost.

HOW IT WORKS IN SIMPLE TERMS:
1. Markdown Chaining:
   - Takes a list of text lines.
   - If the text is short enough (under our line limit, e.g., 350 lines), it saves
     it as a single normal file (like `my_document.md`).
   - If it is too long, it splits the text at natural headings (like `## Chapter 2`)
     and saves them as `my_document_part001.md`, `my_document_part002.md`, etc.
   - It inserts a navigation bar so readers can click back and forth between parts.

2. JSON Chaining:
   - Takes a dictionary with thousands of records (e.g. 500 books).
   - If it exceeds our limit (e.g., 250 items per file), it shards the dictionary
     into `task_list_part001.json`, `task_list_part002.json`, etc.
   - It creates a "Master Index" (manifest) in `task_list.json` that remembers
     where all the shards live, so when we need the data back, it stitches them
     together seamlessly in memory.

INPUTS:
- Target folder path (where to save).
- Base filename (e.g., "my_notes" or "task_list").
- Text lines (for Markdown) or Data dictionary (for JSON).

OUTPUTS:
- A list of created part files on your disk.
- Complete reassembled data when reading.

ERROR HANDLING:
- Creates folders automatically if they don't exist (`os.makedirs`).
- Safely handles missing files without crashing.
===============================================================================
"""

import os
import re
import json
from typing import List, Dict, Any, Optional


class ChunkChainManager:
    """
    The ChunkChainManager handles partitioning and chaining for both human-readable
    Markdown notes and machine-readable JSON data stores.
    """

    def __init__(
        self,
        max_md_lines: int = 350,
        max_json_records: int = 250,
        master_index_relpath: str = "../indices/master_taxonomy.md"
    ):
        """
        Setup the manager with default safety limits.
        
        Args:
            max_md_lines: Maximum number of lines allowed in a single Markdown file before splitting.
            max_json_records: Maximum number of key-value records in a single JSON file.
            master_index_relpath: Relative file path pointing back to the main Master Taxonomy Index.
        """
        self.max_md_lines = max_md_lines
        self.max_json_records = max_json_records
        self.master_index_relpath = master_index_relpath

    # =========================================================================
    # MARKDOWN CHUNKING & CHAINING METHODS
    # =========================================================================

    def write_chained_markdown(
        self,
        target_dir: str,
        base_filename: str,
        lines: List[str],
        frontmatter_dict: Optional[Dict[str, Any]] = None,
        master_index_ref: Optional[str] = None
    ) -> List[str]:
        """
        Writes text to Markdown files. If the text is short, it writes 1 file.
        If the text is long, it breaks it into part001.md, part002.md... with
        clickable navigation buttons.

        Args:
            target_dir: The folder where files should be created.
            base_filename: The name of the file (e.g., "economics_notes.md").
            lines: The list of string lines making up the document body.
            frontmatter_dict: Metadata (title, author, date) to place in YAML frontmatter.
            master_index_ref: Custom path to the Master Index if needed.

        Returns:
            List of absolute file paths that were written to disk.
        """
        # Step 1: Make sure the target folder exists on your computer
        os.makedirs(target_dir, exist_ok=True)
        master_ref = master_index_ref or self.master_index_relpath
        clean_base = os.path.splitext(base_filename)[0]

        # Step 2: Check if file is small enough to stay as a single file
        if len(lines) <= self.max_md_lines:
            out_filename = f"{clean_base}.md"
            out_path = os.path.join(target_dir, out_filename)
            content = self._render_md_single(lines, frontmatter_dict, master_ref)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return [out_path]

        # Step 3: If it's too large, partition lines into multiple parts
        parts_lines = self._partition_md_lines(lines, self.max_md_lines)
        total_parts = len(parts_lines)
        written_files = []

        # Step 4: Write each part to disk with previous/next breadcrumb links
        for idx, part_content in enumerate(parts_lines):
            part_num = idx + 1
            part_filename = f"{clean_base}_part{part_num:03d}.md"
            part_path = os.path.join(target_dir, part_filename)

            # Determine who comes before and after this part
            prev_filename = f"{clean_base}_part{part_num - 1:03d}.md" if part_num > 1 else None
            next_filename = f"{clean_base}_part{part_num + 1:03d}.md" if part_num < total_parts else None

            # Render the Markdown with breadcrumbs
            rendered = self._render_md_part(
                part_lines=part_content,
                part_num=part_num,
                total_parts=total_parts,
                base_title=clean_base,
                frontmatter_dict=frontmatter_dict if part_num == 1 else None,
                prev_file=prev_filename,
                next_file=next_filename,
                master_index_ref=master_ref
            )

            with open(part_path, 'w', encoding='utf-8') as f:
                f.write(rendered)
            written_files.append(part_path)

        return written_files

    def _partition_md_lines(self, lines: List[str], chunk_limit: int) -> List[List[str]]:
        """
        Helper method: Chops lines into groups. It tries to be smart and split
        only at natural paragraph headers (starting with '## ') or dividers ('---')
        so sentences aren't cut in half.
        """
        parts = []
        current_part = []
        current_count = 0

        for line in lines:
            current_part.append(line)
            current_count += 1
            # If we exceeded our limit and found a clean section header, make a cut!
            if current_count >= chunk_limit and (line.startswith("## ") or line.startswith("---")):
                parts.append(current_part)
                current_part = []
                current_count = 0

        # Don't forget the last remaining part
        if current_part:
            # If the last piece is tiny (less than 30 lines), merge it with previous piece
            if parts and len(current_part) < 30:
                parts[-1].extend(current_part)
            else:
                parts.append(current_part)

        return parts or [lines]

    def _render_md_single(
        self,
        lines: List[str],
        frontmatter: Optional[Dict[str, Any]],
        master_ref: str
    ) -> str:
        """
        Helper method: Renders a single non-split Markdown file with optional YAML frontmatter.
        """
        out = []
        # Add YAML frontmatter at the top (useful for Obsidian and static site generators)
        if frontmatter:
            out.append("---")
            for k, v in frontmatter.items():
                if isinstance(v, list):
                    out.append(f"{k}:")
                    for item in v:
                        out.append(f"  - {item}")
                else:
                    out.append(f"{k}: {json.dumps(v) if isinstance(v, (dict, bool)) else v}")
            out.append("---\n")

        if master_ref:
            out.append(f"> [Master Taxonomy Index]({master_ref})\n")
        out.extend(lines)
        return "\n".join(out)

    def _render_md_part(
        self,
        part_lines: List[str],
        part_num: int,
        total_parts: int,
        base_title: str,
        frontmatter_dict: Optional[Dict[str, Any]],
        prev_file: Optional[str],
        next_file: Optional[str],
        master_index_ref: str
    ) -> str:
        """
        Helper method: Renders an individual part file with breadcrumbs navigation at top and bottom.
        """
        out = []
        out.append("---")
        if frontmatter_dict:
            for k, v in frontmatter_dict.items():
                if isinstance(v, list):
                    out.append(f"{k}:")
                    for item in v:
                        out.append(f"  - {item}")
                else:
                    out.append(f"{k}: {json.dumps(v) if isinstance(v, (dict, bool)) else v}")
        out.append(f"part_number: {part_num}")
        out.append(f"total_parts: {total_parts}")
        out.append(f"prev_part: {json.dumps(prev_file)}")
        out.append(f"next_part: {json.dumps(next_file)}")
        out.append("---\n")

        # Create Top Navigation Breadcrumbs
        nav_items = []
        if prev_file:
            nav_items.append(f"[Prev: Part {part_num - 1}]({prev_file})")
        else:
            nav_items.append("*(Start of Document)*")

        if master_index_ref:
            nav_items.append(f"[Master Index]({master_index_ref})")

        if next_file:
            nav_items.append(f"[Next: Part {part_num + 1}]({next_file})")
        else:
            nav_items.append("*(End of Document)*")

        nav_bar = " | ".join(nav_items)
        out.append(f"> **Part {part_num} of {total_parts}** - {nav_bar}\n")
        out.extend(part_lines)

        # Create Bottom Navigation Breadcrumbs
        out.append("\n---\n")
        out.append(f"> **Navigation**: {nav_bar}\n")

        return "\n".join(out)

    # =========================================================================
    # JSON CHUNKING & CHAINING METHODS
    # =========================================================================

    def write_chained_json(
        self,
        target_dir: str,
        base_filename: str,
        records_dict: Dict[str, Any],
        manifest_extra: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Writes large dictionaries across multiple JSON shard files if they contain
        too many records, and writes a master manifest index pointing to all parts.

        Args:
            target_dir: Folder to save into.
            base_filename: Main name (e.g. "task_list.json").
            records_dict: The dictionary holding records.
            manifest_extra: Optional extra tracking info to put in the manifest.

        Returns:
            The path to the root manifest file.
        """
        os.makedirs(target_dir, exist_ok=True)
        clean_base = os.path.splitext(base_filename)[0]
        items = list(records_dict.items())
        total_records = len(items)

        # If data is small, write a single standard JSON file
        if total_records <= self.max_json_records:
            root_path = os.path.join(target_dir, f"{clean_base}.json")
            payload = {
                "chain_metadata": {
                    "is_chained": False,
                    "total_records": total_records,
                    "parts": [f"{clean_base}.json"]
                },
                "data": records_dict
            }
            if manifest_extra:
                payload["manifest_info"] = manifest_extra
            with open(root_path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, indent=2)
            return root_path

        # If data is large, shard into smaller chunks
        shards = []
        for i in range(0, total_records, self.max_json_records):
            shards.append(dict(items[i:i + self.max_json_records]))

        total_parts = len(shards)
        part_filenames = []

        # Write each shard file
        for idx, shard_data in enumerate(shards):
            part_num = idx + 1
            part_filename = f"{clean_base}_part{part_num:03d}.json"
            part_path = os.path.join(target_dir, part_filename)
            part_filenames.append(part_filename)

            prev_part = f"{clean_base}_part{part_num - 1:03d}.json" if part_num > 1 else None
            next_part = f"{clean_base}_part{part_num + 1:03d}.json" if part_num < total_parts else None

            part_payload = {
                "chain_metadata": {
                    "base_name": clean_base,
                    "part_index": part_num,
                    "total_parts": total_parts,
                    "prev_part": prev_part,
                    "next_part": next_part,
                    "record_count": len(shard_data),
                    "total_records": total_records
                },
                "data": shard_data
            }
            def _safe_write_json(file_path: str, payload: Any, max_retries: int = 5):
                import time
                for attempt in range(max_retries):
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(payload, f, indent=2)
                        return
                    except (PermissionError, OSError) as e:
                        if attempt == max_retries - 1:
                            print(f"[Warning] Failed to write {file_path} after {max_retries} attempts: {e}")
                        else:
                            time.sleep(0.3 * (attempt + 1))

            _safe_write_json(part_path, part_payload)

        # Write the Master Root Manifest that tracks all shards
        root_path = os.path.join(target_dir, f"{clean_base}.json")
        root_manifest = {
            "chain_metadata": {
                "is_chained": True,
                "base_name": clean_base,
                "total_parts": total_parts,
                "total_records": total_records,
                "part_files": part_filenames
            },
            "manifest_info": manifest_extra or {}
        }
        _safe_write_json(root_path, root_manifest)

        return root_path

    def read_chained_json(self, json_path: str) -> Dict[str, Any]:
        """
        Reads a JSON file. If it's a chained manifest, it automatically loads
        and stitches all part files together so the caller receives the complete dictionary!

        Args:
            json_path: Path to the JSON file or manifest.

        Returns:
            The complete combined dictionary.
        """
        if not os.path.exists(json_path):
            return {}

        with open(json_path, 'r', encoding='utf-8') as f:
            content = json.load(f)

        meta = content.get("chain_metadata", {})
        # If it's not chained, simply return the inner data
        if not meta.get("is_chained", False):
            return content.get("data", content)

        # If it is chained, loop over all listed shard files and assemble the dictionary
        base_dir = os.path.dirname(json_path)
        combined_data = {}
        for part_file in meta.get("part_files", []):
            part_full = os.path.join(base_dir, part_file)
            if os.path.exists(part_full):
                with open(part_full, 'r', encoding='utf-8') as pf:
                    pdata = json.load(pf)
                    combined_data.update(pdata.get("data", {}))

        return combined_data
