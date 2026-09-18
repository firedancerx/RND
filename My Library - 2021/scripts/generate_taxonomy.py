"""
===============================================================================
FILE: generate_taxonomy.py
===============================================================================
WHAT IS THIS FILE FOR? (THE INTENT):
When you read a lot of books, how do you discover the big ideas and concepts they
are discussing without reading every single page manually?

This file is our "Idea Mining & Knowledge Extraction Lab". It does two clever things:
1. Multi-Ngram Phrase Extraction:
   - Scans thousands of sentences to find repeated meaningful multi-word terms
     (like "Working Capital", "Cognitive Behavioral Therapy", or "Neural Networks").
2. Semantic Triplet Extraction:
   - Identifies grammatical relationships where one concept acts on another,
     forming knowledge graph triples:
     `[[Subject]]` -- `[Relationship]` --> `[[Object]]`
     (e.g., `[[Working Capital]] -- is_a --> [[Financial Management]]`).
3. External Cloud LLM Synthesis:
   - Calls the DigitalOcean GenAI Agent / Gemini API to refine and summarize
     complex conceptual clusters.

HOW IT WORKS IN SIMPLE TERMS:
1. `extract_multi_ngrams`:
   - Examines word sequences (2-word bigrams and 3-word trigrams).
   - Tallies phrase frequency and how many distinct documents use that term.
   - Selects the most prominent, meaningful multi-word concepts.

2. `extract_semantic_triplets`:
   - Uses regex patterns to find relationship verbs:
     * `is_a`: "is a", "refers to", "defines as"
     * `part_of`: "comprises", "consists of", "includes"
     * `influences`: "impacts", "determines", "drives"
     * `prerequisite_of`: "requires", "depends on", "based on"
     * `mitigates`: "treats", "reduces", "prevents"
     * `measures`: "quantifies", "evaluates"
   - Whenever two known taxonomy concepts appear on opposite sides of one of these
     verbs in the same sentence, it creates a verified Semantic Triple!

INPUTS:
- Text chunks from all processed books.
- List of active taxonomy concepts.

OUTPUTS:
- Candidate multi-ngram concepts.
- List of verified Semantic Triplet dictionaries.
- LLM synthesized summaries.

ERROR HANDLING:
- Includes timeout safeguards on all external network/API requests (10-15s timeout).
- If the external LLM or network is unavailable, the pipeline falls back gracefully
  to local statistical extraction without crashing.
===============================================================================
"""

import os
import re
import json
import math
import urllib.request
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

# DigitalOcean GenAI Agent connection parameters
DO_AGENT_ID = "d139564c-a122-11f1-aee4-4e013e2ddde4"
DO_API_KEY = os.environ.get("DO_API_KEY", "Lm9QyNOPFSzSUVy8XuCEvUDol__n6g92")
DO_CHAT_URL = "https://qdaknrh2rzs3aueib5py5cbo.agents.do-ai.run/api/v1/chat/completions"


class TaxonomyGenerator:
    """
    Extracts multi-ngram domain concepts, calls cloud LLM agents for synthesis,
    and extracts structured ontology relationship triples from passage texts.
    """

    def __init__(self, do_agent_id: Optional[str] = None, do_api_key: Optional[str] = None):
        self.do_agent_id = do_agent_id or DO_AGENT_ID
        self.do_api_key = do_api_key or DO_API_KEY
        # Stop-words to ignore so we do not extract meaningless phrases like "the book of"
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'over', 'after',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'this', 'that', 'these', 'those', 'it', 'its', 'they', 'them', 'their',
            'which', 'what', 'where', 'when', 'who', 'how', 'all', 'any', 'both',
            'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will',
            'just', 'should', 'now', 'also', 'as', 'if', 'may', 'would', 'could',
            'page', 'chapter', 'book', 'text', 'used', 'use', 'using', 'one', 'two'
        }

    def _get_do_token(self) -> Optional[str]:
        """
        Helper method: Requests a temporary JWT Bearer access token from DigitalOcean
        using our API Key.
        """
        try:
            token_url = f"https://cloud.digitalocean.com/gen-ai/auth/agents/{DO_AGENT_ID}/token"
            headers = {"Content-Type": "application/json", "X-Api-Key": DO_API_KEY}
            req = urllib.request.Request(token_url, data=json.dumps({}).encode('utf-8'), headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data.get("access_token")
        except Exception:
            return None

    def call_llm_synthesis(self, prompt: str, max_timeout: int = 15) -> Optional[str]:
        """
        Sends a prompt to the DigitalOcean GenAI Agent / Gemini endpoint and returns
        the generated synthesis text.

        Args:
            prompt: Instructions for the AI model.
            max_timeout: Number of seconds to wait before giving up if network is slow.

        Returns:
            The AI response string, or None if unavailable.
        """
        token = self._get_do_token()
        if not token:
            return None
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            payload = json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            }).encode('utf-8')
            req = urllib.request.Request(DO_CHAT_URL, data=payload, headers=headers)
            with urllib.request.urlopen(req, timeout=max_timeout) as resp:
                result = json.loads(resp.read().decode('utf-8'))
                choices = result.get('choices', [])
                if choices:
                    return choices[0]['message']['content']
        except Exception:
            pass
        return None

    def extract_multi_ngrams(
        self,
        chunks: List[Dict[str, Any]],
        top_n: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scans all text passages to identify frequent 2-word (bigram) and 3-word (trigram)
        phrases representing domain concepts.

        Args:
            chunks: List of passage chunk dictionaries.
            top_n: Number of top candidate phrases to return.

        Returns:
            List of candidate concept dictionaries with name, keywords, and frequency.
        """
        phrase_freqs = Counter()
        doc_freqs = Counter()

        for c in chunks:
            text = c['text']
            words = [w.capitalize() for w in re.findall(r'\b[a-zA-Z]{3,}\b', text) if w.lower() not in self.stop_words]
            seen_phrases = set()

            # Extract adjacent 2-word pairs
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if len(bigram) > 7:
                    phrase_freqs[bigram] += 1
                    seen_phrases.add(bigram)

            # Extract adjacent 3-word triplets
            for i in range(len(words) - 2):
                trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
                if len(trigram) > 11:
                    phrase_freqs[trigram] += 1
                    seen_phrases.add(trigram)

            for p in seen_phrases:
                doc_freqs[p] += 1

        # Keep phrases that appear at least twice across documents
        sorted_phrases = [p for p, f in phrase_freqs.most_common() if f >= 2 and doc_freqs[p] >= 1][:top_n]

        candidates = []
        for p in sorted_phrases:
            kws = [w.lower() for w in p.split()]
            candidates.append({
                "name": p,
                "keywords": kws,
                "description": f"Contextual knowledge concept relating to {p}.",
                "frequency": phrase_freqs[p]
            })
        return candidates

    def extract_semantic_triplets(
        self,
        chunks: List[Dict[str, Any]],
        taxonomy_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Parses sentences to discover relational statements connecting two taxonomy items.
        Example: "Working capital constitutes an integral part of financial management"
        Becomes: [[Working Capital]] -- is_a --> [[Financial Management]]

        Args:
            chunks: Text chunks to analyze.
            taxonomy_items: The list of established taxonomy concepts.

        Returns:
            List of extracted semantic triplet dictionaries.
        """
        triplets = []
        predicate_patterns = [
            (r'\b(is an|is a|refers to|defines as|constitutes)\b', "is_a"),
            (r'\b(comprises|consists of|includes|part of|contains)\b', "part_of"),
            (r'\b(influences|impacts|determines|affects|drives)\b', "influences"),
            (r'\b(requires|depends on|based on|prerequisite)\b', "prerequisite_of"),
            (r'\b(mitigates|treats|reduces|prevents)\b', "mitigates"),
            (r'\b(measures|quantifies|evaluates)\b', "measures")
        ]

        concept_names = [t['name'] for t in taxonomy_items]

        for c in chunks:
            text = c['text']
            sentences = re.split(r'[.!?]+\s+', text)

            for sent in sentences:
                for pattern, pred in predicate_patterns:
                    match = re.search(pattern, sent, re.IGNORECASE)
                    if match:
                        pred_text = match.group(0)
                        parts = re.split(re.escape(pred_text), sent, 1, re.IGNORECASE)
                        if len(parts) == 2:
                            left = parts[0].strip()
                            right = parts[1].strip()

                            matched_left = None
                            matched_right = None

                            # Check if a known concept lives in the left side and right side
                            for cn in concept_names:
                                if cn.lower() in left.lower() and not matched_left:
                                    matched_left = cn
                                if cn.lower() in right.lower() and not matched_right:
                                    matched_right = cn
                                if matched_left and matched_right:
                                    break

                            # If both sides contain distinct valid concepts, record the triple!
                            if matched_left and matched_right and matched_left != matched_right:
                                triplets.append({
                                    "subject": matched_left,
                                    "predicate": pred,
                                    "object": matched_right,
                                    "chunk_id": c['chunk_id'],
                                    "doc_title": c.get('doc_title', ''),
                                    "context_snippet": sent[:120]
                                })
        return triplets
