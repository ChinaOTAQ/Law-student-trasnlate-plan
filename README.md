# Law Student Translate Plan

> 一套基于 Claude Code 的法学学术 PDF 全文翻译工作流，输出带页脚注的 Word .docx 文件。

---

## 目录

- [概述](#概述)
- [环境要求](#环境要求)
- [安装 Skill](#安装-skill)
- [使用方法](#使用方法)
  - [命令一：/translate（直接翻译）](#命令一translate直接翻译)
  - [命令二：/translate-ocr（OCR 精准模式）](#命令二translate-ocr-ocr-精准模式)
- [完整工作流](#完整工作流)
- [翻译逻辑与标准](#翻译逻辑与标准)
- [输出文件命名规则](#输出文件命名规则)
- [排版规格](#排版规格)
- [文件结构](#文件结构)

---

## 概述

本项目将学术 PDF（主要为英文/德文法学文献）全文翻译为中文，生成格式规范的 Word `.docx` 文件：

- 所有脚注转换为 **Word 页脚注**（非尾注），编号连续、上标格式
- 正文、脚注采用法学论文标准排版
- 翻译完成后自动清理中间文件，按**引用格式**重命名输出文件

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

```
/translate
```

触发词（任意一个均可）：
- `/translate`
- `翻译这个pdf`
- `全文翻译`
- `translate this paper`
- `pdf翻译成中文word`
- `翻译pdf`

**流程**：
```
读取 PDF → 提取正文+脚注 → 翻译 → 写 _data.py（脚注字典）→ 写 _main.py（构建器）→ 生成 .docx → 清理+重命名
```

### 命令二：`/translate-ocr`（OCR 精准模式）

**适用场景**：扫描件、图片 PDF、文字模糊、直接读取乱码

```
/translate-ocr
```

触发词（任意一个均可）：
- `/translate-ocr`
- `pdf不清晰`
- `扫描件翻译`
- `ocr翻译`
- `先转md再翻译`
- `pdf转md`

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
          读取 translation_standards.md
          （翻译规范，每次必读）
                     ↓
          写 temp/<slug>_data.py
          （FOOTNOTES 字典，所有脚注中译）
                     ↓
          uv run fix_dict_quotes.py
          （修复中文引号导致的语法错误）
                     ↓
          写 temp/<slug>_main.py
          （正文构建器，段落+脚注引用）
                     ↓
          uv run temp/<slug>_main.py
          （生成 temp/<slug>_cn.docx）
                     ↓
          uv run cleanup_rename.py
          （清理中间文件，重命名输出）
                     ↓
┌─────────────────────────────────────────────────────────┐
│  输出：                                                   │
│  <引用格式>.pdf                                           │
│  【译文】<引用格式>.docx                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 翻译逻辑与标准

翻译遵循 `references/translation_standards.md` 中的完整规范，核心原则如下：

### 1. 准确性优先
- 精准传达法律含义、逻辑层次和细微差别
- 原文有明显错误（笔误、引注错误）须在译文中用 `［译者注：……］` 标注修正

### 2. 消除翻译腔（最重要）
- 先完整理解原文结构，再用地道汉语重构
- 拆分复杂从句，冗长定语转为独立分句
- 禁止将英/德文语法结构直接平移到中文

### 3. 专业术语处理
- 使用学界公认译法（如 Corpus Iuris Civilis → 国法大全）
- 非中文专有名词在（）中标注原文
- 同一术语首次出现时用 `［译者注：……］` 说明译法选择

### 4. 引号规范
- **禁止**半角引号 `"` `"`
- 使用全角引号：`「」`（首选）、`『』`（嵌套引用）
- 书名用《》，篇名用〈〉

### 5. 脚注处理
- 所有原文脚注对应翻译，编号与原文一致
- 避免连续引用标注如 `[169][170]`（难以定位对应关系）
- OCR 可能有误，但脚注通常按顺序排列，可据此校正

---

## 输出文件命名规则

### 书籍

| 情形 | 格式 |
|------|------|
| 单一作者 | `【主题】Firstname Lastname, Title, Publisher (Year)` |
| 两位作者 | `【主题】A Name and B Name, Title, Publisher (Year)` |
| 三位及以上 | `【主题】Firstname Lastname et al., Title, Publisher (Year)` |
| 一位编者 | `【主题】Firstname Lastname (ed.), Title, Publisher (Year)` |
| 两位编者 | `【主题】A Name and B Name (eds.), Title, Publisher (Year)` |
| 三位及以上编者 | `【主题】Firstname Lastname et al. (eds.), Title, Publisher (Year)` |

### 期刊文章

```
Author(s), Article Title, Journal Name, Vol.X, p.X (Year)
```

### 最终文件名示例

```
【比较法】Ralf Michaels, The Functional Method of Comparative Law, Oxford (2006).pdf
【译文】【比较法】Ralf Michaels, The Functional Method of Comparative Law, Oxford (2006).docx
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
└── references/
    ├── translation_standards.md      # 完整翻译规范（每次翻译必读）
    └── workflow.md                   # 详细工作流模板与注意事项
```

---

## License

MIT
