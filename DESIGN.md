---
name: AInformer
description: 机器不替人筛的 AI 情报条目池
colors:
  ink: "#000000"
  card: "#0a0a0a"
  surface: "#141414"
  line: "#262626"
  line-strong: "#3a3a3a"
  text: "#f5f5f5"
  text-soft: "#c9c9c9"
  muted: "#8b8b8b"
  accent: "#7c86e8"
  accent-strong: "#5e6ad2"
  signal-green: "#3dd68c"
  amber: "#f0c000"
  alert-red: "#eb5757"
  on-accent: "#ffffff"
typography:
  brand:
    fontFamily: "-apple-system, Segoe UI Variable Text, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1
    letterSpacing: "-0.01em"
  title:
    fontFamily: "-apple-system, Segoe UI Variable Text, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "14px"
    fontWeight: 500
    lineHeight: 1.4
  body:
    fontFamily: "-apple-system, Segoe UI Variable Text, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "-apple-system, Segoe UI Variable Text, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1
  data:
    fontFamily: "ui-monospace, SF Mono, JetBrains Mono, Cascadia Mono, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
rounded:
  xs: "4px"
  sm: "7px"
  md: "10px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
components:
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "30px"
  button-primary:
    backgroundColor: "{colors.accent-strong}"
    textColor: "#ffffff"
    rounded: "{rounded.sm}"
    padding: "0 12px"
    height: "30px"
  input-search:
    backgroundColor: "{colors.card}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
    padding: "0 11px 0 30px"
    height: "30px"
  chip-tier:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    rounded: "{rounded.xs}"
    padding: "0 8px"
  list-row:
    backgroundColor: "{colors.card}"
    textColor: "{colors.text}"
    rounded: "0px"
    padding: "11px 16px"
---

# Design System: AInformer

## Overview

**Creative North Star: "The Wire Desk"**

通讯社的编辑台：原始电讯按时间铺在桌上，来源和时间戳并排可比，编辑自己挑哪条留下。界面不替你判断价值，它只保证每一条都在同一视线里公平出现。

这套系统是 **Operate** 型：用户来这里完成"扫一遍 → 勾几条 → 导出"的任务，不是被说服。所以表达欲全部让位于扫描效率：纯黑底、中性灰层次、一个强调色，密度高、边框细、没有阴影、没有装饰性动效。品牌的个性藏在精度里——等宽数字对齐、时间列右对齐、选中态只用底色和勾选框。

**Key Characteristics:**
- 纯黑（#000000）+ 三级中性灰，层次靠明度差不靠色相
- 单一强调色，且分成"填充"与"文字"两个亮度档
- 零阴影、零渐变、零发光；深度只由 1px 边框与底色差表达
- 数据（时间、计数、序号）一律等宽 + tabular-nums
- 图标是手绘 SVG 线性图标，不用字形代替

## Colors

冷、静、几乎无彩：整页只在强调色和三个语义色上出现饱和度。

### Primary
- **Wire Blue** (#7c86e8)：文字与链接用的强调色。对 #0a0a0a 为 6.1:1，满足 AA。用于链接 hover、聚合源标签、简报侧栏序号、聚焦环。
- **Wire Blue Fill** (#5e6ad2)：填充用。白字在其上为 4.7:1。只用于主按钮底色与勾选框选中态。

### Neutral
- **Ink** (#000000)：页面底。纯黑，不用蓝紫调。
- **Card** (#0a0a0a)：条目区、输入框、面板底。
- **Surface** (#141414)：hover 底。
- **Line** (#262626)：默认边框与行分隔。
- **Line Strong** (#3a3a3a)：未选中的勾选框边、滚动条滑块。
- **Text** (#f5f5f5)：标题与正文主色。
- **Text Soft** (#c9c9c9)：摘要正文（简报视图）。
- **Muted** (#8b8b8b)：来源名、时间、占位符、次要标签。对 #0a0a0a 为 5.8:1。

### Tertiary
- **Signal Green** (#3dd68c)：官方源标记。
- **Amber** (#f0c000)：媒体源标记、无日期提示。
- **Alert Red** (#eb5757)：错误。
- **On Accent** (#ffffff)：主按钮文字，对 #5e6ad2 为 4.7:1。

### Named Rules
**The One Voice Rule.** 强调色只出现在链接、选中态、聚焦环和聚合源标签上；一屏之内彩色面积不超过 5%，它的稀缺就是它的意义。

**The Two-Tone Accent Rule.** 填充永远用 #5e6ad2（白字可读），文字永远用 #7c86e8（黑底可读）。两者不可互换。

## Typography

**Body Font:** 系统 UI 栈（-apple-system / Segoe UI Variable / PingFang SC / Microsoft YaHei）
**Label/Mono Font:** 系统等宽栈（ui-monospace / SF Mono / JetBrains Mono）

**Character:** 工作字体，不是展示字体。中文走苹方/微软雅黑，英文走系统 UI 字，不加载 webfont，也不用 Inter 这类"默认 AI 脸"。等宽只出现在真正是数据的地方：时间、计数、序号、页码。

### Hierarchy
- **Brand** (600, 13px, 1): 顶栏站名，`-0.01em`。
- **Title** (500, 14px, 1.4): 条目标题，唯一允许 500 权重的地方。
- **Body** (400, 13px, 1.5): 控件文字、按钮、下拉。
- **Summary** (400, 12px, 1.5): 条目摘要，单行截断。
- **Label** (500, 12px, 1): 统计条标签、来源名。
- **Data** (400, 12px, 1.5, tabular-nums): 日期、计数、页码、简报序号。

### Named Rules
**The Data-Is-Mono Rule.** 等宽只用于数字与时间。正文、标题、按钮一律用 UI 字，不用等宽"装技术感"。

**The Tabular Rule.** 任何会变化的数字（计数、页码、日期）必须 `font-variant-numeric: tabular-nums`，否则滚动时会跳动。

## Layout

1180px 定宽容器，24px 侧边距；900px 以下侧边距收到 16px。纵向节奏：顶栏 8px 内边距 + 40px 内容高，统计条 10px 上下，主区 24px 上、64px 下。

条目列表是 CSS Grid 五列：`24px 96px 1fr 88px 18px`（勾选 / 来源 / 标题 / 日期 / 外链），列间距 12px，行内边距 `11px 16px`。密度是刻意的：一屏 900px 高能看到约 14 条。

简报视图是 `220px 1fr` 两栏，左栏 sticky。移动端单列，侧栏变成横向滚动的序号条，来源与日期列隐藏。

## Elevation & Depth

**没有阴影。** 系统是纯平层：深度只由 1px 边框（#262626）和底色差（#000 → #0a0a0a → #141414）表达。唯一允许的"阴影"是聚焦环 `0 0 0 3px rgba(124,134,232,0.38)`，它是状态反馈，不是装饰。

### Named Rules
**The No-Glow Rule.** 禁止零偏移彩色光晕（logo 曾经有一圈紫蓝发光，已删）。任何 `box-shadow` 不得带色相。

## Shapes

控件 7px 圆角（按钮、输入框、下拉），容器 10px（条目列表、面板），勾选框 4px。边框一律 1px。除顶栏的品牌圆点外没有胶囊形。不做卡片嵌套，列表就是列表。

## Components

### Buttons
- **Shape:** 7px 圆角，30px 高，1px 边框。
- **Ghost:** 透明底 + #262626 边框 + muted 文字；hover 变 surface 底、文字转白。
- **Primary:** #5e6ad2 底 + 白字；hover 加深到 #4e5bbf。只用于"导出 Markdown"。
- **Focus:** `0 0 0 3px` 强调色环，无 outline。
- **Disabled:** 透明度 0.4，光标不变手型。

### Chips
- **Style:** 20px 高、4px 圆角、无边框，底色为对应语义色的 18% 透明，文字用该语义色。
- **Tier:** 官方=绿、媒体=琥珀、聚合=Wire Blue。颜色即层级，不另加图标。

### Cards / Containers
- **Corner Style:** 10px。
- **Background:** Card。
- **Border:** 1px Line。
- **Shadow:** 无。
- **Internal Padding:** 列表行 11px 16px，面板 32px。

### Inputs / Fields
- **Style:** Card 底、1px Line 边框、7px 圆角、30px 高。
- **Search:** 左侧 13px 手绘放大镜，输入区左内边距 30px。
- **Focus:** 边框转强调色 + 3px 环。
- **Placeholder:** muted（5.8:1）。

### Navigation
- **Top bar:** sticky，Card 底，1px 底边；品牌圆点 7px 强调色。
- **View switch:** 两个独立 30px 按钮（条目池 / 我的简报），选中态用 primary-soft 底 + 强调色边框。不做带外框的分段控件。
- **Brief sidebar:** 序号用等宽 11px，选中项用 primary-soft 底，无左侧彩条。

### List Row (signature)
勾选框 + 来源 + 标题/摘要 + 日期 + 外链箭头。选中态只改底色（primary-soft）并填充勾选框，不加左侧彩条、不加环。hover 底为 Surface。外链箭头是 13px 手绘 SVG，`aria-hidden`，不参与 Tab。

## Do's and Don'ts

### Do:
- **Do** 用 #7c86e8 做文字强调、#5e6ad2 做填充；两档不可互换。
- **Do** 数字用 `tabular-nums`，日期列右对齐。
- **Do** 深度用 1px 边框和底色差表达。
- **Do** 图标手绘 SVG，1.4–1.5px 描边、圆头圆角。
- **Do** 选中态用底色 + 勾选框，一屏能一眼看出选了哪些。

### Don't:
- **Don't** 用蓝紫底或任何带色相的深色背景；底就是 #000000。
- **Don't** 用零偏移彩色光晕、渐变文字、玻璃模糊。
- **Don't** 在列表项或卡片上加彩色左边条。
- **Don't** 用 emoji / Unicode 字形当图标。
- **Don't** 把页面改成营销落地页：没有 hero、没有卖点三栏、没有 CTA 区。
- **Don't** 用大留白换"高级感"；这个界面的货币是密度。
