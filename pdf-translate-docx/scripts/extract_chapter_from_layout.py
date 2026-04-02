#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Extract structured chapter content from MinerU layout.json.

Produces two files:
  1. _data.py  — FOOTNOTES dict (original language, not translated)
  2. _structure.txt — ordered list of blocks: TITLE / TEXT / FOOTNOTE_REF positions

This replaces the need to read PDF pages for footnotes and markdown for structure,
saving significant tokens in the translation workflow.

Usage:
    uv run extract_chapter_from_layout.py layout.json --pages 8-35 \\
        --data-out ch1_data.py --text-out ch1_structure.txt

Block types used:
  para_blocks:
    - title  → section headings (used for add_heading in docx)
    - text   → body paragraphs (translated, footnote refs inline)
    - list   → list items (treated as body text)
  discarded_blocks:
    - page_footnote → footnote content (extracted to _data.py)
    - header/footer/page_number → IGNORED
"""

import argparse
import json
import re
import sys


def extract_text(block):
    """Extract text from a MinerU block."""
    parts = []
    for key in ['lines', 'paras']:
        if key in block:
            items = (block[key] if key == 'lines'
                     else [l for para in block[key] for l in para.get('lines', [])])
            for line in items:
                for span in line.get('spans', []):
                    parts.append(span.get('content', ''))
    text = ''.join(parts).strip()
    # Clean up hyphenation at line breaks
    text = re.sub(r'(?<=[a-zA-Z])-\s*\n\s*', '', text)
    text = re.sub(r'\n', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def parse_footnote_id(text):
    """Parse footnote ID and content."""
    if text.startswith('*'):
        return '*', text[1:].strip()
    m = re.match(r'^(\d+[a-z]?)\s+(.+)', text, re.DOTALL)
    if m:
        return m.group(1), m.group(2).strip()
    return None, text


def extract_chapter(layout_path, page_start, page_end):
    """Extract structured chapter content.

    Returns:
        blocks: list of dicts with keys: type ('title'|'text'|'list'), content, page
        footnotes: dict mapping ID -> text
    """
    with open(layout_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    pages = data.get('pdf_info', data if isinstance(data, list) else [])

    blocks = []
    footnotes = {}

    for page in pages[page_start:page_end + 1]:
        page_idx = page.get('page_idx', 0)

        # Extract structured para_blocks
        for b in page.get('para_blocks', []):
            btype = b.get('type', 'text')
            if btype in ('image', 'table'):
                continue  # skip non-text blocks
            text = extract_text(b)
            if not text:
                continue
            blocks.append({
                'type': btype,  # 'title', 'text', 'list'
                'content': text,
                'page': page_idx,
            })

        # Extract footnotes from discarded_blocks
        for b in page.get('discarded_blocks', []):
            if b.get('type') != 'page_footnote':
                continue
            text = extract_text(b)
            if not text:
                continue
            fn_id, fn_text = parse_footnote_id(text)
            if fn_id is None:
                continue
            if fn_id in footnotes:
                footnotes[fn_id] += ' ' + fn_text
            else:
                footnotes[fn_id] = fn_text

    return blocks, footnotes


def write_data_py(footnotes, output_path):
    """Write FOOTNOTES dict."""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('# /// script\n')
        f.write('# requires-python = ">=3.10"\n')
        f.write('# dependencies = ["python-docx", "lxml"]\n')
        f.write('# ///\n')
        f.write('# Auto-extracted from MinerU layout.json\n\n')
        f.write('FOOTNOTES = {\n')

        def sort_key(k):
            if k == '*':
                return (-1, '')
            try:
                return (int(re.match(r'\d+', k).group()), k)
            except (ValueError, AttributeError):
                return (999999, k)

        for fn_id in sorted(footnotes.keys(), key=sort_key):
            text = footnotes[fn_id].replace('\\', '\\\\').replace('"', '\\"')
            if fn_id == '*' or not fn_id.isdigit():
                f.write(f'    "{fn_id}": "{text}",\n')
            else:
                f.write(f'    {fn_id}: "{text}",\n')

        f.write('}\n\n')
        f.write('if __name__ == "__main__":\n')
        f.write('    print(f"Footnotes: {len(FOOTNOTES)}")\n')
        f.write('    for k, v in FOOTNOTES.items():\n')
        f.write('        preview = v[:80] + "..." if len(v) > 80 else v\n')
        f.write('        print(f"  [{k}] {preview}")\n')

    print(f'Footnotes: {len(footnotes)} → {output_path}')


def write_structure(blocks, output_path):
    """Write structured content for translation reference.

    Format:
        === TITLE ===
        Section Name Here

        --- TEXT (p.10) ---
        Body paragraph text here with footnote markers like superscript numbers...

        --- LIST (p.11) ---
        List item text...
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        for b in blocks:
            btype = b['type'].upper()
            page = b['page']
            if btype == 'TITLE':
                f.write(f'\n=== TITLE (p.{page}) ===\n')
            else:
                f.write(f'\n--- {btype} (p.{page}) ---\n')
            f.write(b['content'] + '\n')

    print(f'Blocks: {len(blocks)} → {output_path}')
    # Stats
    from collections import Counter
    c = Counter(b['type'] for b in blocks)
    for t, n in c.most_common():
        print(f'  {t}: {n}')


def main():
    parser = argparse.ArgumentParser(
        description='Extract structured chapter from MinerU layout.json')
    parser.add_argument('layout', help='Path to layout.json')
    parser.add_argument('--pages', required=True,
                        help='Page range (0-based), e.g., "8-35"')
    parser.add_argument('--data-out', required=True,
                        help='Output _data.py path')
    parser.add_argument('--text-out', required=True,
                        help='Output _structure.txt path')

    args = parser.parse_args()

    start, end = args.pages.split('-')
    blocks, footnotes = extract_chapter(args.layout, int(start), int(end))

    write_data_py(footnotes, args.data_out)
    write_structure(blocks, args.text_out)


if __name__ == '__main__':
    main()
