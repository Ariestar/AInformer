# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

小团队共享。作者本人每天扫一遍池子，勾选若干条导出 Markdown 简报发给同事；同事从链接进入，需要在几秒内看懂这是什么、能做什么，不需要教程。

## Product Purpose

把多个一手源与中文源抓回来的 AI 条目原样聚合成一个可筛选的池子，由人决定看什么、留什么、发什么。成功的样子：打开就能扫，勾几条就能导出一份可发的简报。

## Positioning

机器不替人筛。不做重要性打分、不做摘要生成，只做格式归一、去重、时间排序，取舍权完整交给人。同类 AI 资讯产品普遍替你筛，这一条它们没法照抄。

## Operating Context

GitHub Actions 每 4 小时抓取并部署一次；桌面浏览器为主，手机快速扫为辅；导出 Markdown 简报在团队内流转；数据窗口 60 天。

## Capabilities and Constraints

筛选（关键词 / 来源 / 层级 / 有无日期）、排序、勾选、导出 Markdown、简报视图、深浅色、分页、筛选状态写入 URL。
约束：纯静态站（Astro 5 + React islands），无后端；数据契约唯一来源 `schema/pool.schema.json`；Python 侧零运行时依赖。

## Brand Commitments

名称 AInformer。纯黑深色基调 + 中性灰层次，不用蓝紫底。不做营销落地页，不用彩色发光与渐变。

## Evidence on Hand

真实条目来自 29 个源（官方 / 媒体 / 聚合 / 论文），落盘在 `data/items.json`。没有用户评价、没有商业指标、没有客户案例，后续工作不得编造。

## Product Principles

1. 不替人筛：只做归一与排序，不做判断。
2. 密度优先：一屏尽量多条目，滚动比点击便宜。
3. 一眼可读：来源层级、时间、标题必须在同一视线内可比。
4. 取舍可回溯：筛选与勾选可分享、可恢复。
5. 安静的工具：视觉服务于扫描，不做装饰性表演。

## Accessibility & Inclusion

WCAG AA 对比度；键盘可达；尊重 `prefers-reduced-motion`；深浅色跟随系统。
