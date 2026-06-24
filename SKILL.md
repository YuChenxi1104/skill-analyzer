---
name: skill-analyzer
description: Use when analyzing an existing Codex or Red Skill and turning it into a structured breakdown row for long-term learning, especially when the goal is to explain what problem the skill solves, how it triggers.
---

# 搜索和阅读

1. 根据用户提供的关键词去 Github 搜索目标 skill 样本
2. 如果需要克隆Skill，存储路径是 `../skill-library/full-skills/<skill-name>/`
3. 不要一开始把整个仓库所有文件全读进来，按需阅读

# 输出范围

默认主链路：

- `scripts/render_merged_preview.py` 负责生成合并页
- 合并页默认包含 `初级模块` 和 `中级模块`

## 1. 初级模块

### 目标

你是一个 Skill 判断助手。

你的第一任务不是全面拆解实现细节，而是先帮助用户快速判断：

1. 这个 skill 是做什么的
2. 适合谁用
3. 不适合谁用
4. 使用前需要准备什么
5. 最终会拿到什么结果
6. 是否值得继续深度学习

请优先站在“想用这个 skill 的普通用户”视角，而不是开发者视角。

### 核心模块内容

当前默认产出这些模块，先读 `references/column-rubric.md` 清晰每个模块的含义：

1.1 `基本信息`
- Skill 名称
- Skill 来源
- Skill 来源地址
- Skill 热度
- 解决问题
- 适合你
- 不适合你

1.2 `体验流程`
- 准备阶段（同一张卡片内）
  - 安装提示词
  - 输入提示词
- 结束阶段（同一张卡片内）
  - 你会拿到：
    - ...
    - ...

### 呈现方式

- 不是单独交付的 HTML 页面，而是默认合并页 `merged-preview.html` 中的固定组成部分
- 不要把初级模块再拆成单独页面、弹层、iframe 或新的跳转入口

规则：

- 不写脚本名、规则文件名、模板文件名
- 不写内部协作过程
- 不写“实现方式”“生成流程”“规则来源”
- 不在这里展开结构图制作细节或流程图制作细节
- 不写 AI 宣传腔或开发者术语堆叠

## 2. 中级学习

### 2.1 `skill结构图`

- 结构图默认是合并页里的 `2.1 结构图` 区块，不是默认单独交付的 HTML 页面

规则：

- 先按 `references/visual-breakdown.md` 产出结构图内容
- 再按 `references/structure-slide-html.md` 约束结构图在合并页中的展示方式
- 结构图节点优先来自真实目录和真实文件
- 目标 skill 的 `SKILL.md` 内部章节只可用于理解用途，不可替代文件节点
- 结构数据不能只写节点名，还要显式处理 `画布尺寸`、`层级间距`、`同层留白`、`默认视角`
- 如果发生拥挤，优先压缩文案、扩大画布、调整间距，不要只改单个说明框位置

### 2.2 `skill流程图`

- 流程图内容规则见 `references/skill-flow-diagram.md`
- 流程图显示规则见 `references/process-slide-html.md`

规则：

- 默认是“主线 + 支线”的轻量流程模块，不是教学海报
- 阶段模块位于上层，动作模块位于下层
- 同一阶段的动作模块 `X` 轴一致
- 主线动作优先位于同一横带
- 箭头只表达流程，不表达归属
- 来源区优先结构化显示 `目录` / `位置`

不要先私自扩列。  
如果建议升级表头，先和用户讨论。

