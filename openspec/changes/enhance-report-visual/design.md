## Context

当前报告生成流程:

- `Reporter.generate()` 生成结构化数据 (dict)
- `run_generate_report_html()` 将数据渲染为 HTML 字符串
- 使用 `ui-ux-pro-max` skill 获取设计 tokens (可选)
- 输出单一卡片布局的 HTML

现状问题:

- AI 增强评分产生的 `highlights`、`concerns`、`adjustment_reasoning` 仅被简单列表展示
- 视觉层次单一,信息密度低
- 缺少决策支持信息 (如面试建议)

技术约束:

- 保持纯服务端渲染 (不引入前端构建)
- 保持 Python 单一技术栈
- 支持邮件客户端兼容性
- 移动端和打印友好

## Goals / Non-Goals

**Goals:**

- 重构 HTML 生成逻辑,实现多层次布局
- 充分可视化展示 AI 数据 (highlights/concerns/reasoning)
- 增加算法 vs AI 对比可视化
- 提供面试建议等行动指引
- 保持服务端渲染架构
- 响应式设计和打印优化

**Non-Goals:**

- 不引入前端框架 (React/Vue)
- 不使用客户端 JS 交互 (保持静态 HTML)
- 不修改 Reporter 的核心评分逻辑
- 不改变 API 接口格式

## Decisions

### 1. 布局架构: 多区块垂直堆叠

**决策**: 采用垂直堆叠的多区块布局,信息优先级从上到下递减

```
┌─────────────────────┐
│ 1. 评估概览          │  ← 综合分 + 推荐结论 (第一眼)
├─────────────────────┤
│ 2. 核心亮点 💡       │  ← AI highlights (30秒内)
├─────────────────────┤
│ 3. 需要关注 ⚠️        │  ← AI concerns (30秒内)
├─────────────────────┤
│ 4. 详细维度评分      │  ← 4个维度 + AI推理框 (深入阅读)
├─────────────────────┤
│ 5. 评分对比分析      │  ← 算法 vs AI (深入阅读)
├─────────────────────┤
│ 6. 面试建议 🎯       │  ← 行动指引
└─────────────────────┘
```

**理由**:

- 符合 F 型阅读模式 (先看顶部和左侧)
- 满足不同阅读深度需求 (快速浏览 vs 深入研究)
- 垂直布局在移动端和邮件客户端兼容性最好

**备选方案**: 左右分栏布局 (概览在左,详情在右)

- **弃用原因**: 移动端体验差,邮件客户端支持有限

---

### 2. AI 数据可视化: 独立卡片 + 渐变背景

**决策**: 使用独立的卡片容器展示 highlights 和 concerns,通过颜色区分

```css
/* Highlights 卡片 */
.highlight-card {
  background: linear-gradient(135deg, #e0f2fe, #dbeafe); /* 浅蓝渐变 */
  border-left: 4px solid #3b82f6;
  icon: 🚀 💻 🎓 (蓝绿色系);
}

/* Concerns 卡片 */
.concern-card {
  background: linear-gradient(135deg, #fef3c7, #fde68a); /* 浅黄渐变 */
  border-left: 4px solid #f59e0b;
  icon: ⚠️ ⚡ 👥 (黄橙色系);
}
```

**理由**:

- 视觉差异化清晰 (积极 vs 警示)
- 卡片形式提升信息感知优先级
- 渐变背景增加现代感,不失专业性

**备选方案**: 纯色背景 + 图标

- **弃用原因**: 视觉冲击力不足,难以快速区分区域

---

### 3. AI 推理展示: 折叠式框体

**决策**: 在每个维度评分下增加"AI 评估"框,展示完整 `adjustment_reasoning`

```html
<div class="ai-reasoning-box">
  <strong>🤖 AI 评估 (基准分: 60 → 调整后: 85)</strong>
  <p>虽然简历仅明确列出 Python 和 FastAPI...</p>
</div>
```

样式:

```css
.ai-reasoning-box {
  background: #f8fafc; /* 浅灰背景 */
  border: 1px solid #e2e8f0;
  padding: 16px;
  font-size: 0.9em; /* 稍小字体 */
  line-height: 1.6; /* 易读行距 */
}
```

**理由**:

- 与主要评分内容视觉区分,但不喧宾夺主
- 完整展示 AI 推理过程,提升可解释性
- 灰色背景表明这是"元信息"(关于评分的说明)

**备选方案**: 使用 `<details>` 标签实现可展开

- **弃用原因**: 需要客户端 JS,违背 Non-Goals;且在某些邮件客户端不支持

---

### 4. 对比可视化: 表格 + 文字柱状图

**决策**: 使用表格对比算法和 AI 分数,用 Unicode 字符绘制柱状图

```
              算法基准分         AI 调整后          差异
  ─────────────────────────────────────────────────────────
  技能         60  ▓▓▓▓▓▓        85  ▓▓▓▓▓▓▓▓▓     +25 ⬆
  经验        100  ▓▓▓▓▓▓▓▓▓▓    95  ▓▓▓▓▓▓▓▓▓     -5  ⬇
```

**理由**:

- 表格格式信息密度高,便于对比
- 文字柱状图 (▓) 兼容性好,无需图表库
- 差异列清晰展示 AI 调整幅度

**备选方案**: 使用 Chart.js 绘制真实图表

- **弃用原因**: 需要 Canvas/SVG,在邮件客户端不显示;增加复杂度

---

### 5. 面试建议生成: 规则引擎

**决策**: 基于评分结果和 concerns,使用规则生成面试建议

```python
def generate_interview_suggestions(dimensions: dict) -> list[str]:
    suggestions = []

    # 规则1: 如果某维度有 concerns,建议深入考察
    for dim_name, dim_score in dimensions.items():
        if dim_score.concerns:
            suggestions.append({
                "topic": dim_labels[dim_name],
                "concerns": dim_score.concerns,
                "questions": generate_questions(dim_name, dim_score.concerns)
            })

    # 规则2: 如果有 missing 技能,建议评估学习能力
    # ...

    return suggestions
```

**理由**:

- 规则简单清晰,易于维护
- 基于实际评估数据,针对性强
- 为面试官提供具体行动指引

**备选方案**: 使用 LLM 生成面试建议

- **弃用原因**: 增加成本 (每报告多一次 LLM 调用);响应时间增加;不稳定

---

### 6. 样式管理: 内联 CSS

**决策**: 将所有 CSS 以 `<style>` 标签内联在 HTML `<head>` 中

**理由**:

- 邮件客户端不支持外部 CSS 文件
- 单文件分发,无需静态资源托管
- 保持现有架构 (生成 HTML 字符串)

**备选方案**: 使用外部 CSS 文件

- **弃用原因**: 需要静态资源服务器;邮件场景不可用

---

### 7. 响应式设计: CSS Media Queries

**决策**: 使用 `@media` 查询适配移动端和打印

```css
/* 移动端 */
@media (max-width: 768px) {
  .highlight-card {
    padding: 12px 16px;
  }
  .ai-reasoning-box {
    font-size: 0.85em;
  }
}

/* 打印 */
@media print {
  .highlight-card {
    background: #fff;
    border: 1px solid #ccc;
  }
}
```

**理由**:

- 标准 CSS 特性,无需 JS
- 移动端和打印体验显著提升
- 兼容性好

---

### 8. 数据流: Reporter → HTML 生成器

**决策**: Reporter 保持现有输出格式,HTML 生成器负责布局和样式

```
Reporter.generate()
    ↓
{
  "overall_score": 85,
  "dimensions": {...},
  "top_strengths": [...],   ← 已有
  "key_concerns": [...],    ← 已有
  "reasons": [...]
}
    ↓
run_generate_report_html()
    ↓
增强 HTML (多区块布局)
```

**理由**:

- 职责分离: Reporter 负责数据,HTML 生成器负责展示
- Reporter 无需修改,向后兼容
- 所有视觉变更集中在一个文件

**备选方案**: 修改 Reporter 输出格式以支持新布局

- **弃用原因**: 影响面大,可能破坏现有代码

## Risks / Trade-offs

### Risk 1: HTML 文件大小增加

**风险**: 增加 CSS 和结构后,HTML 文件可能从 ~5KB 增加到 ~15KB

**缓解**:

- 保持 CSS 精简,避免冗余
- 使用 CSS 复用 (通用类)
- 对于邮件场景,这个大小仍在可接受范围 (<100KB)

---

### Risk 2: 邮件客户端兼容性

**风险**: 不同邮件客户端对 CSS 支持差异大 (Outlook 特别差)

**缓解**:

- 使用表格布局作为 fallback (Outlook 支持)
- 避免使用 Flexbox/Grid (Outlook 不支持)
- 使用内联样式 (最大兼容性)
- 渐进增强: 即使样式失效,内容仍可读

---

### Risk 3: 面试建议规则维护成本

**风险**: 随着评估维度增加,规则可能变得复杂难维护

**缓解**:

- 初期保持规则简单 (3-5条)
- 规则集中在一个函数,易于定位和修改
- 后续可考虑配置文件管理规则
- 如果规则复杂度失控,再考虑引入 LLM 生成

---

### Trade-off: 静态 HTML vs 交互式组件

**选择**: 静态 HTML (无客户端 JS)

**优势**:

- ✅ 邮件客户端兼容
- ✅ 快速加载
- ✅ SEO 友好
- ✅ 实现简单

**劣势**:

- ❌ 无法展开/折叠
- ❌ 无法动态过滤
- ❌ 交互有限

**评估**: 在当前场景下,兼容性和简单性优先级更高。如果未来需要交互,可以考虑 Alpine.js (轻量级)。

---

### Trade-off: 规则引擎 vs LLM 生成面试建议

**选择**: 规则引擎

**优势**:

- ✅ 成本低 (无额外 LLM 调用)
- ✅ 响应快
- ✅ 结果稳定可预测

**劣势**:

- ❌ 灵活性低
- ❌ 需要维护规则

**评估**: 在初期阶段,规则引擎足够用。如果后续发现规则无法覆盖场景,再考虑混合方案 (规则 + LLM)。

## Migration Plan

**部署步骤**:

1. **向后兼容验证**
   - 确保新 HTML 生成器接受现有 Reporter 输出格式
   - 验证不启用 AI 增强评分时也能正常工作

2. **灰度发布**

   ```python
   # 通过环境变量控制
   USE_ENHANCED_REPORT = os.getenv("USE_ENHANCED_REPORT", "false")

   if USE_ENHANCED_REPORT == "true":
       return generate_enhanced_html(report)
   else:
       return generate_legacy_html(report)  # 当前版本
   ```

3. **验证场景**
   - 测试 AI 增强评分开启时的报告
   - 测试 AI 增强评分关闭时的报告
   - 测试移动端渲染
   - 测试邮件客户端渲染 (Gmail, Outlook, Apple Mail)
   - 测试打印效果

4. **全量上线**
   - 内部使用 1 周,收集反馈
   - 调整样式和文案
   - 设置 `USE_ENHANCED_REPORT=true` 全量

**回滚策略**:

- 如果发现严重问题,设置 `USE_ENHANCED_REPORT=false` 即可回滚
- 保留旧版 HTML 生成函数至少 2 周

## Open Questions

1. **面试建议的详细程度**
   - 目前设计是提供话题方向,是否需要具体问题示例?
   - 示例: "建议考察 Docker 能力" vs "建议询问:请描述你对容器化的理解..."

2. **是否需要版本标识**
   - 报告底部是否显示"AI 增强评分系统 v1.1"?
   - 便于追踪和反馈,但增加视觉噪音

3. **是否支持主题切换**
   - 未来是否考虑浅色/深色主题?
   - 当前不支持,但架构上可预留 tokens 机制

**待确认后再实施**。
