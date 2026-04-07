## ADDED Requirements

### Requirement: 显示算法vs AI对比表格

报告 SHALL 在"评分对比分析"区块显示算法基准分和AI调整后分数的对比表格。

#### Scenario: 显示完整对比表格

- **WHEN** 报告包含baseline_score字段
- **THEN** 显示包含所有4个维度的对比表格
- **AND** 表格包含3列: 算法基准分、AI调整后、差异
- **AND** 表格底部显示综合分对比

#### Scenario: 差异正值显示绿色

- **WHEN** AI调整后分数 > 算法基准分
- **THEN** 差异列显示绿色"+N"和上箭头 (⬆)
- **AND** 字体颜色为#16A34A

#### Scenario: 差异负值显示红色

- **WHEN** AI调整后分数 < 算法基准分
- **THEN** 差异列显示红色"-N"和下箭头 (⬇)
- **AND** 字体颜色为#DC2626

#### Scenario: 差异为0显示横线

- **WHEN** AI调整后分数 = 算法基准分
- **THEN** 差异列显示"0 ━"
- **AND** 字体颜色为#64748B

---

### Requirement: 使用文字柱状图可视化分数

对比表格 SHALL 使用Unicode字符绘制柱状图展示分数。

#### Scenario: 显示算法基准分柱状图

- **WHEN** 显示对比表格
- **THEN** 算法基准分列显示分数后跟柱状图
- **AND** 柱状图使用▓字符,长度与分数成正比 (每10分1个▓)

#### Scenario: 显示AI调整后分柱状图

- **WHEN** 显示对比表格
- **THEN** AI调整后列显示分数后跟柱状图
- **AND** 柱状图长度与分数成正比

#### Scenario: 柱状图最大长度为10个字符

- **WHEN** 分数为100
- **THEN** 柱状图显示10个▓字符

---

### Requirement: 对比表格响应式设计

对比表格 SHALL 在移动端优化显示。

#### Scenario: 移动端缩小表格字体

- **WHEN** 设备宽度 <= 768px
- **THEN** 表格字体大小缩小至0.8em

#### Scenario: 移动端隐藏柱状图

- **WHEN** 设备宽度 <= 480px
- **THEN** 柱状图列隐藏,仅显示数字

---

### Requirement: 对比分析仅在AI模式显示

对比分析区块 SHALL 仅在AI增强评分开启时显示。

#### Scenario: AI模式显示对比

- **WHEN** 任意维度包含baseline_score字段
- **THEN** 显示"评分对比分析"区块

#### Scenario: 非AI模式不显示对比

- **WHEN** 所有维度不包含baseline_score字段
- **THEN** 不显示"评分对比分析"区块
