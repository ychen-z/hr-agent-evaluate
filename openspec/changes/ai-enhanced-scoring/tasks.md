## 1. 数据模型扩展

- [x] 1.1 在 `app/types/models.py` 中扩展 `DimensionScore` 类,添加 `baseline_score`, `adjustment_reasoning`, `highlights`, `concerns` 字段(全部 Optional)
- [x] 1.2 在 `app/types/models.py` 中扩展 `MatchReport` 类,添加 `overall_assessment`, `top_strengths`, `key_concerns` 字段(全部 Optional)
- [x] 1.3 验证数据模型向后兼容性(现有代码读取 `score` 字段应该正常工作)

## 2. LLM 客户端提取

- [x] 2.1 创建 `app/utils/llm_client.py` 文件
- [x] 2.2 从 `app/pipeline/jd_parser.py` 中提取 LLM 调用逻辑到 `LLMClient` 类
- [x] 2.3 实现 `LLMClient.invoke(prompt, response_format)` 方法,支持 JSON 格式输出
- [x] 2.4 添加 JSON 解析和错误处理逻辑(参考 JDParser 的实现)
- [x] 2.5 重构 `JDParser` 使用新的 `LLMClient`(确保不破坏现有功能)

## 3. AI 评估 Prompt 设计

- [x] 3.1 在 `app/pipeline/matcher.py` 中定义 `AI_EVALUATION_PROMPT` 常量
- [x] 3.2 Prompt 包含角色定义(资深技术招聘专家)
- [x] 3.3 Prompt 包含 4 个维度的评估要求(技能、经验、学历、软技能)
- [x] 3.4 Prompt 包含输出格式要求(JSON schema 示例)
- [x] 3.5 Prompt 包含评分原则(客观、具体、引用证据)

## 4. AIEnhancedMatcher 实现

- [x] 4.1 在 `app/pipeline/matcher.py` 中创建 `AIEnhancedMatcher` 类,继承 `Matcher`
- [x] 4.2 实现 `__init__` 方法,初始化 `LLMClient`
- [x] 4.3 实现 `match` 方法:
  - 调用 `super().match()` 获取算法基准分
  - 调用 `_ai_evaluate()` 进行 AI 评估
  - 返回 AI 调整后的结果
- [x] 4.4 实现 `_ai_evaluate` 方法:
  - 构建 prompt(包含简历、需求、基准分)
  - 调用 LLM
  - 解析 JSON 响应
  - 转换为 `DimensionScore` 对象
- [x] 4.5 实现 `_build_prompt` 方法,填充 prompt 模板
- [x] 4.6 实现 `_parse_ai_response` 方法,解析 LLM 返回的 JSON

## 5. 错误处理与降级

- [x] 5.1 在 `_ai_evaluate` 中添加 try-except,捕获所有异常
- [x] 5.2 LLM 调用失败时记录警告日志
- [x] 5.3 LLM 调用失败时返回算法基准分(降级策略)
- [x] 5.4 添加 JSON 解析失败的错误处理(记录原始响应)
- [x] 5.5 添加 API Key 失效的处理(401 错误)

## 6. 工具集成

- [x] 6.1 在 `app/agent/tools/score_candidate.py` 中添加环境变量检查 `USE_AI_ENHANCED_MATCHER`
- [x] 6.2 根据环境变量选择使用 `Matcher` 或 `AIEnhancedMatcher`
- [x] 6.3 默认值设置为 "false"(保守策略)
- [x] 6.4 添加日志输出当前使用的 Matcher 类型

## 7. Reporter 适配

- [x] 7.1 在 `app/pipeline/reporter.py` 中检查 `DimensionScore` 是否包含 AI 字段
- [x] 7.2 如果包含 AI 字段,在生成 `reasons` 时优先使用 `highlights`
- [x] 7.3 如果包含 `overall_assessment`,添加到 `MatchReport` 输出
- [x] 7.4 确保 Reporter 对两种模式的输入都兼容

## 8. 文档更新

- [x] 8.1 在 `docs/components/matcher.md` 中添加 "AI 增强评分" 章节
- [x] 8.2 文档包含 AI 增强的工作原理图
- [x] 8.3 文档包含 Prompt 设计说明
- [x] 8.4 文档包含使用示例(如何启用 AI 增强)
- [x] 8.5 文档包含降级策略说明
- [x] 8.6 文档包含成本估算信息
- [x] 8.7 文档包含我们在 explore 模式讨论的方案对比(作为优化选择章节)

## 9. 测试

- [x] 9.1 添加 `test_llm_client.py`,测试 LLM 客户端基本功能
- [x] 9.2 添加 `test_ai_enhanced_matcher.py`,测试 AI 增强评分
- [x] 9.3 测试用例: 算法基准分正确获取
- [x] 9.4 测试用例: AI 评估成功的场景
- [x] 9.5 测试用例: LLM 失败降级到算法评分
- [x] 9.6 测试用例: JSON 解析失败降级
- [x] 9.7 测试用例: 数据模型扩展字段正确填充
- [x] 9.8 测试用例: 向后兼容性(现有代码能正常运行)
- [ ] 9.9 手动测试: 使用真实 LLM API 评估候选人

## 10. 配置与部署

- [x] 10.1 在 `.env.example` 中添加 `USE_AI_ENHANCED_MATCHER` 配置项及说明
- [x] 10.2 在 `readme.md` 中更新环境变量说明
- [x] 10.3 在 `readme.md` 中添加 AI 增强评分的功能说明
- [x] 10.4 验证环境变量开关工作正常(true/false 切换)
