## ADDED Requirements

### Requirement: 核心亮点以卡片形式展示

核心亮点 (highlights) SHALL 以独立卡片形式展示,使用浅蓝色渐变背景。

#### Scenario: 显示AI生成的亮点

- **WHEN** 报告包含 `top_strengths` 数据
- **THEN** 在"核心亮点"区块显示每个亮点为独立卡片
- **AND** 卡片使用浅蓝色渐变背景 (#E0F2FE 到 #DBEAFE)
- **AND** 卡片左侧有4px蓝色边框 (#3B82F6)

#### Scenario: 亮点卡片包含图标

- **WHEN** 显示亮点卡片
- **THEN** 每个卡片开头显示相关emoji图标 (如 🚀 💻 🎓)
- **AND** 图标大小为1.5em

#### Scenario: 没有亮点时不显示区块

- **WHEN** 报告不包含 `top_strengths` 数据
- **THEN** 不显示"核心亮点"区块

---

### Requirement: 需要关注的点以警告卡片展示

需要关注的点 (concerns) SHALL 以警告卡片形式展示,使用浅黄色渐变背景。

#### Scenario: 显示AI识别的关注点

- **WHEN** 报告包含 `key_concerns` 数据
- **THEN** 在"需要关注"区块显示每个关注点为独立卡片
- **AND** 卡片使用浅黄色渐变背景 (#FEF3C7 到 #FDE68A)
- **AND** 卡片左侧有4px橙色边框 (#F59E0B)

#### Scenario: 关注点卡片包含建议

- **WHEN** 显示关注点卡片
- **THEN** 卡片显示关注点描述
- **AND** 显示"建议"文字 (如"建议面试时确认...")

#### Scenario: 没有关注点时不显示区块

- **WHEN** 报告不包含 `key_concerns` 数据
- **THEN** 不显示"需要关注"区块

---

### Requirement: AI推理过程以灰色框展示

AI调整推理 (adjustment_reasoning) SHALL 在每个维度下以灰色框展示。

#### Scenario: 显示完整推理过程

- **WHEN** 维度包含 `adjustment_reasoning` 字段
- **THEN** 在该维度评分下方显示"AI评估"框
- **AND** 框使用浅灰色背景 (#F8FAFC)
- **AND** 框有1px淡边框 (#E2E8F0)

#### Scenario: 推理框显示分数变化

- **WHEN** 显示AI推理框
- **THEN** 框标题显示"🤖 AI 评估"
- **AND** 显示"基准分: X → 调整后: Y"格式
- **AND** 基准分使用删除线样式 (#94A3B8)
- **AND** 调整后分使用绿色加粗 (#16A34A)

#### Scenario: 没有AI推理时不显示框

- **WHEN** 维度不包含 `adjustment_reasoning` 字段
- **THEN** 不显示AI推理框

---

### Requirement: 卡片样式响应式适配

亮点和关注点卡片 SHALL 在移动端优化显示。

#### Scenario: 移动端缩小卡片内边距

- **WHEN** 设备宽度 <= 768px
- **THEN** 卡片内边距从 16px 20px 缩小至 12px 16px

#### Scenario: 移动端缩小图标

- **WHEN** 设备宽度 <= 768px
- **THEN** emoji图标大小从 1.5em 缩小至 1.2em
