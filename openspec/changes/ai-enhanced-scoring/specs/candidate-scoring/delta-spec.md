## MODIFIED Requirements

### Requirement: 候选人评分支持 AI 增强模式

系统 SHALL 支持两种评分模式: 纯算法模式和 AI 增强模式,通过环境变量控制。

#### Scenario: 启用 AI 增强评分

- **WHEN** 环境变量 `USE_AI_ENHANCED_MATCHER` 设置为 "true"
- **AND** 系统执行候选人评分
- **THEN** 系统 SHALL 使用 `AIEnhancedMatcher` 进行评分
- **AND** 评分结果 SHALL 包含 AI 调整后的分数和详细推理

#### Scenario: 使用传统算法评分

- **WHEN** 环境变量 `USE_AI_ENHANCED_MATCHER` 未设置或设置为 "false"
- **AND** 系统执行候选人评分
- **THEN** 系统 SHALL 使用传统 `Matcher` 进行评分
- **AND** 评分结果 SHALL 仅包含算法计算的分数,不包含 AI 特有字段

#### Scenario: 默认行为

- **WHEN** 环境变量 `USE_AI_ENHANCED_MATCHER` 未设置
- **THEN** 系统 SHALL 默认使用传统算法评分(保守策略)
