---
name: pdf-translate-docx
description: "Translate academic PDFs to Chinese Word .docx with footnotes. Supports single articles and multi-chapter books. Uses MinerU layout.json for auto footnote extraction."
---

# pdf-translate-docx

## Bundled resources

| File | Purpose |
| --- | --- |
| `scripts/docx_helpers.py` | Footnote engine + formatting helpers |
| `scripts/fix_dict_quotes.py` | Fix SyntaxError from `"` inside Chinese dict values |
| `scripts/extract_chapter_from_layout.py` | Auto-extract footnotes + structure from MinerU layout.json |
| `scripts/build_docx_from_translation.py` | **Generic docx builder: _translation.txt + _data.py → _cn.docx (saves ~60% tokens)** |
| `scripts/cleanup_rename.py` | Post-translation cleanup + citation-format rename |
| `references/translation_standards.md` | Legal-academic translation rules — read before translating |
| `references/workflow.md` | Detailed templates, segments pattern, pitfall table |

---

## File organization rules

All translation output files go in the **same folder as the source PDF**, organized as:

```
<Book Folder>/
├── Original.pdf                          # Source PDF stays at root
├── 译文/
│   ├── contracts_ch1_cn.docx             # Per-chapter translations
│   ├── contracts_ch2_cn.docx
│   └── 【译文】【主题】Citation.docx      # Merged full-book translation
├── 中间文件/
│   ├── contracts_ch1_data.py             # Footnotes (per chapter)
│   ├── contracts_ch1_main.py             # Build scripts (per chapter)
│   └── contracts_merge.py               # Merge script
└── 素材文件/
    ├── layout.json                       # MinerU layout extraction
    └── MinerU_markdown_*.md              # MinerU markdown extraction
```

**Never** scatter files in `temp/` root. Keep everything co-located with the PDF.

---

## Workflow overview

### For single articles

1. Read PDF → extract text + footnotes
2. Write `_data.py` (footnotes, original language) + `_main.py` (inline Chinese translation)
3. Run `uv run _main.py` → generates `_cn.docx`

### For multi-chapter books (preferred workflow)

1. **MinerU extract** → get `layout.json` + `.md` (user may provide these)
2. **Auto-extract** footnotes + structure per chapter via `extract_chapter_from_layout.py`
3. **Parallel translate** — launch one agent per chapter, each writes `_data.py` + `_main.py` → `_cn.docx`
4. **Merge** all chapter docx files into one `【译文】` file

---

## Auto-extract from MinerU layout.json (recommended for books)

When `layout.json` is available from MinerU extraction, use the automated tool:

```bash
SKILL=/Users/zhiyuanqian/.lawvable/skills/pdf-translate-docx/scripts
uv run $SKILL/extract_chapter_from_layout.py layout.json \
    --pages 8-35 \
    --data-out 中间文件/ch1_data.py \
    --text-out 中间文件/ch1_structure.txt
```

This produces:
- `_data.py` — FOOTNOTES dict auto-extracted from `page_footnote` blocks (~60-80% coverage; fill gaps from PDF if needed)
- `_structure.txt` — ordered blocks with `=== TITLE ===` and `--- TEXT ---` markers, ready for translation

Block types from layout.json:

| Source | Type | Use |
| --- | --- | --- |
| `para_blocks` | `title` | Section headings → `add_heading()` |
| `para_blocks` | `text` / `list` | Body paragraphs → translate + `add_para()` |
| `discarded_blocks` | `page_footnote` | Footnotes → `_data.py` |
| `discarded_blocks` | `header` / `footer` / `page_number` | **IGNORED** |

This saves significant tokens: agents read `_structure.txt` instead of PDF pages.

---

## Footnote handling

**Footnotes are NOT translated.** Keep original-language text verbatim in `_data.py`.
Only the body text is translated. Footnotes are inserted by ID at the correct position.

If `_data.py` is already provided (e.g. from auto-extraction or prior work), reuse it directly.

---

## Inline translation (preferred approach)

**Write translated Chinese directly in the `_main.py` segments.** This is faster and avoids
intermediate txt files. Translate each paragraph and embed the Chinese text inline in
`add_para(doc, [...])` calls, marking footnote positions by ID.

`_main.py` template:

```python
import sys, os
SKILL_SCRIPTS = '/Users/zhiyuanqian/.lawvable/skills/pdf-translate-docx/scripts'
sys.path.insert(0, SKILL_SCRIPTS)
sys.path.insert(0, os.path.dirname(__file__))

from docx_helpers import (
    add_footnote, add_heading, fmt_para, _set_run_font,
    set_page_margins, FONT_SIZE_PT
)
from <slug>_data import FOOTNOTES
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = os.path.join(os.path.dirname(__file__), '..', '译文', '<slug>_cn.docx')


def add_para(doc, segments, first_line_pt=21,
             align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             bold=False, size_pt=FONT_SIZE_PT):
    p = doc.add_paragraph()
    fmt_para(p, size_pt=size_pt, bold=bold, align=align,
             first_line_pt=first_line_pt)
    for text, fn_id in segments:
        if text:
            run = p.add_run(text)
            _set_run_font(run, size_pt=size_pt, bold=bold)
        if fn_id is not None:
            add_footnote(p, fn_id, FOOTNOTES[fn_id], doc)
    return p


def build():
    doc = Document()
    set_page_margins(doc)
    # Title
    p = doc.add_paragraph()
    run = p.add_run('文章标题（中译）')
    _set_run_font(run, size_pt=16, bold=True)
    fmt_para(p, size_pt=16, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, first_line_pt=0)
    # Sections — translate body text inline; footnotes by ID (not translated)
    add_heading(doc, '一、引言', level=1)
    add_para(doc, [
        ('这里直接写中文翻译，遇到脚注标记处断开', 1),
        ('继续翻译后续文字……', None),
    ])
    doc.save(OUT)
    print(f'Saved: {OUT}')

if __name__ == '__main__':
    build()
```

---

## Parallel translation for multi-chapter books

For books with multiple chapters, launch **one agent per chapter** in parallel:

1. Each agent reads the chapter's markdown/structure + PDF pages for that chapter
2. Each agent writes its own `_data.py` + `_main.py` in `中间文件/`
3. Each agent generates `_cn.docx` in `译文/`
4. After all agents complete, run merge script to combine into one `【译文】` file

This parallelization dramatically reduces total translation time for large books.

---

## Merging chapters

After all chapters are translated, merge into a single docx:

```python
# contracts_merge.py — merges chapter docx files with footnote ID remapping
# Key: remap footnote IDs to avoid collisions between chapters
# Add page breaks between chapters
# See existing merge scripts for the full pattern
```

---

## add\_para segments pattern

| text | fn\_id | Effect |
| --- | --- | --- |
| '正文文字。' | None | Plain run |
| '引用前文字' | 3 | Run + footnote superscript 3 |
| None | 5 | Footnote ref only |

---

## Typography spec

| Element | Font | Size | Line | 段前/段后 |
| --- | --- | --- | --- | --- |
| 正文 | 宋体 / Times New Roman | 五号 10.5pt | x1.3 | 0.3行 |
| 脚注 | 宋体 / Times New Roman | 小五号 9pt | x1.1 | 0.1行 |
| 脚注序号 | — | — | — | 上标 |

Heading 1: 13.5pt bold centered · Heading 2: 12pt bold left

---

## Token-budget strategy

### Best: layout.json + _translation.txt (saves ~60% tokens)

Pre-process with zero-token scripts, agents only output pure translated text:

1. `extract_chapter_from_layout.py` → `_data.py` + `_structure.txt` (0 tokens)
2. Agent reads `_structure.txt`, writes `_translation.txt` with `{{FN:N}}` markers (only token cost)
3. `build_docx_from_translation.py` → `_cn.docx` (0 tokens)

`_translation.txt` format — agents output ONLY this:
```
===TITLE===
一、引言
---TEXT---
正文翻译……{{FN:1}}继续翻译……
---QUOTE---
引用段落翻译……{{FN:7}}
---TEXT---
下一段翻译……
```

### Good: inline _main.py approach

Write `_data.py` then `_main.py` with translated text inline in segments. More tokens but works without layout.json.

---

## Quick reference commands

```bash
SKILL=/Users/zhiyuanqian/.lawvable/skills/pdf-translate-docx/scripts

# 1. Auto-extract structure + footnotes from layout.json (0 tokens)
uv run $SKILL/extract_chapter_from_layout.py layout.json --pages 8-35 \
    --data-out 中间文件/ch1_data.py --text-out 中间文件/ch1_structure.txt

# 2. (Agent writes 中间文件/ch1_translation.txt — the only token cost)

# 3. Build docx from translation (0 tokens)
uv run $SKILL/build_docx_from_translation.py \
    --translation 中间文件/ch1_translation.txt \
    --data 中间文件/ch1_data.py \
    --output 译文/ch1_cn.docx \
    --title "章节标题" --author "作者"

# Fix quote escaping if needed
uv run $SKILL/fix_dict_quotes.py 中间文件/ch1_data.py --dict-name FOOTNOTES

# MinerU extract (precision mode only)
mineru-open-api extract <file.pdf> -o 素材文件/ --language en
```

---

## Cleanup and rename

```
SKILL=/Users/zhiyuanqian/.lawvable/skills/pdf-translate-docx
uv run $SKILL/scripts/cleanup_rename.py \
    --pdf    /path/to/original.pdf \
    --docx   译文/<slug>_cn.docx \
    --outdir 译文/ \
    --type   book \
    --topic  "合同法" \
    --citation "Douglas Baird (ed.), Contracts Stories, Foundation Press (2007)"
```

### Citation format rules

**Language is auto-detected** from PDF content. Override with `--lang en` or `--lang de`.

#### English (--lang en)

```
1 author:   Firstname Lastname, Title, Publisher (Year)
2 authors:  A Name & B Name, Title, Publisher (Year)
3 authors:  A Name, B Name & C Name, Title, Publisher (Year)
4+ authors: Firstname Lastname et al., Title, Publisher (Year)
editors:    ... (ed.) / (eds.)
journal:    Author(s), Article Title, Journal, Vol.X, p.X (Year)
```

#### German (--lang de) — standard Fußnotenzitierweise

```
Brox/Walker, Besonderes Schuldrecht, 35. Aufl., C.H.Beck, München 2011
H. Koziol, Titel, AcP 196 (1996) 593 ff.
```

Prepend 【主题】 via --topic flag. Final filenames:

```
【合同法】Douglas Baird (ed.), Contracts Stories, Foundation Press (2007).pdf
【译文】【合同法】Douglas Baird (ed.), Contracts Stories, Foundation Press (2007).docx
```
