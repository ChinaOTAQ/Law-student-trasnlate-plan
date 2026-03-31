---
name: pdf-translate-docx
description: >
  Translate an academic PDF fully into Chinese and produce a formatted Word
  .docx file with Word page-level footnotes (脚注). Two trigger commands:

  /translate — Direct PDF reading → translation → .docx.
  Use for clear text-selectable PDFs.
  Triggers on: "翻译这个pdf", "全文翻译", "/translate", "translate this paper",
  "pdf翻译成中文word", "翻译pdf"

  /translate-ocr — PDF via MinerU precision OCR → Markdown → translation → .docx.
  Use when PDF is scanned, blurry, or text extraction is unreliable.
  Triggers on: "pdf不清晰", "扫描件翻译", "/translate-ocr", "ocr翻译",
  "先转md再翻译", "转为md", "pdf转md", "先提取md"

  Both commands end with cleanup of intermediate files and renaming:
  PDF → citation-format.pdf, .docx → 【译文】citation-format.docx.
  Typography: 宋体/Times New Roman, 五号(10.5pt) 正文 1.3x, 小五号(9pt) 脚注 1.1x.
---

# pdf-translate-docx

## Bundled resources

| File | Purpose |
|------|---------|
| `scripts/docx_helpers.py` | Footnote engine + formatting helpers |
| `scripts/fix_dict_quotes.py` | Fix SyntaxError from `"` inside Chinese dict values |
| `scripts/cleanup_rename.py` | Post-translation cleanup + citation-format rename |
| `references/translation_standards.md` | Legal-academic translation rules — read before translating |
| `references/workflow.md` | Detailed templates, segments pattern, pitfall table |

---

## Command: /translate — Direct PDF to .docx

Use when PDF has selectable text (clear scan or born-digital).

### Steps

1. Read the PDF using `pdf-processing-anthropic` skill or Read tool.
   Extract: section structure, full body text with inline citation numbers, all footnotes.

2. Read `references/translation_standards.md`.

3. Write `temp/<slug>_data.py` (FOOTNOTES dict) then run fix:
```
SKILL=/Users/zhiyuanqian/.lawvable/skills/pdf-translate-docx
uv run $SKILL/scripts/fix_dict_quotes.py temp/<slug>_data.py --dict-name FOOTNOTES
```

4. Write `temp/<slug>_main.py` and build:
```
uv run temp/<slug>_main.py
```

5. Run cleanup + rename (see Cleanup section below).

---

## Command: /translate-ocr — PDF via Markdown to .docx

Use when PDF is scanned, blurry, image-only, or direct reading gives garbled text.

### Steps

1. Extract to Markdown via MinerU precision mode (never use flash-extract):
```
mineru-open-api extract <file.pdf> -o temp/extracted/
# For heavy scans add --ocr:
mineru-open-api extract <file.pdf> --ocr -o temp/extracted/
```
Read `temp/extracted/<name>.md` as the translation source.

2-5. Same as /translate steps 2-5.

---

## Translation file templates

`temp/<slug>_data.py`:
```python
FOOTNOTES = {
    1:  "脚注1中文译文。",
    2:  "脚注2，Zweigert与Kotz（注2），第33页。",
}
```

`temp/<slug>_main.py`:
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

OUT = os.path.join(os.path.dirname(__file__), '<slug>_cn.docx')


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
    p = doc.add_paragraph()
    run = p.add_run('文章标题（中译）')
    _set_run_font(run, size_pt=16, bold=True)
    fmt_para(p, size_pt=16, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, first_line_pt=0)
    add_heading(doc, '一、引言', level=1)
    add_para(doc, [('正文文字……', 1), ('更多文字……', None)])
    doc.save(OUT)
    print(f'Saved: {OUT}')

if __name__ == '__main__':
    build()
```

---

## Cleanup and rename

Run after .docx is verified correct. This script:
- Renames PDF → `<citation>.pdf`
- Renames docx → `【译文】<citation>.docx`
- Deletes all intermediate temp files (`_data.py`, `_main.py`, `extracted/`, etc.)

```
SKILL=/Users/zhiyuanqian/.lawvable/skills/pdf-translate-docx
uv run $SKILL/scripts/cleanup_rename.py \
    --pdf    /path/to/original.pdf \
    --docx   temp/<slug>_cn.docx \
    --outdir /path/to/output/ \
    --type   book \
    --topic  "代理、合伙、封闭公司" \
    --citation "Stephen Bainbridge, Agency Partnerships & LLCs, Foundation Press (2023)"
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

Textbooks — authors by last name, joined `/`; use `--edition "X. Aufl."`:
```
Brox/Walker, Besonderes Schuldrecht, 35. Aufl., C.H.Beck, München 2011
```

Journal articles — `ZeitschriftAbk Band (Jahr) Startseite ff.` (no S., no Vol.):
```
H. Koziol, Titel, AcP 196 (1996) 593 ff.
```

Festschrift / edited volume:
```
Claus-Wilhelm Canaris, Titel, in: Festschrift für Larenz, C.H.Beck, München 1983, S. 85
```

Editors use `(Hrsg.)`:
```
Bachmann/Roth (Hrsg.), Titel, C.H.Beck, München 2012
```

Prepend 【主题】 via --topic flag.

Final filenames:
```
【侵权法】Brox/Walker, Besonderes Schuldrecht, 35. Aufl., C.H.Beck, München 2011.pdf
【译文】【侵权法】Brox/Walker, Besonderes Schuldrecht, 35. Aufl., C.H.Beck, München 2011.docx

【比较法】Ralf Michaels, The Functional Method of Comparative Law, Oxford (2006).pdf
【译文】【比较法】Ralf Michaels, The Functional Method of Comparative Law, Oxford (2006).docx
```

---

## add_para segments pattern

| text | fn_id | Effect |
|------|-------|--------|
| '正文文字。' | None | Plain run |
| '引用前文字' | 3 | Run + footnote superscript 3 |
| None | 5 | Footnote ref only |

---

## Typography spec

| Element | Font | Size | Line | 段前/段后 |
|---------|------|------|------|---------|
| 正文 | 宋体 / Times New Roman | 五号 10.5pt | x1.3 | 0.3行 |
| 脚注 | 宋体 / Times New Roman | 小五号 9pt | x1.1 | 0.1行 |
| 脚注序号 | — | — | — | 上标 |

Heading 1: 13.5pt bold centered · Heading 2: 12pt bold left

---

## Token-budget strategy

Long articles (>100 footnotes): write _data.py first → fix → verify → write _main.py section by section.
Details: references/workflow.md · Rules: references/translation_standards.md
