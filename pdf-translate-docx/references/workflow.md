# pdf-translate-docx — Detailed Workflow Reference

## File layout produced per article

```
temp/
  <article>_data.py       # FOOTNOTES dict  (id → original-language text, NOT translated)
  <article>_main.py       # Document builder: inline Chinese translation + footnotes by ID
  <article>_cn.docx       # Final output
```

The skill's `docx_helpers.py` is imported from the skill's `scripts/` directory — add it to `sys.path`.

---

## Phase 1 — Read the PDF

Use the `pdf-processing-anthropic` skill (or Read tool) to extract full text.
Identify:
- Article title, author, publication info
- Section structure (headings and sub-headings)
- Every footnote/endnote: number → full citation text

---

## Phase 2 — Write `<article>_data.py`

**Footnotes are NOT translated.** Keep original-language citation text verbatim.
If `_data.py` is already provided (e.g. from OCR or prior extraction), reuse it directly.

Structure:
```python
#!/usr/bin/env python3
FOOTNOTES = {
    1:  "K. Popper, op. cit., p. 27, 42.",
    2:  "F. de Saussure, Cours de linguistique générale, Paris, Payot, 1916, p. 33.",
    # ...
    "192a": "Special non-integer key example.",
}
if __name__ == '__main__':
    print(len(FOOTNOTES))
```

**Critical:** Text may contain ASCII `"` characters from quoted passages.
All values must use escaped inner quotes: `"He said \"hello\"."` — OR run `fix_dict_quotes.py` after writing.

Run fix if needed:
```bash
uv run <skill_scripts>/fix_dict_quotes.py temp/<article>_data.py --dict-name FOOTNOTES
```

---

## Phase 3 — Write `<article>_main.py`

Template structure:
```python
#!/usr/bin/env python3
import sys, os
# ── Import docx_helpers from skill scripts dir ──────────────────────────────
SKILL_SCRIPTS = '/path/to/.lawvable/skills/pdf-translate-docx/scripts'
sys.path.insert(0, SKILL_SCRIPTS)
sys.path.insert(0, os.path.dirname(__file__))

from docx_helpers import (
    add_footnote, add_body_para, add_heading, fmt_para,
    _set_run_font, set_page_margins,
    FONT_SIZE_PT, FONT_NAME
)
from <article>_data import FOOTNOTES
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT = os.path.join(os.path.dirname(__file__), '<article>_cn.docx')


def add_para(doc, segments, first_line_pt=21,
             align=WD_ALIGN_PARAGRAPH.JUSTIFY,
             bold=False, size_pt=FONT_SIZE_PT):
    """
    segments: list of (text_str_or_None, fn_id_or_None)
    Builds one paragraph with interleaved text runs and footnote refs.
    """
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

    # ── Title ────────────────────────────────────────────────────────
    p = doc.add_paragraph()
    run = p.add_run('文章中文标题')
    _set_run_font(run, size_pt=16, bold=True)
    fmt_para(p, size_pt=16, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, first_line_pt=0)

    # ── Body sections ────────────────────────────────────────────────
    # Translate body text INLINE in segments; footnotes by ID only (not translated)
    add_heading(doc, '一、引言', level=1)
    add_para(doc, [
        ('这里直接写中文翻译，遇到脚注标记处断开', 1),  # footnote 1 inserted here
        ('继续翻译后续文字……', None),                    # no footnote
    ])
    # ... repeat for every section

    doc.save(OUT)
    print(f'Saved: {OUT}')


if __name__ == '__main__':
    build()
```

Run:
```bash
uv run temp/<article>_main.py
```

---

## Paragraph `segments` pattern

Each call to `add_para` takes a list of `(text, fn_id)` tuples:

| text | fn_id | Effect |
|------|-------|--------|
| `'Some text.'` | `None` | Plain run, no footnote |
| `'Before cite'` | `3` | Text run, then footnote ref ³ appended |
| `None` | `5` | Footnote ref only (rare) |

Footnote refs appear **immediately after** the preceding text run — place the tuple at the exact inline citation point.

---

## Formatting defaults (docx_helpers.py)

| Property | Value |
|----------|-------|
| Font | 宋体 (SimSun) |
| Size | 10.5 pt (5号) |
| Line spacing | ×1.3 (WD_LINE_SPACING.MULTIPLE) |
| Space before/after | 4.1 pt (0.30行) |
| Body first-line indent | 21 pt (~2 Chinese chars) |
| Heading 1 | 13.5 pt, bold, centered, no indent |
| Heading 2 | 12 pt, bold, left, no indent |
| Footnote text | 9 pt (18 half-pts), 宋体 |

To override, pass `size_pt=`, `bold=`, `align=`, or `first_line_pt=` to `add_para` / `fmt_para`.

---

## Token budget guidance

**Preferred (inline):** Write `_data.py` (original footnotes verbatim, no translation) then write `_main.py` with translated Chinese body text directly in `add_para` segments. This avoids intermediate files and is the fastest approach.

For long articles (>100 footnotes), split work across two files:
- `_data.py` — FOOTNOTES dict only (original language, not translated)
- `_main.py` — imports data, builds document with inline Chinese translation

This keeps each file within context and avoids token-limit cutoffs mid-write.

---

## Common pitfalls

| Problem | Cause | Fix |
|---------|-------|-----|
| `SyntaxError: invalid character '，'` | Chinese text contains ASCII `"` inside a `"…"` string | Run `fix_dict_quotes.py` |
| Footnotes appear as endnotes | footnotes.xml part not linked | Ensure `add_footnote` is called (it auto-creates the part) |
| East-Asian font not applied | `_set_run_font` not called on run | Always call `_set_run_font` after `p.add_run()` |
| Footnote IDs duplicate | fn_id reused | Use a strictly incrementing counter or the dict key directly |
