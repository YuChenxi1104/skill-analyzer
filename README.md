# skill-analyzer

`skill-analyzer` 用来把一个现有 skill 拆成“可学习、可复用、可展示”的分析结果，尤其适合向 AI 初学者讲清楚：

- 它解决什么问题
- 它怎么触发
- 它的文件如何组织
- 它最后交付什么

这个目录既支持放在完整仓库里使用，也支持单独拿出来作为一个独立 skill 使用。

## 定位

- 目录名称：`skill-analyzer`
- skill 名称：见 `SKILL.md` frontmatter

## 路径原则

为了方便别人下载后直接使用，本文档默认采用两条路径规则：

1. 仓库内部文件一律相对 `skill-analyzer` 根目录描述
2. 输出目录只给推荐位置，不写死你的本机绝对路径

推荐做法是：

- 无论是整仓库模式还是独立模式，都先进入 `skill-analyzer` 根目录再运行脚本
- `assets/`、`references/`、`scripts/` 的引用都从当前 skill 根目录出发

## 两种使用方式

### 1. 整仓库模式

适合直接克隆整个 GitHub 仓库的人。

推荐约定：

- skill 样本目录：`../skill-library/full-skills/`
- 分析输出目录：`../skill-library/outputs/<skill-name>/`

### 2. 独立 skill 模式

适合只拿走 `skill-analyzer` 这个目录单独使用的人。

推荐约定：

- skill 样本目录：自行决定，只要后续引用一致
- 分析输出目录：`outputs/<skill-name>/`

## 当前目录结构

### 根目录

- `SKILL.md`
  - skill 入口协议，负责总流程和交付边界
- `README.md`
  - 目录地图、使用方式、路径约定
- `references/`
  - 拆解规则文档
- `scripts/`
  - 生成和导出脚本
- `assets/`
  - 模板、海报素材和参考图

### `references/`

- `column-rubric.md`
  - 栏目写法规则
- `visual-breakdown.md`
  - 结构图模块规则
- `structure-slide-html.md`
  - 结构图 HTML 展示规则
- `skill-flow-diagram.md`
  - 流程图模块规则
- `skill-breakdown-schema.md`
  - 顶层职责边界说明
- `sample-skill-module-map.md`
  - 常见样本模块映射表，用来加快初判

### `scripts/`

- `render_structure_slide.py`
  - 把结构数据渲染成单页结构图 HTML
- `render_merged_preview.py`
  - 用初级模块数据 + 结构数据生成合并页
- `render_process_poster.py`
  - 按需生成独立流程图 HTML
- `export_generated_assets.mjs` / `export_generated_assets.py`
  - 导出部分生成素材
- `export_process_assets.mjs`
  - 导出流程图相关素材

## 默认轻量模式

为了提高生成速度，默认拆解流程现在优先走轻量模式。

### 默认正式产物

- `structure-data.json`
- `<skill-name>-merged-preview.html`

### 默认不做的事

- 不默认单独生成 `*-process-poster.html`
- 不默认生成任何 PNG 预览图
- 不默认为了“看起来全”去深读非关键文件

### 只在需要时再补的中间产物

- `<skill-name>-structure-slide.html`
- `<skill-name>-process-poster.html`

适用场景：

- 布局调试
- 结构图讲解
- 流程图需要单独展示

## 推荐读取顺序

1. 先读目标 skill 的 `SKILL.md`
2. 再读 `README.md`
3. 再读 `CLAUDE.md / AGENTS.md / Agent.md`（如果存在）
4. 再看顶层目录结构
5. 最后只补读被点名引用、且会真正影响拆解的 `references/`、`scripts/`、`assets/`

默认不要一开始就扫完整个仓库。

## 快速判断技巧

如果目标 skill 结构比较常见，先看：

- `references/sample-skill-module-map.md`

它的作用是帮助你更快判断：

- 哪些目录是独立模块
- 哪几个文件最值得优先展开
- 哪些文件只需要确认存在，不需要一开始深读

它只是提速辅助，不替代真实样本。
