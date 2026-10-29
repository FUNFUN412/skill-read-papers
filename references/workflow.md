# 从原论文到可迭代的精读项目

## 输入与范围

先查看当前文件和用户已有设置。输入可为本地可选中文字 PDF、扫描 PDF、DOI/arXiv/出版社链接或粘贴文本。链接先定位版本及可合法访问的全文，扫描件先 OCR 并标出低置信度数学。已有全文时不要重新下载另一版覆盖。记录标题、作者、版本/日期、来源路径或 URL、文件 SHA256。

默认完成用户指定范围；“全文精读”包括正文和其要求的附录、图表，不退化为总结。缺页、模糊公式或取不到全文时，先完成可核实部分并列出具体缺口。只问一个概念时给出适合其基础的解释，不强加整套建稿流程。

## 源文分块先于翻译

按自然段、标题、独立公式、图、表分块。稳定 ID 如 `P001`、`E003`、`F002`，后续插入不重编号。保留源文顺序、公式编号、图表标题及内部引用。每块附原论文物理页与选区；从原 PDF 核对数学上下标、转置、条件概率、求和边界和矩阵维度。

建议 `source_map.json`：

```json
{
  "schema_version": 1,
  "source": {"sha256": "<source-file-sha256>", "title": "Paper title"},
  "blocks": [
    {
      "id": "P001",
      "kind": "paragraph",
      "source_physical_page": 1,
      "source_bbox": [30, 40, 280, 160],
      "tex_file": "parts/introduction.tex",
      "reader_physical_page": null,
      "reader_printed_label": null,
      "translation_status": "pending"
    }
  ]
}
```

此结构是建议的数据约定，两个附带工具不自动生成完整 source map。来源不明的值用 `null`，不能为了通过覆盖率检查猜填。图像记录源页、裁剪区域及资产路径；表格优先可编辑，无法可靠重建时保留完整清晰图像并说明。不要把跨页图裁掉或把图注当正文翻译两次。

翻译按语义忠实，不逐词机械对应；维护术语表，首次出现解释缩写。保留“可能/近似/在这些条件下”等限定，不能把经验结果翻成数学保证。英文、中文段首对应即可，段内不强制逐行对齐。

## 项目文件与职责

```text
paper-reader/
├── main.tex                  主入口与阅读配置
├── reader.sty / sidebar.tex   共用排版与独立笔记
├── parts/                    按章节分配的正文
├── notes.tex                 当前问答与详细页链接
├── tutorials/                补充解释，独立于作者原文
├── assets/                   本地阅读所需原图/表格
├── annotations/              带标注输入快照与导入记录
├── source_map.json           稳定 ID 与源文位置
├── pages.json                物理页、印刷标签和详细页计划
└── qa_report.json            实际检查结果
```

不要求已有项目改名迁移；沿用其入口和可维护结构。项目文档记录编译方式、字体依赖与正文/解释页页码约定。不要把某台电脑的 TinyTeX、Python 或临时目录路径写入通用模板。

## 多 agent 交接

可并行的工作：互不重叠的章节翻译、公式独立复核、原图清点、只读视觉 QA。应顺序执行的工作：修改公共宏、合并、编译、依据最新坐标排侧栏、最终发布。

委派示例：

```text
目标：翻译 source_map 中 P020–P048，保留数学和限定条件。
输入：原论文 PDF、源块清单、当前术语表。
可改：parts/method.tex；提交新术语建议为消息。
不可改：main.tex、reader.sty、sidebar.tex、pages.json、其他章节。
交付：完成 ID、未解决源文问题、公式/图表缺口、已做检查。
```

主 agent 维护 ID、术语决策和公共文件。数学 agent 应读取原始公式，独立核对条件、维度和数值例子；不要只审另一位 agent 的转述。QA agent 应查看最终渲染，不能只读源码。两位 agent 不同时编辑同一文件；任务接管或取消时先明确停止旧写入，再编辑。未完成的后台检查不算“已通过”。

## 页码与可验证数据

`pages.json` 给审核脚本的最小示例：

```json
{
  "expected_physical_pages": 4,
  "pages": [
    {"physical_page": 1, "printed_label": "1", "kind": "body", "header_text": "Paper title"},
    {"physical_page": 2, "printed_label": "", "kind": "detail", "header_text": "详细解释页"},
    {"physical_page": 3, "printed_label": "2", "kind": "body", "header_text": "Paper title"},
    {"physical_page": 4, "printed_label": "3", "kind": "body", "header_text": "Paper title"}
  ]
}
```

正文印刷页码与物理页分开。插入一个不编号页面后，后续所有物理页会增加，正文页号应连续；真正重排正文时更新映射，不把旧页号当永久 ID。页眉日期按用户时区和当前约定处理，不每次无故改版式。

可选 `positions.json`：

```json
{
  "rows": [
    {"id": "P001", "english": {"page": 1, "y": 85.0}, "chinese": {"page": 1, "y": 85.0}}
  ]
}
```

单位为 PDF point，页号为从 1 开始的成稿物理页；`y` 应是实际第一条文字基线或同定义的保存锚点。脚本检查的是给定数据，主 agent 还需确认数据确实来自本次编译。未提供坐标就不能声称通过了段首对齐检查。
