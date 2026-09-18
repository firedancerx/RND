# 05. Universal Chunking & Chaining Protocol

## 1. Overview
To prevent memory bloat, avoid single-point-of-failure monolithic files, and provide effortless navigation across multi-thousand-page libraries, the system implements a **Universal Chunking & Chaining Protocol** (`scripts/chunk_chain_manager.py`).

Every document, index, summary, and JSON registry supports bidirectional linked chaining:

```
  [<< Previous Part]  ◀───▶  [Master Index]  ◀───▶  [Next Part >>]
```

---

## 2. Markdown Chaining Specification

### A. Pagination Rules
- **Line Limit**: Maximum 400 lines of formatted content per part file (e.g. `doc_id_part001.md`, `doc_id_part002.md`).
- **YAML Frontmatter**: Every chained Markdown file contains standardized YAML frontmatter:
  ```yaml
  ---
  title: Financial Accounting Series
  part_index: 1
  total_parts: 3
  doc_id: financial_accounting_series
  master_index: ../indices/master_taxonomy.md
  previous_part: null
  next_part: financial_accounting_series_part002.md
  created_at: '2026-09-19T03:30:00'
  ---
  ```

### B. Navigation Breadcrumbs
Every part automatically receives top and bottom breadcrumb navigation bars:
```markdown
[<< Previous Part](doc_part001.md) | [📖 Master Taxonomy Index](../indices/master_taxonomy.md) | [Next Part >>](doc_part003.md)
---
```

---

## 3. JSON Registry Chaining Specification

Large registries (such as `task_list.json`) are automatically chained when exceeding 250 records:
- `task_list_part001.json`, `task_list_part002.json`
- Each JSON part includes metadata tracking `part_index`, `total_parts`, `total_records`, and `next_part`.
- Readers (`read_chained_json`) transparently traverse and assemble all parts into a unified memory dictionary.
