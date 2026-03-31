#!/usr/bin/env python3
"""
cleanup_rename.py — post-translation cleanup.

Actions:
  1. Delete all intermediate temp files (_data.py, _main.py, extracted/, fix_quotes.py)
  2. Rename the translated .docx  → 【译文】<citation>.docx
  3. Rename the original .pdf     → <citation>.pdf
     (moved / copied to same output dir as docx)

Language is auto-detected from PDF content; override with --lang en|de.

Citation format rules
---------------------
English (--lang en)
  1 author:   Firstname Lastname, Title, Publisher (Year)
  2 authors:  A Name & B Name, Title, Publisher (Year)
  3 authors:  A Name, B Name & C Name, Title, Publisher (Year)
  4+ authors: Firstname Lastname et al., Title, Publisher (Year)
  editors:    ... (ed.) / (eds.)
  journal:    Author(s), Article Title, Journal, Vol.X, p.X (Year)

German (--lang de)  — based on standard German Fußnotenzitierweise
  Textbook:
    Nachname/Nachname, Titel, X. Aufl., Verlag, Verlagsort Jahr
    e.g. Brox/Walker, Besonderes Schuldrecht, 35. Aufl., C.H.Beck, München 2011
  Journal article:
    Vorname Nachname, Titel, ZeitschriftAbk Band (Jahr) Startseite ff.
    e.g. H. Koziol, Titel, AcP 196 (1996) 593 ff.
  Festschrift / edited volume:
    Vorname Nachname, Titel, in: Festschrift für X, Verlagsort: Verlag, Jahr, S. X
  Commentary:
    KommentarName/Autor, § X, X. Aufl., Verlagsort: Verlag, Jahr, Rn. X
  Editors:   Nachname/Nachname (Hrsg.), Titel, Verlag, Verlagsort Jahr

Translated output gets 【译文】 prepended to the citation.

Usage
-----
  # English book
  uv run cleanup_rename.py \\
      --pdf    /path/to/original.pdf \\
      --docx   temp/<slug>_cn.docx \\
      --outdir /path/to/output/ \\
      --type   book --lang en \\
      --citation "Stephen Bainbridge, Agency Partnerships & LLCs, Foundation Press (2023)" \\
      --topic  "代理、合伙、封闭公司"

  # German textbook
  uv run cleanup_rename.py \\
      --pdf    /path/to/original.pdf \\
      --docx   temp/<slug>_cn.docx \\
      --outdir /path/to/output/ \\
      --type   book --lang de \\
      --edition "35. Aufl." \\
      --citation "Brox/Walker, Besonderes Schuldrecht, 35. Aufl., C.H.Beck, München 2011"
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


def _en_author_names(people: list[str]) -> str:
    """
    English name joining rules:
      1:  Firstname Lastname
      2:  A & B
      3:  A, B & C
      4+: Firstname Lastname et al.
    """
    if len(people) == 1:
        return people[0]
    elif len(people) == 2:
        return f'{people[0]} & {people[1]}'
    elif len(people) == 3:
        return f'{people[0]}, {people[1]} & {people[2]}'
    else:
        return f'{people[0]} et al.'


def build_book_citation(authors: list[str], editors: list[str],
                        title: str, publisher: str,
                        year: str, topic: str,
                        lang: str = 'en',
                        edition: str = '') -> str:
    """
    Build book citation string for file naming.

    English (lang='en'):
      publisher = publisher name, year in parentheses at end.
    German (lang='de'):
      publisher = "Verlag, Verlagsort" or just Verlagsort;
      edition = "X. Aufl." inserted before publisher;
      authors joined with '/'.
    """
    topic_part = f'【{topic}】' if topic else ''

    if lang == 'de':
        if authors:
            credit = '/'.join(authors)
        else:
            credit = '/'.join(editors) + ' (Hrsg.)'
        edition_part = f', {edition}' if edition else ''
        return f'{topic_part}{credit}, {title}{edition_part}, {publisher} {year}'
    else:
        if authors:
            credit = _en_author_names(authors)
        else:
            people = editors
            names = _en_author_names(people)
            suffix = '(ed.)' if len(people) == 1 else '(eds.)'
            credit = f'{names} {suffix}'
        return f'{topic_part}{credit}, {title}, {publisher} ({year})'


def build_article_citation(authors: list[str],
                           title: str, journal: str,
                           volume: str, page: str,
                           year: str,
                           lang: str = 'en') -> str:
    """
    English: Author(s), Title, Journal, Vol.X, p.X (Year)
    German:  Author(s), Titel, ZeitschriftAbk Band (Jahr) Seite ff.
             e.g. H. Koziol, Titel, AcP 196 (1996) 593 ff.
             (Band = volume; Jahr in parentheses after band; S. prefix omitted in standard form)
    """
    if lang == 'de':
        names = '/'.join(authors)
        band_part = f'{volume} ({year}) ' if volume else f'({year}) '
        return f'{names}, {title}, {journal} {band_part}{page} ff.'
    else:
        names = _en_author_names(authors)
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
                    help='Topic for 【…】 bracket')
    ap.add_argument('--type',     choices=['book', 'article'], default=None,
                    help='Document type (book or article)')
    ap.add_argument('--lang',     choices=['en', 'de'], default='en',
                    help='Citation style: en (English) or de (German). '
                         'Auto-detected from PDF content if not set.')
    ap.add_argument('--edition',  default='',
                    help='Edition for German books, e.g. "35. Aufl."')
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
                raw_authors = input('Autoren (durch "/" getrennt, leer = Hrsg.): ').strip()
                raw_editors = input('Herausgeber (durch "/" getrennt, leer = Autoren): ').strip()
                title       = input('Titel: ').strip()
                publisher   = input('Verlag, Verlagsort (z.B. "C.H.Beck, München"): ').strip()
                year        = input('Jahr: ').strip()
                edition     = args.edition or input('Auflage (z.B. "35. Aufl.", leer = keine): ').strip()
                topic       = args.topic or input('Thema für 【…】 (leer = weglassen): ').strip()
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
                journal     = input('Zeitschrift (Abkürzung, z.B. AcP, NJW): ').strip()
                volume      = input('Band (Nummer, z.B. 196): ').strip()
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
