## Why

当前的候选人评估报告以单一卡片呈现,信息层次扁平,未充分利用 AI 增强评分产生的丰富数据(`highlights`、`concerns`、`adjustment_reasoning`)。HR 和面试官在查看报告时需要更清晰的视觉层次和更直观的决策支持信息。

## What Changes

- **视觉层次优化**: 将报告从单一卡片重构为多层次区块(评估概览、核心亮点、关注点、详细评分、对比分析、面试建议)
- **AI 数据可视化**: 将 `highlights` 和 `concerns` 以独立卡片样式展示,增加视觉差异化
- **推理过程展示**: 在每个维度下增加 AI 评估框,完整展示 `adjustment_reasoning`
- **对比可视化**: 新增算法基准分 vs AI 调整后分数的对比表格和柱状图
- **行动指引**: 新增"面试建议"章节,基于评估结果提供具体面试方向
- **响应式增强**: 优化移动端和打印样式

## Capabilities

### New Capabilities

- `enhanced-report-layout`: 定义多层次报告布局结构,包括区块划分、信息优先级、响应式规则
- `ai-insights-visualization`: 定义如何可视化展示 AI 生成的 highlights、concerns 和 reasoning
- `comparison-charts`: 定义算法 vs AI 评分对比的可视化规则

### Modified Capabilities

- `report-generation`: 修改现有报告生成逻辑,支持新的布局和样式系统

## Impact

**代码影响**:

- `app/agent/tools/generate_report_html.py`: 需要重构 HTML 生成逻辑和 CSS 样式
- `app/pipeline/reporter.py`: 可能需要调整数据组织格式以支持新布局

**用户影响**:

- HR 和面试官将看到更直观、信息更丰富的报告
- 报告文件大小会略有增加(增加 CSS 和结构)
- 移动端和打印体验提升

**依赖影响**:

- 无新增外部依赖
- 保持使用 Tailwind CDN 和 Google Fonts
