# 04. Vector Store & Cloud GenAI Integration

## 1. Local Dense Vector Database Architecture

The system features an embedded, serverless vector database implemented in Python using SQLite 3 and NumPy (`scripts/vector_store.py`).

### A. Database Schema (`vector_store.sqlite`)

```sql
-- 1. Document Chunks & Dense Vectors
CREATE TABLE IF NOT EXISTS document_chunks (
    chunk_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    doc_title TEXT NOT NULL,
    section TEXT NOT NULL,
    text TEXT NOT NULL,
    vector_blob BLOB NOT NULL,
    created_at TEXT NOT NULL
);

-- 2. Taxonomy Nodes & Concept Vectors
CREATE TABLE IF NOT EXISTS taxonomy_vectors (
    taxonomy_id TEXT PRIMARY KEY,
    taxonomy_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    depth INTEGER NOT NULL,
    keywords TEXT NOT NULL,
    vector_blob BLOB NOT NULL,
    updated_at TEXT NOT NULL
);

-- 3. Tacit User Reflection Notes
CREATE TABLE IF NOT EXISTS user_notes (
    note_id TEXT PRIMARY KEY,
    doc_id TEXT NOT NULL,
    chunk_id TEXT,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

---

## 2. 256-Dimensional Dense Embedding Engine

### A. Mathematical Embedding Model
Each text passage is converted into a 256-dimensional unit-norm dense vector:
1. **Tokenization & Cleaning**: Splits text into alphanumeric tokens, lowercasing and discarding stopwords.
2. **Deterministic Hash Projection**: Maps each word $w$ to a bucket index $i = 	ext{MD5}(w) \pmod{256}$.
3. **Frequency Weighting**: Accumulates term frequencies $v[i] = \sum 	ext{tf}(w)$.
4. **Unit-Norm Normalization**: Normalizes the vector to unit length:
   $$\hat{v} = rac{ec{v}}{\|ec{v}\|_2} = rac{ec{v}}{\sqrt{\sum_{k=1}^{256} v_k^2}}$$

### B. Cosine Similarity Calculation
The similarity between document passage vector $ec{u}$ and taxonomy concept vector $ec{w}$ is calculated as:
$$	ext{Sim}(ec{u}, ec{w}) = ec{u} \cdot ec{w} = \sum_{k=1}^{256} u_k w_k$$
Matches exceeding the threshold (default: `0.25`) are linked.

---

## 3. External Cloud Generative AI Agent Integration

For high-level knowledge synthesis (Executive Summaries and Core Principles), the system communicates with an external DigitalOcean Serverless GenAI Agent.

### A. Endpoint & Authentication
- **Service**: DigitalOcean GenAI Agent Serverless Platform
- **Agent ID**: `d139564c-a122-11f1-aee4-4e013e2ddde4`
- **Protocol**: HTTPS POST via Python standard library (`urllib.request`)
- **Payload Schema**:
  ```json
  {
    "messages": [
      {
        "role": "user",
        "content": "Synthesize an Executive Summary and 5 Core Principles..."
      }
    ]
  }
  ```

### B. Offline & Timeout Resilience
The API request includes a 10–12 second strict socket timeout. If the cloud endpoint is unreachable or offline, the system automatically falls back to an internal statistical summary generator without halting the pipeline.
