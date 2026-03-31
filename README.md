# Law Student Translate Plan

> 一套基于 Claude Code 的法学学术 PDF 全文翻译工作流，输出带页脚注的 Word .docx 文件。支持**英语**和**德语**文献引用格式。

---

## 目录

- [概述](#概述)
- [环境要求](#环境要求)
- [安装 Skill](#安装-skill)
- [使用方法](#使用方法)
- [完整工作流](#完整工作流)
- [翻译逻辑与标准](#翻译逻辑与标准)
- [输出文件命名规则](#输出文件命名规则)
- [排版规格](#排版规格)
- [文件结构](#文件结构)
- [贡献者](#贡献者)

---

## 概述

本项目将学术 PDF（英文/德文法学文献）全文翻译为中文，生成格式规范的 Word `.docx` 文件：

- 所有脚注转换为 **Word 页脚注**（非尾注），编号连续、上标格式
- 正文、脚注采用法学论文标准排版
- 翻译完成后自动清理中间文件，按**引用格式**重命名输出文件
- 支持**英语**（`--lang en`）和**德语**（`--lang de`）两套引用命名规范

---

## 环境要求

| 依赖 | 说明 |
|------|------|
| [Claude Code](https://claude.ai/code) | AI 翻译引擎，需登录账号 |
| Python + [uv](https://github.com/astral-sh/uv) | 运行翻译脚本（`uv run`） |
| `python-docx` + `lxml` | 生成 Word 文件（uv 自动安装） |
| `mineru-open-api`（可选） | OCR 精准提取，用于扫描件/模糊 PDF |

安装 MinerU CLI（用于 `/translate-ocr` 命令）：
```bash
# macOS (Apple Silicon)
curl -L https://github.com/opendatalab/MinerU-Ecosystem/releases/latest/download/mineru-open-api_darwin_arm64.tar.gz | tar xz
sudo mv mineru-open-api /usr/local/bin/

# 配置 Token（从 https://mineru.net 获取）
echo "YOUR_TOKEN" | mineru-open-api auth
```

---

## 安装 Skill

下载 `pdf-translate-docx.skill` 文件，在 Claude Code 中安装：

```bash
claude skill install pdf-translate-docx.skill
```

或手动将 `pdf-translate-docx/` 文件夹复制到你的 Claude skills 目录（通常为 `~/.lawvable/skills/`）。

---

## 使用方法

在 Claude Code 中打开目标 PDF 所在目录，直接输入命令。

### 命令一：`/translate`（直接翻译）

**适用场景**：PDF 文字可选中（数字原生 PDF，文字清晰）

触发词（任意一个均可）：`/translate` · `翻译这个pdf` · `全文翻译` · `translate this paper` · `pdf翻译成中文word`

**流程**：
```
读取 PDF → 提取正文+脚注 → 翻译 → 写 _data.py → 写 _main.py → 生成 .docx → 清理+重命名
```

### 命令二：`/translate-ocr`（OCR 精准模式）

**适用场景**：扫描件、图片 PDF、文字模糊、直接读取乱码

触发词（任意一个均可）：`/translate-ocr` · `pdf不清晰` · `扫描件翻译` · `先转md再翻译` · `pdf转md`

**流程**：
```
MinerU 精准 OCR → 提取 Markdown → 翻译 → 写 _data.py → 写 _main.py → 生成 .docx → 清理+重命名
```

---

## 完整工作流

```
┌─────────────────────────────────────────────────────────┐
│                        输入 PDF                          │
└────────────────────┬────────────────────────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
     文字可选中              扫描件/模糊
   /translate              /translate-ocr
          │                     │
    直接读取 PDF          MinerU 精准 OCR
                               ↓
                        temp/extracted/*.md
          │                     │
          └──────────┬──────────┘
                     ↓
          读取 translation_standards.md（翻译规范）
                     ↓
          写 temp/<slug>_data.py（FOOTNOTES 脚注字典）
                     ↓
          uv run fix_dict_quotes.py（修复引号语法错误）
                     ↓
          写 temp/<slug>_main.py（正文构建器）
                     ↓
          uv run temp/<slug>_main.py → temp/<slug>_cn.docx
                     ↓
          uv run cleanup_rename.py --lang en|de
                     ↓
┌─────────────────────────────────────────────────────────┐
│  <引用格式>.pdf                                           │
│  【译文】<引用格式>.docx                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 翻译逻辑与标准

### 核心原则

| 原则 | 说明 |
|------|------|
| 准确性优先 | 精准传达法律含义、逻辑层次和细微差别 |
| 消除翻译腔 | 先理解原文结构，再用地道汉语重构；拆分复杂从句 |
| 忠于原文 | 不添加或删减信息；原文错误用 `［译者注：……］` 标注 |
| 专业术语 | 使用学界公认译法；非中文专有名词在（）中标注原文 |

### 引号规范

- **禁止**半角引号 `"` `"`
- 使用全角引号：`「」`（首选）、`『』`（嵌套引用）
- 书名用《》，篇名用〈〉

### 脚注处理

- 编号与原文一致，全部转为 Word 页脚注（非尾注）
- 避免连续引用标注如 `[169][170]`（难以定位对应关系）

---

## 输出文件命名规则

用 `--lang en`（默认）或 `--lang de` 选择引用格式，通过 `--topic` 添加 `【主题】`。

### 英语格式（--lang en）

| 情形 | 格式 |
|------|------|
| 单一作者 | `Firstname Lastname, Title, Publisher (Year)` |
| 两位作者 | `A Name and B Name, Title, Publisher (Year)` |
| 三位及以上 | `Firstname Lastname et al., Title, Publisher (Year)` |
| 编者 | `... (ed.)` / `... (eds.)` |
| 期刊文章 | `Author(s), Article Title, Journal, Vol.X, p.X (Year)` |

示例：
```
【比较法】Ralf Michaels, The Functional Method of Comparative Law, Oxford (2006).pdf
【译文】【比较法】Ralf Michaels, The Functional Method of Comparative Law, Oxford (2006).docx
```

### 德语格式（--lang de）

| 情形 | 格式 |
|------|------|
| 单一作者 | `Vorname Nachname, Titel, Aufl. Verlagsort Jahr` |
| 多位作者 | 作者间用 `/` 连接：`A/B, Titel, Stadt Jahr` |
| 编者 | `Vorname Nachname (Hrsg.), Titel, Stadt Jahr` |
| 期刊文章 | `Vorname Nachname, Titel, ZeitschriftAbk Jahr, S. X` |

> 与英语格式的三处关键区别：
> - 多作者用 `/` 而非 "and"（`Brox/Walker` 而非 `Brox and Walker`）
> - 出版地（城市）而非出版社名称；年份直接跟在城市后
> - 期刊引用：年份在前、页码在后，用 `S.` 而非 `p.`，无 `Vol.`

示例：
```
--lang de --edition "2. Aufl." --topic "比较法"
→ 【比较法】Ralf Michaels, Die Funktionsmethode, 2. Aufl. Tübingen 2006.pdf
→ 【译文】【比较法】Ralf Michaels, Die Funktionsmethode, 2. Aufl. Tübingen 2006.docx

--lang de（期刊）
→ Karl Larenz, Zur Struktur subjektiver Rechte, AcP 1977, S. 129.pdf
```

---

## 排版规格

| 元素 | 字体 | 字号 | 行距 | 段前/段后 |
|------|------|------|------|---------|
| 正文 | 宋体 / Times New Roman | 五号 10.5pt | 1.3× | 0.3行（≈4.1pt） |
| 脚注 | 宋体 / Times New Roman | 小五号 9pt | 1.1× | 0.1行（≈1.0pt） |
| 脚注序号 | — | 同脚注 | — | 上标 |
| 一级标题 | 宋体加粗 | 13.5pt | — | 居中 |
| 二级标题 | 宋体加粗 | 12pt | — | 左对齐 |

页边距：上下 2.54cm，左右 3.17cm

---

## 文件结构

```
pdf-translate-docx/
├── SKILL.md                          # Skill 定义（触发条件 + 工作流指引）
├── scripts/
│   ├── docx_helpers.py               # Word 脚注引擎 + 排版工具函数
│   ├── fix_dict_quotes.py            # 修复中文引号导致的 Python 语法错误
│   └── cleanup_rename.py             # 清理中间文件 + 按引用格式重命名
│                                     #   --lang en（英语）/ --lang de（德语）
│                                     #   --edition "X. Aufl."（德语版本号）
└── references/
    ├── translation_standards.md      # 完整翻译规范（每次翻译必读）
    └── workflow.md                   # 详细工作流模板与注意事项
```

---

## 贡献者

| 贡献者 | 角色 |
|--------|------|
| [@ChinaOTAQ](https://github.com/ChinaOTAQ) | 项目发起人、工作流设计、翻译规范制定 |
| [Claude](https://claude.ai/code) | Skill 开发、脚本实现、技术架构 |

---

## License

MIT
