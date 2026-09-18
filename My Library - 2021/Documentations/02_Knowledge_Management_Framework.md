# 02. Knowledge Management Framework & Theoretical Foundations

## 1. Overview
This software is designed around the universal, validated principles of **Knowledge Management (KM)** established across academic literature, organizational theory, and ontological engineering.

```
       ┌────────────────────────────────────────────────────────┐
       │               KM Universal Principles Triad            │
       │                                                        │
       │     [PEOPLE]            [PROCESS]          [TECHNOLOGY]│
       │  Tacit Insights      5-Phase Pipeline     SQLite Vector│
       │  User Heuristics     Intent Logging       Cloud GenAI  │
       │  Annotations         Deprecation Audit    Wikilinks    │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Alignment with Classic KM Models

### A. The SECI Model (Nonaka & Takeuchi, 1995)
The SECI model describes how knowledge dynamically transforms between **Tacit** (internal, experiential) and **Explicit** (codified, structured) forms:

| SECI Stage | Transformation Type | System Implementation |
| :--- | :--- | :--- |
| **Socialization** | *Tacit to Tacit* | Captures shared heuristics and practitioner experiences into persistent user annotation records (`vector_db.save_user_note`). |
| **Externalization** | *Tacit to Explicit* | Converts reader annotations and highlights into formal document sections (`# 📝 User Annotations, Heuristics & Tacit Insights`). |
| **Combination** | *Explicit to Explicit* | Combines multi-book text chunks, extracts multi-ngram candidates, and consolidates them into the structured `Master Taxonomy Markdown`. |
| **Internalization** | *Explicit to Tacit* | Generates AI Executive Summaries and Core Principles briefs allowing users to rapidly absorb and internalize key domain concepts. |

---

### B. Hansen, Nohria & Tierney's KM Strategies (1999)
- **Codification Strategy (Stock of Knowledge)**: High reusability through structured electronic storage, atomic chunking, standardized metadata schemas, and the 6-domain ontology.
- **Personalization Strategy (Flow of Knowledge)**: Two-way semantic cross-linking, Yellow Pages directories, and AI-driven interactive principle extraction.

---

### C. Ontological Engineering & Semantic Triples
Traditional search systems rely on simple keyword matching (TF-IDF), which misses conceptual context. This system incorporates formal ontological engineering:
1. **Multi-Tier Hierarchy**: Depth levels (1 to 5) structuring roots, branches, sub-branches, and leaf concepts.
2. **Knowledge Graph Triples**: Extracted `(Subject, Predicate, Object)` triplets representing formal relationships (e.g. `[[Working Capital]]` -- `measures` --> `[[Operating Liquidity]]`).
3. **Ontology Yellow Pages**: An index measuring concept density, leaf distributions, and corpus connection strengths.

---

### D. Intent-First Governance & Pre-Execution Logging
To prevent accidental data corruption or uncontrolled schema mutations, the system logs an explicit intent record (`output_taxonomy/intents/intent_<timestamp>.md`) prior to modifying the Master Taxonomy or document database.
