#!/usr/bin/env python3
"""
cleanup_rename.py — post-translation cleanup.

Actions:
  1. Delete all intermediate temp files (_data.py, _main.py, extracted/, fix_quotes.py)
  2. Rename the translated .docx  → 【译文】<citation>.docx
  3. Rename the original .pdf     → <citation>.pdf
     (moved / copied to same output dir as docx)

Citation format rules
---------------------
Books
  Single author:
    【主题】Firstname Lastname, Title, Publisher (Year)
  Two authors:
    【主题】A Name and B Name, Title, Publisher (Year)
  2+ editors (no authors):
    【主题】A Name and B Name (eds.), Title, Publisher (Year)
  3+ authors → use first author + et al.:
    【主题】Firstname Lastname et al., Title, Publisher (Year)

Journal articles
  Author(s) [same rules], Article Title, Journal Name, Vol.X, p.X (Year)

Translated output gets 【译文】 prepended to the citation.

Usage
-----
  uv run cleanup_rename.py \\
      --pdf    /path/to/original.pdf \\
      --docx   temp/<slug>_cn.docx \\
      --outdir /path/to/output/ \\
      --type   book|article \\
      --citation "Stephen Bainbridge, Agency Partnerships & LLCs, Foundation Press (2023)" \\
      --topic  "代理、合伙、封闭公司"

  # Or interactive mode (no --citation):
  uv run cleanup_rename.py --pdf ... --docx ... --outdir ... --type book
"""

import argparse
import os
import shutil
import sys
import glob


# ── Citation helpers ──────────────────────────────────────────────────────────

def _sanitize(name: str) -> str:
    """Remove characters illegal in macOS/Windows filenames."""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, '')
    return name.strip()


def build_book_citation(authors: list[str], editors: list[str],
                        title: str, publisher: str,
                        year: str, topic: str,
                        lang: str = 'en',
                        edition: str = '') -> str:
    """
    Build book citation string.
    authors / editors: list of 'Firstname Lastname' strings.
    Pass authors OR editors (not both).

    English (lang='en'):
      1 author:   Firstname Lastname, Title, Publisher (Year)
      2 authors:  A and B, Title, Publisher (Year)
      3+:         Firstname Lastname et al., Title, Publisher (Year)
      editors:    ... (ed.) / (eds.)

    German (lang='de'):
      authors joined with '/':  Hans Brox/Wolf-Dietrich Walker, Titel, Aufl. Stadt Jahr
      editors:                  ... (Hrsg.)
      publisher = Verlagsort (city); edition = '44. Aufl.' etc.
    """
    if lang == 'de':
        if authors:
            names = '/'.join(authors)
            credit = names
        else:
            names = '/'.join(editors)
            credit = f'{names} (Hrsg.)'
        topic_part = f'【{topic}】' if topic else ''
        edition_part = f'{edition} ' if edition else ''
        # German format: Author, Titel, Aufl. Verlagsort Jahr
        return f'{topic_part}{credit}, {title}, {edition_part}{publisher} {year}'
    else:
        # English format
        if authors:
            if len(authors) == 1:
                names = authors[0]
            elif len(authors) == 2:
                names = f'{authors[0]} and {authors[1]}'
            else:
                names = f'{authors[0]} et al.'
            credit = names
        else:
            if len(editors) == 1:
                names = editors[0]
            elif len(editors) == 2:
                names = f'{editors[0]} and {editors[1]}'
            else:
                names = f'{editors[0]} et al.'
            suffix = '(ed.)' if len(editors) == 1 else '(eds.)'
            credit = f'{names} {suffix}'
        topic_part = f'【{topic}】' if topic else ''
        return f'{topic_part}{credit}, {title}, {publisher} ({year})'


def build_article_citation(authors: list[str],
                           title: str, journal: str,
                           volume: str, page: str,
                           year: str,
                           lang: str = 'en') -> str:
    """
    English: Author(s), Title, Journal, Vol.X, p.X (Year)
    German:  Author(s), Titel, Zeitschrift Jahr, S. X
             (no Vol.; year before page; S. not p.)
    """
    if lang == 'de':
        names = '/'.join(authors)
        return f'{names}, {title}, {journal} {year}, S. {page}'
    else:
        if len(authors) == 1:
            names = authors[0]
        elif len(authors) == 2:
            names = f'{authors[0]} and {authors[1]}'
        else:
            names = f'{authors[0]} et al.'
        return f'{names}, {title}, {journal}, Vol.{volume}, p.{page} ({year})'


# ── Cleanup ───────────────────────────────────────────────────────────────────

TEMP_PATTERNS = [
    'temp/*_data.py',
    'temp/*_main.py',
    'temp/fix_quotes.py',
    'temp/extracted/',
]


def cleanup_temp(workdir: str):
    """Delete known intermediate files under workdir."""
    removed = []
    for pattern in TEMP_PATTERNS:
        full = os.path.join(workdir, pattern)
        for match in glob.glob(full):
            if os.path.isdir(match):
                shutil.rmtree(match)
            else:
                os.remove(match)
            removed.append(match)
    return removed


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description='Post-translation cleanup and rename.')
    ap.add_argument('--pdf',      required=True,  help='Path to original PDF')
    ap.add_argument('--docx',     required=True,  help='Path to translated .docx')
    ap.add_argument('--outdir',   required=True,  help='Output directory for final files')
    ap.add_argument('--citation', default=None,
                    help='Full citation string (skip prompts)')
    ap.add_argument('--topic',    default='',
                    help='Book topic for 【…】 bracket (books only)')
    ap.add_argument('--type',     choices=['book', 'article'], default=None,
                    help='Document type (book or article)')
    ap.add_argument('--lang',     choices=['en', 'de'], default='en',
                    help='Citation language style: en (English) or de (German)')
    ap.add_argument('--edition',  default='',
                    help='Edition string for German books, e.g. "44. Aufl."')
    ap.add_argument('--no-cleanup', action='store_true',
                    help='Skip deleting intermediate temp files')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # ── Build citation if not provided ───────────────────────────────────────
    if args.citation:
        citation = args.citation
    else:
        doc_type = args.type or input('Type (book/article): ').strip()
        lang = args.lang
        if doc_type == 'book':
            if lang == 'de':
                sep = '/'
                raw_authors = input('Autoren (durch "/" getrennt, leer lassen für Herausgeber): ').strip()
                raw_editors = input('Herausgeber (durch "/" getrennt, leer lassen für Autoren): ').strip()
                title       = input('Titel: ').strip()
                publisher   = input('Verlagsort (Stadt): ').strip()
                year        = input('Jahr: ').strip()
                edition     = args.edition or input('Auflage (z.B. "44. Aufl.", leer lassen wenn keine): ').strip()
                topic       = args.topic or input('Thema für 【…】 (leer lassen zum Weglassen): ').strip()
                authors = [a.strip() for a in raw_authors.split('/') if a.strip()]
                editors = [e.strip() for e in raw_editors.split('/') if e.strip()]
                citation = build_book_citation(authors, editors, title, publisher,
                                               year, topic, lang='de', edition=edition)
            else:
                raw_authors = input('Authors (comma-separated, leave blank if editors): ').strip()
                raw_editors = input('Editors (comma-separated, leave blank if authors): ').strip()
                title       = input('Title: ').strip()
                publisher   = input('Publisher: ').strip()
                year        = input('Year: ').strip()
                topic       = args.topic or input('Topic for 【…】 (leave blank to omit): ').strip()
                authors = [a.strip() for a in raw_authors.split(',') if a.strip()]
                editors = [e.strip() for e in raw_editors.split(',') if e.strip()]
                citation = build_book_citation(authors, editors, title, publisher,
                                               year, topic, lang='en')
        else:  # article
            if lang == 'de':
                raw_authors = input('Autoren (durch "/" getrennt): ').strip()
                title       = input('Titel des Aufsatzes: ').strip()
                journal     = input('Zeitschrift: ').strip()
                volume      = ''  # not used in German style
                page        = input('Anfangsseite: ').strip()
                year        = input('Jahr: ').strip()
                authors = [a.strip() for a in raw_authors.split('/') if a.strip()]
                citation = build_article_citation(authors, title, journal,
                                                  volume, page, year, lang='de')
            else:
                raw_authors = input('Authors (comma-separated): ').strip()
                title       = input('Article title: ').strip()
                journal     = input('Journal name: ').strip()
                volume      = input('Volume: ').strip()
                page        = input('Starting page: ').strip()
                year        = input('Year: ').strip()
                authors = [a.strip() for a in raw_authors.split(',') if a.strip()]
                citation = build_article_citation(authors, title, journal,
                                                  volume, page, year, lang='en')

    safe_citation = _sanitize(citation)
    print(f'\nCitation: {citation}')

    # ── Rename / copy files ───────────────────────────────────────────────────
    pdf_dest  = os.path.join(args.outdir, safe_citation + '.pdf')
    docx_dest = os.path.join(args.outdir, '【译文】' + safe_citation + '.docx')

    shutil.copy2(args.pdf,  pdf_dest)
    shutil.copy2(args.docx, docx_dest)
    print(f'PDF  → {pdf_dest}')
    print(f'DOCX → {docx_dest}')

    # ── Cleanup intermediate files ────────────────────────────────────────────
    if not args.no_cleanup:
        workdir = os.path.dirname(os.path.abspath(args.pdf))
        removed = cleanup_temp(workdir)
        # also remove the intermediate docx if it differs from dest
        if os.path.abspath(args.docx) != os.path.abspath(docx_dest):
            try:
                os.remove(args.docx)
                removed.append(args.docx)
            except FileNotFoundError:
                pass
        if removed:
            print(f'Cleaned up {len(removed)} intermediate file(s).')

    print('\nDone.')


if __name__ == '__main__':
    main()
