## Why

当前评分系统使用纯算法方法(字符串匹配、数值比较),存在以下问题:

1. **技能匹配过于机械** - 无法识别语义相似的技能(如 React vs Vue)
2. **经验评估片面** - 只看年限,忽视项目质量和复杂度
3. **软技能无法量化** - 依赖简历明确列出,无法从经历中推断

引入 AI 增强评分可以大幅提升评估的准确性和深度,更接近人类 HR 的专业判断。

## What Changes

- **新增** `AIEnhancedMatcher` 类,使用 LLM 进行深度评估
- **保留** 现有算法评分作为基准(baseline),AI 在此基础上调整
- **扩展** `DimensionScore` 模型,支持 AI 推理说明、亮点、关注点
- **扩展** `MatchReport` 模型,增加整体评估摘要、优势和关注点
- **更新** 组件文档 `matcher.md`,添加 AI 增强评分章节
- **单次 LLM 调用** - 成本可控,一次性评估所有维度

## Capabilities

### New Capabilities

- `ai-candidate-evaluation`: AI 对候选人进行深度评估,包括技能语义理解、经验质量判断、软技能推断等

### Modified Capabilities

- `candidate-scoring`: 现有评分能力将被增强,从纯算法升级为 AI+算法混合模式

## Impact

**代码影响**:

- `app/pipeline/matcher.py` - 新增 `AIEnhancedMatcher` 类
- `app/types/models.py` - 扩展 `DimensionScore` 和 `MatchReport` 模型
- `app/agent/tools/score_candidate.py` - 切换到使用 `AIEnhancedMatcher`
- `docs/components/matcher.md` - 更新文档,添加 AI 增强章节

**依赖影响**:

- 依赖现有的 LLM 客户端 (`app/pipeline/jd_parser.py` 中的实现)
- 使用现有的 MiniMax API (与 JDParser 共享)

**成本影响**:

- 每个候选人增加 1 次 LLM 调用
- 预计 token 消耗: ~2000 tokens/候选人 (输入) + ~800 tokens (输出)

**兼容性**:

- 向后兼容 - 现有的 `Matcher` 保留,新增 `AIEnhancedMatcher`
- API 响应结构扩展,但保持基础字段不变
