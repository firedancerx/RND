# 07. User Operations & Launchers Guide

## 1. Launching the System

The platform provides multiple user-friendly execution methods tailored for Windows environments.

---

## 2. Interactive Console Launcher (`Run_Taxonomy_Pipeline.cmd`)
Located in the project root directory, double-click or run:
```cmd
Run_Taxonomy_Pipeline.cmd
```

```text
======================================================================
          SEMANTIC TAXONOMY EXTRACTION & LINKING PIPELINE
======================================================================

  [1] Run FULL End-to-End Pipeline (Ingest, Consolidate, Link, Render)
  [2] Ingest & Chunk Pending Books Only (Step 1)
  [3] Run Global Taxonomy Consolidation & Leader Re-classification (Step 2)
  [4] Run Bi-Directional Semantic Cross-Linking & Strength Scoring (Step 3)
  [5] Re-render Inline Hyperlinks & Master Index (Step 4)
  [6] Start Live Folder Watcher Service (Background Monitor)
  [7] Exit

======================================================================
Select an option [1-7]:
```

---

## 3. Desktop Shortcuts Setup
To create convenient 1-click shortcuts directly on your Windows Desktop:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_shortcut.ps1
```
This automatically provisions 4 desktop shortcuts with distinctive Windows icons:
1. `1. Run Full Pipeline.lnk` (Icon: Computer terminal)
2. `2. Ingest Books Only.lnk` (Icon: Book folder)
3. `3. Consolidate Taxonomy.lnk` (Icon: Tree hierarchy)
4. `4. Render Markdown Index.lnk` (Icon: Document link)

---

## 4. Live Background Folder Watcher Daemon
To automatically queue new books the moment they are copied into the library:
```cmd
python scripts\watch_folder.py "."
```
The service checks the folder every 5 seconds and adds any new PDF, EPUB, TXT, or MD files to `task_list.json` with status `"pending"`.

---

## 5. Viewing Output in Obsidian or Markdown Readers
All generated output lives in `output_taxonomy/`:
- **Document Pages**: `output_taxonomy/documents/` — Open as a vault in [Obsidian](https://obsidian.md) for interactive graphical graph exploration and clickable `[[Wikilinks]]`.
- **Master Taxonomy**: `output_taxonomy/indices/master_taxonomy.md` — Central hierarchical concept catalog.
- **Yellow Pages**: `output_taxonomy/indices/taxonomy_yellow_pages.md` — Concept density directory.
- **Knowledge Graph Triples**: `output_taxonomy/triplets/semantic_triplets.md` — Relational triples.
- **Executive Summaries**: `output_taxonomy/summaries/` — Chapter briefs and core principles.
