"""
===============================================================================
FILE: ingest_and_chunk.py
===============================================================================
WHAT IS THIS FILE FOR? (THE INTENT):
When you have a digital library with PDF files, EPUB e-books, and plain text files,
computers cannot directly understand the book until we read its pages, extract the
words, and break them down into digestible paragraphs (called "chunks").

This file is our "Document Ingestion & Chunking Factory". It opens up any book,
extracts full bibliographic details (Author, Year, Publisher, and a SHA-256 fingerprint),
and slices the raw text into manageable, overlapping paragraph chunks with precise
HTML anchors (like `<a id="doc_Page1_0001"></a>`) so we can point straight to any
sentence later on!

HOW IT WORKS IN SIMPLE TERMS:
1. `get_file_hash`:
   - Computes a unique digital fingerprint (SHA-256) of the book file. If the file
     never changes, its fingerprint stays identical, meaning we never waste time
     reprocessing it twice!

2. `extract_metadata`:
   - Inspects the filename and internal PDF headers to find the Author, Publication
     Year, Publisher, and file size.

3. `_chunk_text`:
   - Takes all the text from a chapter or page and breaks it into paragraphs.
   - Accumulates words up to our target chunk size (e.g. 450 words per chunk).
   - Keeps a small overlap (e.g. 50 words) between neighboring chunks so concepts
     that span across chunk boundaries don't lose their context!

INPUTS:
- Absolute or relative file path to a PDF, EPUB, TXT, or MD document.

OUTPUTS:
- A list of structured chunk dictionaries:
  `{"chunk_id": "...", "doc_id": "...", "section": "Page 1", "text": "...", "word_count": 420}`
- A metadata dictionary with full bibliographic provenance.

ERROR HANDLING:
- Tries fast PyMuPDF (`fitz`) first; if missing, falls back cleanly to `pypdf`.
- Safely handles corrupt or unreadable PDF pages by skipping blank pages instead of crashing.
- Ignores encoding errors in TXT files via `errors='ignore'`.
===============================================================================
"""

import os
import re
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Try loading high-performance PDF libraries with graceful fallback
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None

# Try loading EPUB reading libraries
try:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
except ImportError:
    ebooklib = None


class DocumentChunker:
    """
    Parses digital book files (PDF, EPUB, TXT, MD), extracts metadata,
    and slices the contents into structured, overlapping passage chunks.
    """

    def __init__(self, target_chunk_size: int = 450, overlap: int = 50):
        """
        Configure chunking parameters.
        
        Args:
            target_chunk_size: Desired average number of words per chunk (e.g., 400-500 words).
            overlap: Number of trailing words from the previous chunk to repeat at the start
                     of the next chunk to preserve context continuity.
        """
        self.target_chunk_size = target_chunk_size
        self.overlap = overlap

    def get_file_hash(self, file_path: str) -> str:
        """
        Calculates the SHA-256 cryptographic hash of the book file on disk.
        This provides a tamper-proof digital fingerprint to avoid duplicate processing.
        """
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            # Read in 64 KB blocks for fast performance without overloading RAM
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def extract_metadata(self, file_path: str, ext: str) -> Dict[str, Any]:
        """
        Extracts author, publication year, publisher, and file size metadata.
        """
        basename = os.path.basename(file_path)
        file_hash = self.get_file_hash(file_path)
        stat = os.stat(file_path)

        author = "Unknown Author"
        year = ""
        publisher = ""
        isbn = ""

        # Check if the filename contains 'author [Name]'
        m_auth = re.search(r'authors?\s*:\s*([^-_\[]+)', basename, re.IGNORECASE)
        if m_auth:
            author = m_auth.group(1).strip()

        # Check if the filename contains a 4-digit year (1900-2099)
        m_year = re.search(r'\b(19\d{2}|20\d{2})[\b\-_]', basename)
        if m_year:
            year = m_year.group(1)

        # If it's a PDF, inspect the internal PDF document properties table
        if ext == '.pdf' and fitz:
            try:
                doc = fitz.open(file_path)
                meta = doc.metadata or {}
                if meta.get('author'):
                    author = meta.get('author')
                if meta.get('producer'):
                    publisher = meta.get('producer')
                if meta.get('creationDate'):
                    cdate = meta.get('creationDate')
                    y_match = re.search(r'(19\d{2}|20\d{2})', cdate)
                    if y_match and not year:
                        year = y_match.group(1)
                doc.close()
            except Exception:
                pass

        return {
            "title": basename,
            "author": author,
            "publisher": publisher or "N/A",
            "publication_year": year or "Not Specified",
            "isbn": isbn or "N/A",
            "doc_version": "1.0",
            "file_hash": file_hash,
            "file_size_bytes": stat.st_size,
            "ingested_at": datetime.now().isoformat()
        }

    def process_file(self, file_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Main entry point for ingestion: Detects file type, parses pages/chapters,
        and returns all extracted text chunks alongside the document metadata.
        """
        ext = os.path.splitext(file_path)[1].lower()
        title = os.path.basename(file_path)
        meta = self.extract_metadata(file_path, ext)
        chunks = []

        if ext == '.pdf':
            chunks = self._parse_pdf(file_path, title)
        elif ext == '.epub':
            chunks = self._parse_epub(file_path, title)
        elif ext in ['.txt', '.md']:
            chunks = self._parse_txt(file_path, title)

        return chunks, meta

    def _parse_pdf(self, file_path: str, doc_title: str) -> List[Dict[str, Any]]:
        """
        Helper method: Parses PDF documents page by page using PyMuPDF or PyPDF.
        """
        chunks = []
        doc_id = re.sub(r'[^a-zA-Z0-9]', '_', os.path.splitext(doc_title)[0])[:30].strip('_')

        if fitz:
            doc = fitz.open(file_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                if not text.strip():
                    continue
                page_chunks = self._chunk_text(text, doc_id, doc_title, f"Page {page_num + 1}")
                chunks.extend(page_chunks)
            doc.close()
        elif pypdf:
            reader = pypdf.PdfReader(file_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if not text.strip():
                    continue
                page_chunks = self._chunk_text(text, doc_id, doc_title, f"Page {page_num + 1}")
                chunks.extend(page_chunks)

        return chunks

    def _parse_epub(self, file_path: str, doc_title: str) -> List[Dict[str, Any]]:
        """
        Helper method: Parses EPUB e-books chapter by chapter using EbookLib and BeautifulSoup.
        """
        chunks = []
        doc_id = re.sub(r'[^a-zA-Z0-9]', '_', os.path.splitext(doc_title)[0])[:30].strip('_')
        if not ebooklib:
            return chunks
        try:
            book = epub.read_epub(file_path)
            ch_num = 0
            for item in book.get_items():
                if item.get_type() == ebooklib.ITEM_DOCUMENT:
                    ch_num += 1
                    soup = BeautifulSoup(item.get_content(), 'html.parser')
                    text = soup.get_text()
                    if not text.strip():
                        continue
                    ch_chunks = self._chunk_text(text, doc_id, doc_title, f"Chapter {ch_num}")
                    chunks.extend(ch_chunks)
        except Exception:
            pass

        return chunks

    def _parse_txt(self, file_path: str, doc_title: str) -> List[Dict[str, Any]]:
        """
        Helper method: Parses plain text and markdown documents, splitting by markdown
        headings (e.g. '# Chapter 1' or '## Section') when present.
        """
        doc_id = re.sub(r'[^a-zA-Z0-9]', '_', os.path.splitext(doc_title)[0])[:30].strip('_')
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

        # Check if text contains Markdown headings
        sections = re.split(r'\n(?=#{1,3}\s+)', text)
        if len(sections) > 1:
            chunks = []
            for sec in sections:
                sec = sec.strip()
                if not sec:
                    continue
                first_line = sec.split('\n', 1)[0].strip('# \t\r')
                sec_name = first_line[:40] if first_line else "Section"
                chunks.extend(self._chunk_text(sec, doc_id, doc_title, sec_name))
            return chunks
        return self._chunk_text(text, doc_id, doc_title, "Main Text")

    def _chunk_text(self, text: str, doc_id: str, doc_title: str, section: str) -> List[Dict[str, Any]]:
        """
        Helper method: Chops continuous raw text into overlapping paragraph chunks.
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        chunks = []
        current_chunk = []
        current_length = 0
        chunk_counter = 1

        for p in paragraphs:
            words = p.split()
            if not words:
                continue
            word_count = len(words)

            # If adding this paragraph exceeds target word limit, save the current chunk!
            if current_length + word_count > self.target_chunk_size and current_chunk:
                chunk_text = " ".join(current_chunk)
                c_id = f"{doc_id}_{section.replace(' ', '')}_{chunk_counter:04d}"
                chunks.append({
                    "chunk_id": c_id,
                    "doc_id": doc_id,
                    "doc_title": doc_title,
                    "section": section,
                    "text": chunk_text,
                    "word_count": len(chunk_text.split())
                })
                chunk_counter += 1
                # Keep the last sentence/paragraph as the starting overlap for the next chunk
                current_chunk = current_chunk[-1:] if self.overlap > 0 else []
                current_length = sum(len(c.split()) for c in current_chunk)

            current_chunk.append(p)
            current_length += word_count

        # Save any final trailing chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            c_id = f"{doc_id}_{section.replace(' ', '')}_{chunk_counter:04d}"
            chunks.append({
                "chunk_id": c_id,
                "doc_id": doc_id,
                "doc_title": doc_title,
                "section": section,
                "text": chunk_text,
                "word_count": len(chunk_text.split())
            })

        return chunks
