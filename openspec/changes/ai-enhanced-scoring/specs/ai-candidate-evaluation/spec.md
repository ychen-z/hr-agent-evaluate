## ADDED Requirements

### Requirement: AI 深度评估候选人匹配度

系统 SHALL 使用 LLM 对候选人进行深度评估,超越简单的字符串匹配,提供语义理解和综合判断。

#### Scenario: 识别语义相似的技能

- **WHEN** 候选人简历包含 "Vue.js",岗位要求 "React"
- **THEN** AI 评估 SHALL 识别两者为相似前端框架,给予部分匹配分数(如 70-80分)
- **AND** 推理说明 SHALL 解释 "Vue 和 React 为相似的前端框架,技能可迁移"

#### Scenario: 从项目经历推断技能深度

- **WHEN** 候选人简历列出 "Python",项目经历描述包含 "设计高并发架构"
- **THEN** AI 评估 SHALL 推断候选人 Python 技能深度较高
- **AND** 技能分数 SHALL 高于仅列出 "Python" 但无项目佐证的候选人

#### Scenario: 评估经验质量而非仅看年限

- **WHEN** 候选人 A 有 3 年经验,项目描述为 "日活百万用户的电商系统架构"
- **AND** 候选人 B 有 3 年经验,项目描述为 "企业内部管理系统维护"
- **THEN** AI 评估 SHALL 给候选人 A 更高的经验分数
- **AND** 推理说明 SHALL 解释项目复杂度和技术挑战的差异

#### Scenario: 从工作经历推断软技能

- **WHEN** 候选人简历未明确列出 "领导力",但工作经历包含 "带领 5 人团队"
- **AND** 岗位要求包含 "领导力"
- **THEN** AI 评估 SHALL 推断候选人具有一定领导能力
- **AND** 软技能分数 SHALL 反映这一推断
- **AND** 推理说明 SHALL 引用工作经历中的具体证据

---

### Requirement: AI 评估输出详细推理

系统 SHALL 为每个评分维度提供详细的推理说明,解释分数调整的依据。

#### Scenario: 提供分数调整理由

- **WHEN** AI 将技能匹配分数从算法的 60 分调整为 85 分
- **THEN** 输出 SHALL 包含 `adjustment_reasoning` 字段
- **AND** 该字段 SHALL 具体说明调整原因(如 "候选人掌握相关技术栈...")
- **AND** 该字段 SHALL 引用简历中的具体内容作为证据

#### Scenario: 识别候选人亮点

- **WHEN** AI 发现候选人有特殊优势(如技术栈完整、高并发经验等)
- **THEN** 输出 SHALL 包含 `highlights` 列表
- **AND** 列表 SHALL 包含 2-5 个简洁的亮点描述

#### Scenario: 识别潜在关注点

- **WHEN** AI 发现候选人有需要注意的方面(如经验不足、跳槽频繁等)
- **THEN** 输出 SHALL 包含 `concerns` 列表
- **AND** 列表 SHALL 包含具体的关注点描述
- **AND** 描述 SHALL 客观中立,不带负面情绪

---

### Requirement: 单次 LLM 调用完成评估

系统 SHALL 通过单次 LLM 调用完成所有 4 个维度的评估,以控制成本和响应时间。

#### Scenario: 一次性评估所有维度

- **WHEN** 系统执行 AI 增强评估
- **THEN** 系统 SHALL 调用 LLM 恰好 1 次
- **AND** 该次调用 SHALL 返回所有 4 个维度(技能、经验、学历、软技能)的评分
- **AND** 每个维度 SHALL 包含分数、推理、亮点、关注点

#### Scenario: 评估时间控制

- **WHEN** 系统执行 AI 增强评估
- **THEN** 整体评估时间 SHALL 少于 5 秒(含 LLM 调用和数据处理)

---

### Requirement: 算法基准分作为参考

系统 SHALL 先执行算法评分获得基准分,再由 AI 参考基准分进行调整。

#### Scenario: 提供算法基准分给 AI

- **WHEN** 系统执行 AI 评估
- **THEN** 系统 SHALL 先调用现有 `Matcher.match()` 获取算法基准分
- **AND** 基准分 SHALL 包含在发送给 LLM 的 prompt 中
- **AND** prompt SHALL 说明基准分"仅供参考"

#### Scenario: 保留基准分供对比

- **WHEN** AI 评估完成
- **THEN** 输出的 `DimensionScore` SHALL 同时包含:
  - `score`: AI 调整后的分数
  - `baseline_score`: 算法基准分
- **AND** 两个分数 SHALL 都在 0-100 范围内

---

### Requirement: LLM 失败时降级到算法评分

系统 SHALL 在 LLM 调用失败时优雅降级到算法评分,保证系统可用性。

#### Scenario: LLM API 超时降级

- **WHEN** LLM API 调用超时(如 10 秒无响应)
- **THEN** 系统 SHALL 捕获超时异常
- **AND** 系统 SHALL 记录警告日志
- **AND** 系统 SHALL 返回算法基准分作为最终结果
- **AND** 返回的 `DimensionScore` SHALL 不包含 AI 特有字段(`adjustment_reasoning`, `highlights`, `concerns`)

#### Scenario: LLM 返回格式错误降级

- **WHEN** LLM 返回的 JSON 格式无效或不符合 schema
- **THEN** 系统 SHALL 捕获解析异常
- **AND** 系统 SHALL 记录错误日志(包含 LLM 原始响应)
- **AND** 系统 SHALL 返回算法基准分作为最终结果

#### Scenario: LLM API Key 失效降级

- **WHEN** LLM API 返回 401 Unauthorized
- **THEN** 系统 SHALL 记录错误日志
- **AND** 系统 SHALL 返回算法基准分作为最终结果
- **AND** 系统 SHALL 不重试(避免连续失败)

---

### Requirement: 输出符合扩展后的数据模型

系统 SHALL 输出符合扩展后的 `DimensionScore` 和 `MatchReport` 模型,保持向后兼容性。

#### Scenario: DimensionScore 包含所有必需字段

- **WHEN** AI 评估完成
- **THEN** 每个维度的 `DimensionScore` SHALL 包含:
  - `score`: int (0-100)
  - `baseline_score`: Optional[int] (算法基准分)
  - `matched`: Optional[list[str]] (匹配的技能/软技能)
  - `missing`: Optional[list[str]] (缺失的技能/软技能)
  - `detail`: Optional[str] (经验/学历详情)
  - `adjustment_reasoning`: Optional[str] (AI 推理)
  - `highlights`: Optional[list[str]] (亮点)
  - `concerns`: Optional[list[str]] (关注点)

#### Scenario: MatchReport 包含整体评估

- **WHEN** AI 评估完成并生成报告
- **THEN** `MatchReport` SHALL 包含:
  - `overall_score`: int (综合分数)
  - `dimensions`: dict (各维度详情)
  - `recommendation`: str ("推荐" 或 "不推荐")
  - `reasons`: list[str] (推荐理由)
  - `overall_assessment`: Optional[dict] (AI 整体评估)
  - `top_strengths`: Optional[list[str]] (核心优势 2-5 条)
  - `key_concerns`: Optional[list[str]] (关键关注点 0-3 条)

#### Scenario: 向后兼容现有代码

- **WHEN** 现有代码读取 `DimensionScore.score` 或 `MatchReport.overall_score`
- **THEN** 这些字段 SHALL 正常工作,返回 AI 调整后的分数
- **AND** 现有代码 SHALL 无需修改即可运行
- **AND** 新增的 Optional 字段 SHALL 可以被忽略
