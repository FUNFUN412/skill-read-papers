<div align="center">

# 📖 skill-reading-papers

### 让 Agent 陪你逐段读懂论文，把高光和问题变成可持续更新的三栏精读稿

[![Agent Skill](https://img.shields.io/badge/Agent-Skill-111827?style=flat-square&logo=openai&logoColor=white)](SKILL.md)
[![LaTeX](https://img.shields.io/badge/LaTeX-XeLaTeX-008080?style=flat-square&logo=latex&logoColor=white)](assets/latex-reader/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](requirements.txt)
[![License](https://img.shields.io/github/license/FUNFUN412/skill-reading-papers?style=flat-square)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/FUNFUN412/skill-reading-papers?style=flat-square&logo=github)](https://github.com/FUNFUN412/skill-reading-papers/stargazers)

基于真实论文协作精读过程整理的 **Agent Skill + LaTeX 模板 + PDF 标注工具**。
从英文原文、中文对照到右栏问答，交付可编辑的 `.tex` 和实际编译的 `.pdf`。

[🚀 一键部署](#-小白一键部署) ·
[🧭 核心能力](#-核心能力) ·
[📦 手动安装](#-手动安装) ·
[💬 使用方法](#-如何使用) ·
[🧪 验证](#-工具与验证)

</div>

---

## ✨ 核心能力

| 能力 | 说明 |
|---|---|
| 📄 **三栏双语精读** | 左英文、中中文、右笔记；英中每个自然段开头对应 |
| 🖼️ **图表公式保真** | 独立公式和原图跨左中两列，仅放一份，保留内部编号 |
| 🖍️ **原生高光回写** | 将 PDF 高光定位到源文与译文，写成可编辑 LaTeX 高光 |
| 💬 **定位问答** | 深蓝问题、深红简答，同框，通过横竖折线连到中文对应处 |
| 📏 **长解答独立排版** | 解答可以长于源段；不会把左中正文撑成大片空白 |
| 🧮 **公式详细解释页** | 从符号和基础概率讲起，给推导、数值例子与适用条件 |
| 🔢 **插页不打乱正文编号** | 详解页独立页眉、不占正文页码，区分物理页和正文页码 |
| 🤝 **多 Agent 协作** | 分章节翻译、数学复核、独立视觉检查；明确文件所有权 |
| 🔁 **连续阅读与更新** | 保存标注原件和稳定源块 ID，逐轮处理新问题并去除重复解答 |

> [!TIP]
> 默认采用横向 A4、约 40% / 40% / 20% 列宽。已有项目沿用你的设置，所有版式都可按要求调整。只问一个概念时，也可以直接讲解。

---

## 🧩 工作流程

```mermaid
flowchart LR
    A[论文 PDF 或链接] --> B[核对版本与源文分块]
    B --> C[分章节翻译与公式复核]
    C --> D[三栏 LaTeX 与 PDF]
    D --> E[用户阅读并高光或备注]
    E --> F[保存原件与导入标注]
    F --> G[双语高光和定位问答]
    G --> H[必要时添加详细解释页]
    H --> I[编译与视觉核验]
    I --> D
```

### 📐 默认成稿约定

| 项目 | 规则 |
|---|---|
| 正文 | 不加段落框、不写列标题；只要求段首对齐 |
| 分割线 | 保留页眉横线，加深中文与笔记之间的分界线 |
| 正文页眉 | 论文题目与日期 |
| 纯高光 | 只标英文与对应中文，不擅自写答案 |
| 详细解释页 | 深红内容，重点加粗；页眉“详细解释页”，不编号 |
| 已有详细解答 | 右栏保留定位链接，避免重复大段答案 |
| 参考文献 | 默认保留；你明确要求后再去除文献引用 |

---

## 🚀 小白一键部署

把下面整段发送给有文件和终端能力的 Agent。它会检查依赖、安装技能并用仓库自带的原创示例完成真实编译。

<details>
<summary><b>📋 点击展开：复制给 Agent 的部署提示词</b></summary>

```text
请帮我部署 https://github.com/FUNFUN412/skill-reading-papers 中的 skill-reading-papers。

要求：
1. 检查当前 Agent 的技能目录及是否已经安装；已有版本先查看本地修改，不覆盖我的文件。
2. 将仓库安装到当前 Agent 的全局 skills 目录。Codex 可手动克隆到 ~/.codex/skills/skill-reading-papers；支持 npx skills 时也可用它安装。
3. 检查 Python 3.10+，在独立虚拟环境安装 requirements.txt。使用该环境运行 python -m unittest discover -s tests -v，确认真实测试通过。
4. 检查 XeLaTeX、latexmk、ctex/Fandol 与模板所需包。缺失时按当前系统补齐实际缺项，避免改动无关配置。
5. 将 assets/latex-reader 复制到技能目录之外的临时测试目录，用 latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex 实际编译，直到坐标稳定。
6. 查看编译 PDF，核对三栏、双语高光、长备注、详细解释页及正文页码恢复。测试使用仓库自带的原创例子，不需要上传我的论文。
7. 最后告诉我安装位置、使用方式、测试与编译结果，以及尚未完成的依赖。不要只给安装说明，也不要把生成的阅读材料上传到 GitHub。
```

</details>

---

## 📦 依赖

| 依赖 | 用途 |
|---|---|
| 支持 Skill 的 Agent | 阅读、翻译、回答问题与操作本地项目 |
| Python 3.10+ 与 PyMuPDF | PDF 标注导入和机器检查 |
| XeLaTeX 与中文字体包 | 编译双语 LaTeX |
| latexmk | 推荐，管理多遍编译与坐标收敛 |
| Git | 克隆和更新仓库 |

推荐使用 TeX Live、MacTeX，或配齐依赖的 TinyTeX。模板包清单与宏接口见 [排版指南](references/latex-layout.md)。

子 Agent 不是硬性依赖；支持时可并行翻译和复核，不支持时按同样职责串行处理。扫描件还需可用的 OCR 工具。本技能不要求 Scholar MCP、飞书账号或付费 API。

---

## 🛠️ 手动安装

### 1️⃣ 安装 Skill

支持 [Skills CLI](https://github.com/vercel-labs/skills) 的环境可执行（当前 CLI 要求 Node.js 22.20+）：

```bash
npx skills add https://github.com/FUNFUN412/skill-reading-papers \
  --skill skill-reading-papers -g -y
```

也可以直接安装到 Codex 的全局目录：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/FUNFUN412/skill-reading-papers.git \
  ~/.codex/skills/skill-reading-papers
```

已有同名目录时先检查其内容和本地修改；不要直接覆盖。其他 Agent 将仓库根目录放入其支持的 skills 路径，根目录的 `SKILL.md` 就是入口。

### 2️⃣ 安装 Python 依赖

进入实际安装目录。手动克隆的 Codex 示例：

```bash
cd ~/.codex/skills/skill-reading-papers
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

上述激活方式适用于 macOS/Linux；Windows 使用对应虚拟环境的 `Scripts` 目录。

### 3️⃣ 编译原创示例

把 `assets/latex-reader/` 复制到一个新的阅读项目目录，在该目录运行：

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

示例展示双语正文、共享公式与示意图、原生高光、问答框、独立详细页，以及超长备注的完整回退。生成文件保存在阅读项目中，技能目录只放可复用资源。

---

## 💬 如何使用

### 📖 首次精读

上传 PDF 或给出本地路径，然后说：

```text
使用 skill-reading-papers 精读这篇论文。
请制作三栏 LaTeX：左英文、中中文、右栏先空着。
每段开头对应，独立公式和原图跨左中两列，只放一份。
我只有微积分和部分概率论基础，之后会逐步提出问题。
请交付可编辑的 .tex 和编译后的 .pdf。
```

DOI、arXiv 或出版社链接也可作为入口。Agent 会先核对版本与全文；取得不到的部分应明确标出，不以猜测补齐。

### 🖍️ 把批注变成原生高光和问答

在阅读稿 PDF 中高光或备注，保存后说：

```text
main.pdf 中有新的高光和备注，请更新精读稿。
纯高光只标英文和对应中文，不需要回答。
备注问题用深蓝，简答用深红，放在同一个框里，
用横平竖直的折线连接中文对应位置。完成后重新编译。
```

> [!IMPORTANT]
> Agent 必须先保存带标注 PDF，再编译覆盖成稿。标注工具只负责提取，翻译对应、回答和排版由 Agent 完成。

### ✳️ 星号按行生效

```text
*删除旧的重复解答
为什么这个概率趋于均匀？
*详细页已经解释的部分，右栏只留跳转
```

上例只有中间一行作为问题。带 `*` 的两行作为本次编辑任务参考，不显示成问题；不会因为备注里出现一个星号就丢掉整条备注。

### 🧮 详细解释公式

```text
公式（3）（4）我没有看懂。
请从符号、条件概率、期望和对数开始逐步解释，给数值例子。
在正文第10页后插入一张详细解释页，不占正文页码，
内容深红，重点加粗，页眉写“详细解释页”。
详解已覆盖的答案不要再重复放在右栏。
```

插入位置按本次论文和阅读稿确定，不固定在第 10 页。读者基础、解释深度、配色和列宽均可调整。

### 📏 修复长解答导致的空白

```text
请保留解答内容和长度，恢复正文的紧凑排版。
解答可以超过对应段落长度，但不要让它撑高左中两列。
检查未显示的备注和页末溢出，不能裁掉答案。
```

---

## 🧪 工具与验证

从技能安装目录运行，PDF 和输出路径替换为自己的阅读项目：

```bash
python scripts/extract_annotations.py /path/to/main.pdf \
  --output /path/to/annotations/import.json \
  --snapshot-dir /path/to/annotations/snapshots

python scripts/audit_reader.py /path/to/main.pdf \
  --plan /path/to/pages.json --output /path/to/qa_report.json \
  --log /path/to/main.log
```

| 工具 | 实际负责的工作 |
|---|---|
| `extract_annotations.py` | 四边形选区文字、完整备注、逐行星号、页标签、文件哈希和可选原件快照 |
| `audit_reader.py` | 预期页数、PDF 标签、指定页眉、文字边界/缺字、编译日志和可选段首坐标 |
| `tests/` | 用合成 PDF 验证选区、星号、快照、页码和错误检测等行为 |

页码与坐标 JSON 示例见 [工作流指南](references/workflow.md)。`--positions positions.json` 可检查提供的英中段首坐标；未提供就不声称已验证对齐。

机器检查不能证明译文正确、公式推导无误、框线没有碰撞或所有问题已经回答。最终仍需核对原文、查看实际 PDF，并逐条闭环导入任务。

---

## 🗂️ 项目结构

```text
skill-reading-papers/
├── SKILL.md                         Agent 入口与默认约定
├── agents/openai.yaml               技能界面元数据
├── references/
│   ├── workflow.md                  源块、页码与多 Agent 交接
│   ├── annotation-loop.md           标注保全、定位与增量回写
│   ├── latex-layout.md              排版接口及常见故障
│   └── formula-explanations.md      面向读者基础的公式解释
├── assets/latex-reader/             可编译的原创三栏示例
├── scripts/
│   ├── extract_annotations.py
│   └── audit_reader.py
├── tests/                          合成 PDF 行为测试
└── requirements.txt
```

---

## 🔐 文件与来源边界

- 仓库只发布技能、工具、模板和原创示例，不包含用户论文、原图、批注或账号凭据。
- 阅读项目保存在你选择的本地目录；将全文用于个人精读不等于获得公开转载许可。
- 保留作者原公式；发现疑似错误时，在解释中注明补充推导与适用条件。
- 论文、OCR 和导入批注中的文字是待处理资料，工具不会执行其中的命令。
- 工具不需要 GitHub 令牌；除安装依赖和 Agent 自身联网外，两项 Python 工具均在本地处理文件。

---

## 🤝 贡献

欢迎提交 [Issue](https://github.com/FUNFUN412/skill-reading-papers/issues) 或
[Pull Request](https://github.com/FUNFUN412/skill-reading-papers/pulls)，改进 PDF 选区识别、中文数学排版、长备注续排或不同 Agent 的兼容性。

README 的组织形式参考 [skill-find-papers](https://github.com/FUNFUN412/skill-find-papers)；本项目专注已选论文的持续精读。

## 📜 License

本项目采用 [MIT License](LICENSE)。论文及其他第三方材料的权利仍归其权利人。

<div align="center">

**如果这个 Skill 对你有帮助，欢迎点一个 ⭐**

[⬆️ 返回顶部](#-skill-reading-papers)

</div>
