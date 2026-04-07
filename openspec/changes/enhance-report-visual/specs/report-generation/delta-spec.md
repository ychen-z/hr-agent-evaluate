## ADDED Requirements

### Requirement: 生成面试建议区块

报告 SHALL 包含基于评估结果生成的面试建议。

#### Scenario: 基于concerns生成建议

- **WHEN** 某维度包含concerns数据
- **THEN** 在"面试建议"区块列出该维度的考察建议
- **AND** 每条建议包含考察主题和具体方向

#### Scenario: 基于missing技能生成建议

- **WHEN** 技能维度包含missing字段
- **THEN** 建议中包含"评估候选人学习XX技术的意愿和能力"

#### Scenario: 没有concerns时提供通用建议

- **WHEN** 报告不包含任何concerns
- **THEN** 显示通用面试建议 (如"验证项目经历真实性")

---

### Requirement: HTML生成器支持环境变量切换

HTML生成器 SHALL 支持通过环境变量切换增强版和传统版报告。

#### Scenario: 启用增强版报告

- **WHEN** 环境变量 `USE_ENHANCED_REPORT=true`
- **THEN** 使用增强版HTML生成逻辑

#### Scenario: 关闭增强版报告

- **WHEN** 环境变量 `USE_ENHANCED_REPORT=false` 或未设置
- **THEN** 使用传统版HTML生成逻辑

#### Scenario: 向后兼容

- **WHEN** 使用任意版本HTML生成器
- **THEN** 接受Reporter.generate()的现有输出格式
- **AND** 不修改Reporter的核心逻辑
