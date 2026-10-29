# 三栏 LaTeX 的排版与核验

## 使用模板

新项目复制 `assets/latex-reader/` 到自己的阅读目录。模板只含原创硬币例子，不含论文正文；用 XeLaTeX 编译：

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

没有 latexmk 时连续运行 XeLaTeX，直到引用和保存坐标稳定。推荐 TeX Live / MacTeX / 配齐包的 TinyTeX；模板使用 ctex/Fandol、TeX Gyre、amsmath、longtable、fancyhdr、hyperref、TikZ、zref 和 xeCJKfntef，不需要 shell escape。缺包时补齐实际缺项，不把整套系统重装作为默认修复。

主文件配置 `\ReaderTitle` 与 `\ReaderDate`；`reader.sty` 配置列宽、字体、字号和颜色。示例固定日期仅用于可复现测试，新建阅读稿按用户时区更新。所有段落/笔记 ID 采用不含空白或 TeX 特殊字符的短标识；不要把原始备注直接当宏名。

| 接口 | 用途 |
|---|---|
| `\Pair{块ID}{英文}{中文}` | 两段段首对齐，第三格留空 |
| `\EquationRow{块ID}{公式编号}{数学内容}` | 独立公式跨英中两列，只显示一次 |
| `\ImageRow{块ID}{图片路径}{图注}` | 原图跨英中两列，保持比例 |
| `\SharedRow{块ID}{内容}` | 跨英中两列的表格或其他内容 |
| `\NativeHL{批注ID}{文字}` | 可断行的文本高光 |
| `\NativeMathHL{批注ID}{数学内容}` | 零 padding 的行内数学高光 |
| `\SourceAnchor{批注ID}` | 放在中文实际对应位置，位于高光宏外 |
| `\RegisterQA{批注ID}{问题}{简答}` | 独立右栏问答，适合在 notes.tex 注册 |
| `\RegisterAnswer{批注ID}{解答}` | 仅有解答，无伪造问题 |
| `\RegisterTutorialPointer{批注ID}{目标}{提示}` | 将右栏解答改成详细页链接 |
| `\ReaderDetailedPage{目标}{标题}{内容}` | 表格外插入独立详细页，恢复正文编号 |
| `\ReaderFlushNotes` | 文末排出尚未显示的完整备注 |

示例正文有稳定 ID 小标记，实际项目可调整 `\ReaderBlockMark` 的显示，保留底层 ID/锚点即可。表格长行是不可跨页的 minipage；超过单页的正文段应在合理语义边界拆分并记录父块，不通过缩成不可读的小字掩盖。

## 正文与右栏分离

正文用 `longtable` 的前两格，只按英中较长一侧决定段落行高，第三格始终为空。笔记先排成独立盒子，再依据保存位置在 shipout 阶段叠放到右栏；其高度不得反向影响正文。

侧栏长于源段是正常行为。当前模板先在可用右栏空间放置完整问答；放不下的问答延至后续正文页，或在文末转为可跨页的详细说明并留下来源链接。超一页的答复不剪裁，也不无限等待。最终核对所有注册备注都已出现、跳转目标存在、续排有来源提示。模板回退到文末不等于满足“在指定页后插入”，指定插页仍需主 agent 放到正确位置。

框和指针均需参加占位检查。连接线从实际中文锚点出发，用短横竖线经过栏间空白接入框；不能盖住正文。用**绝对物理页**安排 shipout，不能仅用会恢复或隐藏的 `\thepage`。

## 插页与高光的易错点

- 先结束 longtable，再插详细页，再显式开启 longtable。若重新开启后的第一行是 `\multicolumn`，不要让这一步跨 `\input` 返回边界，文件钩子可能触发 `Misplaced \omit`。
- `SharedRow` 等跨栏宏须保持可展开；不要换成阻止首 token 展开的保护宏。
- 需要切换 geometry 时，在表格外操作；设置和恢复都要管理页面尺寸的全局状态。简单分组包裹 geometry 不能保证恢复后的排版器高度正确。附带模板不通过切换 geometry 实现详解页。
- 独立解释页切换页眉、内容颜色与页脚，隐藏 PDF 标签，结束后恢复正文逻辑页号。多页解释时每页都必须符合规则，不能只处理第一页。
- 高光不能改写数学。行内公式背景 padding 容易增加行高，用零 padding 并比较改动前后的基线和断页。
- 预构造彩色 vbox 时正确配对颜色分组。TikZ shipout 中直接重排长文本要留意字体上下文，避免拉丁字符缺失；不能只凭日志没有报错就交付。

## 实际验证

模板附有原创示例的 `pages.json`，替换内容后要按本次成稿更新。模板输出 `main.reader-pages.tsv` 与 `main.reader-notes.tsv`，用于查看实际物理/逻辑页映射和备注去向；这些 TSV 不是两个 Python 工具的输入 JSON，需要核对后转换为 `pages.json` / 位置数据，不能把后缀改为 JSON 就传入。

```bash
python /path/to/skill-read-papers/scripts/audit_reader.py main.pdf \
  --plan pages.json --output qa_report.json --log main.log \
  --positions positions.json --tolerance 0.5
```

坐标与计划的结构见 [workflow.md](workflow.md)。容差单位为 PDF point。无位置文件时该脚本不会验证段首对齐；它也不会识别框之间的碰撞、是否漏答、数学是否正确或页脚视觉编号。

最后渲染 PDF：看受改动页及相邻页，确认段首、公式、图注、页眉横线、分界线、问答框和折线均完整。对插页查看正文页号与 PDF 标签两套编号。CMEX 数学字体可能把可见的可缩放括号抽成 NUL，脚本只对已知字体给提示；仍需看对应图像确认，不能对所有缺字一概忽略。
