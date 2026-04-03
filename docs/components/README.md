# HR Agent 组件文档

本目录包含 HR Agent 系统各个核心组件的详细文档。

## 📚 组件列表

### 1. JDParser (职位描述解析器)

- **文档**: [jd-parser.md](./jd-parser.md)
- **功能**: 使用 LLM 将非结构化职位描述转换为结构化需求对象
- **输入**: JD 文本
- **输出**: Requirements (技能、经验、学历、软技能)

### 2. Matcher (匹配评分引擎)

- **文档**: [matcher.md](./matcher.md)
- **功能**: 对比简历与需求,计算多维度匹配分数
- **输入**: Resume + Requirements
- **输出**: DimensionScores (技能、经验、学历、软技能各维度评分)

### 3. Reporter (报告生成器)

- **文档**: [reporter.md](./reporter.md)
- **功能**: 将评分结果转换为最终评估报告
- **输入**: DimensionScores
- **输出**: MatchReport (综合评分、推荐结论、理由)

### 4. HRAgent (AI Agent 调度器)

- **文档**: [hr-agent.md](./hr-agent.md)
- **功能**: 基于 LangGraph ReAct 模式,智能编排整个评估流程
- **输入**: Resume + JD Text
- **输出**: AgentResult (报告 + HTML + 推理过程)

### 5. Tools (工具集)

- **文档**: [tools.md](./tools.md)
- **功能**: 三个核心工具函数供 Agent 调用
- **工具列表**:
  - `parse_jd`: 解析职位描述
  - `score_candidate`: 评分候选人
  - `generate_report_html`: 生成 HTML 报告

---

## 🗂️ 文档导航

### 按功能分类

**数据处理**

- [JDParser](./jd-parser.md) - JD 文本解析

**匹配评分** (待补充)

- Matcher - 简历与需求匹配
- Reporter - 报告生成

**AI Agent** (待补充)

- HRAgent - Agent 主循环
- Tools - Agent 工具集

**前端界面** (待补充)

- Frontend - 用户界面

### 按开发阶段分类

**已完成**

- ✅ [JDParser](./jd-parser.md) - v1.1.0

**待补充**

- ⏳ Matcher
- ⏳ Reporter
- ⏳ HRAgent
- ⏳ Tools
- ⏳ Frontend

---

## 📝 文档模板

每个组件文档应包含以下部分:

1. **概述** - 组件的作用和定位
2. **核心功能** - 主要功能说明
3. **在系统中的位置** - 架构图和数据流
4. **数据模型** - 输入输出定义
5. **工作原理** - 实现细节
6. **使用示例** - 代码示例
7. **错误处理** - 常见错误和调试
8. **性能考虑** - 优化建议
9. **依赖关系** - 依赖库和模块
10. **测试** - 单元测试示例
11. **常见问题 (FAQ)** - 问答形式
12. **未来改进方向** - 规划和展望
13. **参考资料** - 相关链接
14. **维护历史** - 版本记录

---

## 🔗 相关文档

- [项目 README](../../readme.md)
- [API 文档](../../docs/api/)
- [架构设计](../../docs/architecture/)

---

## 🤝 贡献指南

如果你想添加或更新组件文档:

1. 使用上述文档模板
2. 包含清晰的代码示例和图表
3. 更新本索引文件
4. 确保文档准确性和可读性

---

## 快速索引

| 组件     | 核心功能         | 技术栈                 |
| -------- | ---------------- | ---------------------- |
| JDParser | LLM 解析职位描述 | MiniMax-M2.5, Pydantic |
| Matcher  | 多维度匹配评分   | Python, 集合运算       |
| Reporter | 生成评估报告     | Pydantic, 加权计算     |
| HRAgent  | ReAct Agent 编排 | LangGraph, MiniMax     |
| Tools    | 工具函数封装     | LangChain, 日志追踪    |

---

## 文档更新历史

| 日期       | 组件     | 版本   |
| ---------- | -------- | ------ |
| 2026-04-03 | JDParser | v1.0.0 |
| 2026-04-03 | Matcher  | v1.0.0 |
| 2026-04-03 | Reporter | v1.0.0 |
| 2026-04-03 | HRAgent  | v1.0.0 |
| 2026-04-03 | Tools    | v1.0.0 |

---

最后更新: 2026-04-03
