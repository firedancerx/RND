"""
===============================================================================
FILE: format_markdown_output.py
===============================================================================
WHAT IS THIS FILE FOR? (Intent & Big Picture)
When knowledge is trapped inside dense PDF or EPUB files, it is hard to navigate
and cross-reference. This file is the "Master Publisher" and "Typesetter" of our
Knowledge Management system. It takes raw text chunks and transforms them into
beautiful, readable, inter-connected Markdown (.md) documents!

Think of Wikipedia: whenever an important concept is mentioned, it is highlighted
as a blue clickable link. This module does exactly that: it finds technical taxonomy
terms in the text, wraps them with Obsidian/Wiki-style links like `[[Taxonomy Concept|Text]]`,
adds academic-style footnote references with similarity confidence scores, generates
Executive Summaries using an AI synthesizer, extracts Knowledge Graph Triples, and
compiles an "Ontology Yellow Pages" directory!

-------------------------------------------------------------------------------
KEY PROCESSES CARRIED OUT:
1. Regex Multi-Word Keyword Highlighting: Inserts `[[Wikilinks]]` around taxonomy terms
   (prioritizing longest phrases first to prevent sub-string mangling).
2. Footnote Annotation: Appends footnotes showing concept domain, depth, and similarity score.
3. User Note Preservation: Includes a dedicated section for personal reflections and tacit notes.
4. Chaining & Chunking Integration: Splits huge books into neat chained parts with breadcrumbs.
5. Triplet Index Generation: Formats Knowledge Graph Subject-Verb-Object triples.
6. Executive Summary Generation: Combines top passages and prompts an LLM for core principles.
7. Yellow Pages Generation: Builds an index showing how often each concept appears across books.

COMPONENTS USED:
- ChunkChainManager (chunk_chain_manager.py): Enforces universal chunking and chaining.
- TaxonomyGenerator (generate_taxonomy.py): Calls LLM for executive summaries.
- re (Python Standard Library): For regular expression phrase replacement.

INPUTS:
- Text chunks, document metadata, similarity links, taxonomy hierarchy, user notes.

OUTPUTS:
- `output_taxonomy/documents/<doc_id>.md`: Chained, wikilinked document pages.
- `output_taxonomy/triplets/semantic_triplets.md`: Knowledge Graph registry.
- `output_taxonomy/summaries/<doc_id>_summary.md`: AI Executive Summaries.
- `output_taxonomy/indices/taxonomy_yellow_pages.md`: Yellow Pages directory.

ERROR HANDLING:
- Handles missing user notes or metadata by supplying safe defaults.
- Protects against regex collisions and nested brackets when replacing terms.
===============================================================================
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Import our custom modules for chunk-chaining and AI taxonomy operations
from chunk_chain_manager import ChunkChainManager
from generate_taxonomy import TaxonomyGenerator


class MarkdownFormatter:
    """
    The MarkdownFormatter class creates structured, interconnected Markdown files
    for books, summaries, ontology indices, and semantic triples.
    """

    def __init__(self, output_dir: str):
        """
        INITIALIZATION:
        Sets up the directory structure where all generated Markdown files will live.
        """
        self.output_dir = output_dir
        # Subdirectories for organized knowledge assets
        self.docs_dir = os.path.join(output_dir, "documents")
        self.indices_dir = os.path.join(output_dir, "indices")
        self.triplets_dir = os.path.join(output_dir, "triplets")
        self.summaries_dir = os.path.join(output_dir, "summaries")
        self.notes_dir = os.path.join(output_dir, "notes")

        # Automatically create each folder if it does not exist yet
        for d in [self.docs_dir, self.indices_dir, self.triplets_dir, self.summaries_dir, self.notes_dir]:
            os.makedirs(d, exist_ok=True)

        # Initialize the chain manager with the relative link to the master taxonomy
        self.chain_mgr = ChunkChainManager(master_index_relpath="../indices/master_taxonomy.md")
        # Initialize the taxonomy helper for AI synthesis
        self.tax_gen = TaxonomyGenerator()

    def generate_document_markdown(
        self,
        doc_id: str,
        doc_title: str,
        chunks: List[Dict[str, Any]],
        passage_links: Dict[str, List[Dict[str, Any]]],
        taxonomy_nodes: List[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]] = None,
        user_notes: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        TRANSFORMS A BOOK'S CHUNKS INTO WIKILINKED MARKDOWN PAGES:
        1. Formats document header and YAML metadata.
        2. Detects taxonomy keywords in the text and wraps them in [[Wikilinks]].
        3. Attaches academic footnotes with vector similarity scores.
        4. Preserves user reflection notes at the bottom.
        5. Writes the files with universal chunking & chaining (e.g. part001.md, part002.md).
        """
        # Use provided metadata or fallback to default dictionary
        meta = metadata or {
            "title": doc_title,
            "doc_id": doc_id,
            "doc_version": "1.0",
            "updated_at": datetime.now().isoformat()
        }

        lines = []
        # Main document title header
        lines.append(f"# {doc_title}\n")
        lines.append("> 📖 **Knowledge Management Document Model** - Semantically Enriched & Densely Wikilinked.\n")

        # Build a lookup table from keyword -> (taxonomy_id, taxonomy_name)
        term_to_nodes = {}
        for node in taxonomy_nodes:
            t_id = node['taxonomy_id']
            t_name = node['name']
            candidates = [node['name']] + node.get('keywords', [])
            for cand in candidates:
                c_clean = cand.strip()
                # Only link terms of 4+ characters to avoid false positive matches on tiny words
                if len(c_clean) >= 4 and not c_clean.lower().startswith('tax_'):
                    key = c_clean.lower()
                    if key not in term_to_nodes:
                        term_to_nodes[key] = []
                    if (t_id, t_name) not in term_to_nodes[key]:
                        term_to_nodes[key].append((t_id, t_name))

        # Sort terms by length (longest phrases first) so "Internal Control System" is linked
        # before just "Control" or "System", avoiding broken partial replacements!
        sorted_terms = sorted(term_to_nodes.keys(), key=lambda k: len(k), reverse=True)

        # Group text chunks by their section or chapter
        sections = {}
        for chunk in chunks:
            sec = chunk.get('section', 'Main')
            if sec not in sections:
                sections[sec] = []
            sections[sec].append(chunk)

        footnotes = []

        # Iterate through each section and paragraph
        for sec_name, sec_chunks in sections.items():
            lines.append(f"## {sec_name}\n")

            for chunk in sec_chunks:
                c_id = chunk['chunk_id']
                text = chunk['text']
                links = passage_links.get(c_id, [])

                linked_text = text

                # Replace technical terms with Wikilinks
                for term in sorted_terms:
                    nodes = term_to_nodes[term]
                    # Regex pattern: Match word boundaries, but ignore if already inside [[...]]
                    pattern = re.compile(rf'(?<!\[\[)\b({re.escape(term)})\b(?![^\[]*\]\])', re.IGNORECASE)

                    def replace_func(match, n_list=nodes):
                        matched_word = match.group(1)
                        t_id, t_name = n_list[0]
                        return f"[[{t_name}|{matched_word}]]"

                    linked_text = pattern.sub(replace_func, linked_text)

                # Insert HTML anchor tag so other files can link directly to this paragraph!
                chunk_md = f'<a id="{c_id}"></a>\n{linked_text}'

                # Add footnote references if this chunk has high-confidence vector matches
                if links:
                    fn_refs = []
                    seen_links = set()
                    for link in links:
                        t_id = link['taxonomy_id']
                        if t_id in seen_links:
                            continue
                        seen_links.add(t_id)

                        fn_id = f"fn_{c_id}_{t_id.replace('.', '_')}"
                        fn_refs.append(f"[^{fn_id}]")
                        tax_target = f"../indices/master_taxonomy.md#{t_id.lower().replace('.', '_')}"
                        fn_entry = (
                            f"[^{fn_id}]: *Semantic Concept*: [[{link['taxonomy_name']}]]({tax_target}) "
                            f"(Domain: `{link['domain']}` | Depth: `{link['depth']}` | Similarity: `{link['strength']:.2f}`)"
                        )
                        footnotes.append(fn_entry)
                    chunk_md += " " + "".join(fn_refs)

                lines.append(chunk_md + "\n")

        # Append the list of footnotes at the bottom of the document
        if footnotes:
            lines.append("\n---\n### Semantic Association Footnotes & Density Scores\n")
            lines.extend(footnotes)

        # Append User Annotations and Notes section (SECI Tacit Knowledge Externalization)
        lines.append("\n---\n## 📝 User Annotations, Heuristics & Tacit Insights\n")
        if user_notes:
            for n in user_notes:
                lines.append(f"- **[{n.get('created_at', 'Stored')}]**: {n.get('content', '')}\n")
        else:
            lines.append("*No user notes added yet. Add your personal insights, commentary, or heuristics here. They are automatically preserved across re-runs.*\n")

        # Write out with chunking & chaining manager (splits large docs into parts if needed)
        files = self.chain_mgr.write_chained_markdown(
            target_dir=self.docs_dir,
            base_filename=f"{doc_id}.md",
            lines=lines,
            frontmatter_dict=meta,
            master_index_ref="../indices/master_taxonomy.md"
        )
        return files

    def generate_semantic_triplets_md(
        self,
        triplets: List[Dict[str, Any]]
    ) -> List[str]:
        """
        GENERATES THE SEMANTIC TRIPLETS REGISTRY:
        Produces a knowledge graph document listing (Subject -> Predicate -> Object)
        triplets with links back to the original source passage.
        """
        lines = []
        lines.append("# Semantic Ontology Triplets Registry\n")
        lines.append("> 🌐 **Explicit Knowledge Graph Triples** extracted across documents and linked to the Master Taxonomy.\n")
        lines.append("---\n")

        if not triplets:
            lines.append("*No triplets extracted yet.*\n")
        else:
            for i, tr in enumerate(triplets):
                s = tr['subject']
                p = tr['predicate']
                o = tr['object']
                doc_title = tr.get('doc_title', 'Doc')
                chunk_id = tr.get('chunk_id', '')

                lines.append(f"## Triple {i + 1}: [[{s}]] -- `{p}` --> [[{o}]]\n")
                lines.append(f"- **Relation Type**: `{p}`")
                lines.append(f"- **Source Passage**: [\"{tr['context_snippet']}\"]({doc_title}.md#{chunk_id})\n")
                lines.append("---\n")

        frontmatter = {
            "type": "semantic_triplets_index",
            "total_triplets": len(triplets),
            "updated_at": datetime.now().isoformat()
        }

        return self.chain_mgr.write_chained_markdown(
            target_dir=self.triplets_dir,
            base_filename="semantic_triplets.md",
            lines=lines,
            frontmatter_dict=frontmatter,
            master_index_ref="../indices/master_taxonomy.md"
        )

    def generate_executive_summary(
        self,
        doc_id: str,
        doc_title: str,
        chunks: List[Dict[str, Any]],
        taxonomy_matches: List[Dict[str, Any]]
    ) -> List[str]:
        """
        GENERATES AN AI EXECUTIVE SUMMARY & CORE PRINCIPLES:
        Calls an external LLM (or local fallback) to summarize the book into
        actionable decision-making principles and lists key taxonomy topics.
        """
        lines = []
        lines.append(f"# Executive Summary & Core Principles: {doc_title}\n")
        lines.append("> 💡 **Knowledge Synthesis Brief** for executive decision-support and active internalization.\n")
        lines.append("---\n")

        # Take a representative sample of text from the beginning of the book
        pooled_text = " ".join([c['text'] for c in chunks[:10]])[:1200]
        llm_prompt = (
            f"Synthesize an Executive Summary and 5 Core Principles for the following book:\n"
            f"Title: {doc_title}\nContent Sample:\n{pooled_text}\n"
            "Respond with ## Executive Summary followed by ## Core Principles & Heuristics."
        )

        # Call the GenAI agent for synthesis
        synthesis = self.tax_gen.call_llm_synthesis(llm_prompt, max_timeout=12)
        if synthesis:
            lines.append(synthesis)
        else:
            # Fallback summary if offline or timeout occurs
            lines.append("## Executive Summary\n")
            lines.append(f"This document (\"{doc_title}\") encompasses {len(chunks)} analyzed atomic passages. It provides comprehensive domain coverage of related concepts and practical frameworks.\n")
            lines.append("## Core Principles & Heuristics\n")
            for m in taxonomy_matches[:5]:
                lines.append(f"1. **[[{m['taxonomy_name']}]]**: Essential foundational principle governing this domain.\n")

        # List related taxonomy intersections
        lines.append("\n---\n## Conceptual Knowledge Intersections\n")
        for m in taxonomy_matches[:8]:
            lines.append(f"- [[{m['taxonomy_name']}]] ({m.get('domain', 'Deep Hierarchy')}) - Association Strength: `{m['strength']}`\n")

        frontmatter = {
            "type": "executive_summary",
            "doc_id": doc_id,
            "doc_title": doc_title,
            "generated_at": datetime.now().isoformat()
        }

        return self.chain_mgr.write_chained_markdown(
            target_dir=self.summaries_dir,
            base_filename=f"{doc_id}_summary.md",
            lines=lines,
            frontmatter_dict=frontmatter,
            master_index_ref="../indices/master_taxonomy.md"
        )

    def generate_taxonomy_yellow_pages(
        self,
        master_data: Dict[str, Any],
        taxonomy_to_passages: Dict[str, List[Dict[str, Any]]]
    ) -> List[str]:
        """
        GENERATES THE KNOWLEDGE YELLOW PAGES DIRECTORY:
        Creates a lookup catalog showing every taxonomy concept, its depth,
        its total occurrences in the library, and links to top passages.
        """
        lines = []
        lines.append("# Knowledge Management Yellow Pages & Connectivity Metrics\n")
        lines.append("> 📒 **Ontology Yellow Pages** showing domain depths, leaf-node quantities, and corpus linkages.\n")
        lines.append("---\n")

        for domain in master_data.get("hierarchy", []):
            lines.append(f"# Domain: {domain['domain_name']}\n")
            for node in domain.get('concept_nodes', []):
                t_id = node['taxonomy_id']
                name = node['name']
                passages = taxonomy_to_passages.get(t_id, [])

                lines.append(f"## [[{name}]] (`{t_id}`)\n")
                lines.append("- **Depth Level**: `4/5`")
                lines.append(f"- **Corpus Occurrences / Links**: `{len(passages)}` passages")
                lines.append(f"- **Keywords Covered**: `{', '.join(node.get('keywords', []))}`\n")

                if passages:
                    lines.append("- **Top References**:")
                    for p in passages[:3]:
                        doc_file = f"../documents/{p['chunk_id'].split('_')[0]}.md#{p['chunk_id']}"
                        lines.append(f"  - [{p['doc_title']} - {p['section']}]({doc_file}) | Strength: `{p['strength']:.2f}`")
                lines.append("\n---\n")

        frontmatter = {
            "type": "taxonomy_yellow_pages",
            "total_domains": master_data.get("total_domains", 0),
            "total_nodes": master_data.get("total_nodes", 0),
            "updated_at": datetime.now().isoformat()
        }

        return self.chain_mgr.write_chained_markdown(
            target_dir=self.indices_dir,
            base_filename="taxonomy_yellow_pages.md",
            lines=lines,
            frontmatter_dict=frontmatter,
            master_index_ref="master_taxonomy.md"
        )
