"""
===============================================================================
FILE: taxonomy_hygiene.py
===============================================================================
WHAT IS THIS FILE FOR? (Intent & Big Picture)
In any large knowledge repository or digital library, "Taxonomy Drift" can occur:
- Old concepts might be defined that are never actually used in any book ("Orphan Nodes").
- Broken links or missing documents can clutter the library index.
- Some concepts might be overloaded while others are completely neglected.

This file is our "Quality Assurance Inspector" and "Doctor for Knowledge Health".
It performs automated audits of our Master Taxonomy against all generated Markdown
documents, calculates link density, flags orphan concepts, and calculates an
overall "Knowledge Hygiene Score" (0% to 100%)!

-------------------------------------------------------------------------------
KEY PROCESSES CARRIED OUT:
1. Master Taxonomy Parsing: Reads `master_taxonomy.md` and extracts all defined concept names and IDs.
2. Cross-Corpus Link Counting: Scans all `.md` files in `output_taxonomy/documents/` to count
   how many times each concept is referenced.
3. Orphan Identification: Detects concepts with 0 references in the corpus.
4. Hygiene Scoring: Computes percentage metric: `(Active Concepts / Total Concepts) * 100`.
5. Audit Report Generation: Prints a clear audit dashboard to the console.

COMPONENTS USED:
- re: Regular expressions to parse markdown anchors and headers.
- os & glob: File system scanning.

INPUTS:
- `output_taxonomy/indices/master_taxonomy.md`
- `output_taxonomy/documents/*.md`

OUTPUTS:
- Console audit report summary.
- Audit report dictionary with hygiene metrics and list of orphan concepts.

ERROR HANDLING:
- Gracefully handles missing master taxonomy files or empty document directories.
===============================================================================
"""

import os
import re
import json
import argparse
from datetime import datetime
from typing import List, Dict, Any


class TaxonomyHygieneAuditor:
    """
    The TaxonomyHygieneAuditor scans the Master Taxonomy and generated documents
    to measure network connectivity, identify orphan concepts, and score system hygiene.
    """

    def __init__(self, output_dir: str):
        """
        INITIALIZATION:
        Sets paths to the master taxonomy index and documents directory.
        """
        self.output_dir = output_dir
        self.master_md_path = os.path.join(output_dir, "indices", "master_taxonomy.md")
        self.docs_dir = os.path.join(output_dir, "documents")

    def run_audit(self) -> Dict[str, Any]:
        """
        EXECUTES THE HYGIENE AUDIT:
        Returns a dictionary summarizing total concepts, orphan counts, and hygiene score.
        """
        print("=" * 60)
        print("RUNNING KNOWLEDGE MANAGEMENT TAXONOMY HYGIENE AUDIT")
        print("=" * 60)

        # Check if the master taxonomy exists
        if not os.path.exists(self.master_md_path):
            print("Master taxonomy not found at:", self.master_md_path)
            return {"error": "Master taxonomy not found"}

        # Read the contents of the master taxonomy markdown
        with open(self.master_md_path, 'r', encoding='utf-8') as f:
            tax_content = f.read()

        # Step 1: Extract all defined taxonomy concepts using regex
        concepts = []
        for m in re.finditer(r'## <a id="[^"]+"></a>(TAX_[^:]+):\s*([^\n<]+)', tax_content):
            concepts.append({
                "id": m.group(1).strip(),
                "name": m.group(2).strip()
            })

        # Step 2: List all processed Markdown document files
        doc_files = [f for f in os.listdir(self.docs_dir) if f.endswith('.md')] if os.path.exists(self.docs_dir) else []

        # Step 3: Count how many times each concept appears across the documents
        link_counts = {c['name']: 0 for c in concepts}
        for dfile in doc_files:
            with open(os.path.join(self.docs_dir, dfile), 'r', encoding='utf-8') as df:
                dtext = df.read()
            for c in concepts:
                link_counts[c['name']] += dtext.count(c['name'])

        # Step 4: Identify orphans (0 mentions) and high-density hub nodes (3+ mentions)
        orphans = [c['name'] for c in concepts if link_counts.get(c['name'], 0) == 0]
        strong_nodes = [c['name'] for c in concepts if link_counts.get(c['name'], 0) >= 3]

        # Step 5: Compute the Knowledge Hygiene Score (Percentage)
        coverage = 0.0
        if concepts:
            coverage = round((len(concepts) - len(orphans)) / len(concepts) * 100, 2)

        # Build comprehensive report dictionary
        report = {
            "audited_at": datetime.now().isoformat(),
            "total_concepts": len(concepts),
            "total_documents": len(doc_files),
            "orphan_nodes_count": len(orphans),
            "orphans_list": orphans,
            "high_density_nodes": len(strong_nodes),
            "hygiene_score_percent": coverage
        }

        # Print audit findings to the terminal
        print(f"Total Taxonomy Concepts: {len(concepts)}")
        print(f"Total Document Files:  {len(doc_files)}")
        print(f"Orphan Nodes (0 links): {len(orphans)}")
        print(f"Knowledge Hygiene Score: {coverage}%")
        return report


if __name__ == "__main__":
    # Command-line argument parsing for flexible execution
    parser = argparse.ArgumentParser(description="KM Taxonomy Hygiene Auditor")
    parser.add_argument("--output-dir", type=str, default="./output_taxonomy", help="Output directory to audit")
    args = parser.parse_args()

    auditor = TaxonomyHygieneAuditor(args.output_dir)
    auditor.run_audit()
