## Context

当前评分系统 (`Matcher` + `Scorer`) 使用纯算法方法:

- 技能匹配: 字符串集合比较
- 经验评估: 年限数值比较
- 学历评估: 枚举等级映射
- 软技能: 字符串集合比较

这种方法快速、确定,但缺乏语义理解和深度判断能力。

**约束条件**:

- 成本控制: 每个候选人仅 1 次 LLM 调用
- 响应时间: 整体评估时间 < 5秒
- 可解释性: AI 评分必须提供详细推理
- 兼容性: 保留现有 API 结构,扩展字段

**技术栈**:

- LLM: MiniMax-M2.5 (已用于 JDParser)
- 框架: Pydantic 数据模型
- 现有模块: `app/pipeline/matcher.py`, `app/utils/scorer.py`

## Goals / Non-Goals

**Goals:**

- 使用 LLM 进行深度候选人评估,识别语义相似技能、评估经验质量、推断软技能
- 保留算法评分作为基准,AI 在此基础上调整
- 输出详细的推理说明、亮点和关注点
- 单次 LLM 调用完成所有维度评估
- 向后兼容现有代码

**Non-Goals:**

- 不完全替代算法评分(保留算法作为基准和兜底)
- 不进行多轮对话式评估(成本过高)
- 不支持自定义评分维度(保持 4 维度结构)
- 不改变现有权重配置(技能 40%、经验 30%、学历 15%、软技能 15%)

## Decisions

### 决策 1: 混合架构 - AI 主导 + 算法基准

**选择**: 先执行算法评分获得基准分,再用 AI 调整

**理由**:

- ✅ 算法快速确定,提供可靠基线
- ✅ AI 可以参考基准分,避免偏离过大
- ✅ 算法作为兜底,当 LLM 失败时可降级
- ✅ 可对比 AI 前后的分数变化

**备选方案**:

- ❌ 纯 AI 评分: 成本高,不稳定,难以兜底
- ❌ 投票制(AI + 算法各 50%): 权重分配困难,AI 优势受限

---

### 决策 2: 单次 LLM 调用评估所有维度

**选择**: 设计一个综合 prompt,一次性评估 4 个维度

**理由**:

- ✅ 成本可控(1 次调用 vs 4 次调用)
- ✅ LLM 可以进行跨维度综合判断
- ✅ 响应时间更快(并行 vs 串行)

**Prompt 结构**:

```python
EVALUATION_PROMPT = """
【岗位需求】{requirements}
【候选人简历】{resume}
【算法基准分】{baseline_scores}

评估以下 4 个维度:
1. 技术技能 (考虑语义相似度、技能深度...)
2. 工作经验 (项目质量、复杂度、相关性...)
3. 教育背景 (学历等级、专业相关性...)
4. 软技能 (从经历推断...)

输出 JSON: {dimensions, overall_assessment}
"""
```

**备选方案**:

- ❌ 每维度单独调用: 成本 4 倍,无法跨维度综合
- ❌ 分两次调用(技能+经验一次,其他一次): 复杂度增加,收益不明显

---

### 决策 3: 数据模型扩展而非替换

**选择**: 在现有 `DimensionScore` 和 `MatchReport` 基础上扩展字段

**扩展字段**:

```python
class DimensionScore(BaseModel):
    score: int  # AI 调整后的分数
    baseline_score: Optional[int] = None  # 新增: 算法基准分
    # ... 现有字段 ...
    adjustment_reasoning: Optional[str] = None  # 新增: AI 推理
    highlights: Optional[list[str]] = None  # 新增: 亮点
    concerns: Optional[list[str]] = None  # 新增: 关注点

class MatchReport(BaseModel):
    # ... 现有字段 ...
    overall_assessment: Optional[dict] = None  # 新增: 整体评估
    top_strengths: Optional[list[str]] = None  # 新增: 核心优势
    key_concerns: Optional[list[str]] = None  # 新增: 关键关注点
```

**理由**:

- ✅ 向后兼容,现有代码无需修改
- ✅ 渐进式升级,可选择性使用新字段
- ✅ 保留基准分供对比和调试

**备选方案**:

- ❌ 创建全新模型: 破坏兼容性,迁移成本高
- ❌ 替换现有字段: 需要大量现有代码改动

---

### 决策 4: 类继承 - `AIEnhancedMatcher` 继承 `Matcher`

**选择**: 新建 `AIEnhancedMatcher` 类继承 `Matcher`

```python
class AIEnhancedMatcher(Matcher):
    def __init__(self):
        super().__init__()
        self.llm_client = self._init_llm()

    def match(self, resume, requirements) -> dict[str, DimensionScore]:
        # 1. 调用父类获取算法基准分
        baseline_scores = super().match(resume, requirements)

        # 2. 使用 LLM 调整评分
        ai_scores = self._ai_evaluate(resume, requirements, baseline_scores)

        # 3. 合并返回
        return ai_scores
```

**理由**:

- ✅ 代码复用,继承现有算法逻辑
- ✅ 易于切换(工具中改一行代码)
- ✅ 保留现有 `Matcher` 作为备用

**备选方案**:

- ❌ 修改现有 `Matcher`: 破坏兼容性,回滚困难
- ❌ 装饰器模式: 过度设计,不如继承直观

---

### 决策 5: LLM 客户端复用 JDParser 的实现

**选择**: 提取 `JDParser` 中的 LLM 客户端为共享模块

**实现**:

```python
# app/utils/llm_client.py (新建)
class LLMClient:
    def __init__(self):
        self.api_key = os.getenv("MINIMAX_API_KEY")
        self.group_id = os.getenv("MINIMAX_GROUP_ID")
        self.base_url = "https://api.minimax.chat/v1/text/chatcompletion_v2"

    def invoke(self, prompt: str, response_format: str = "json") -> dict:
        # ... 通用调用逻辑 ...
```

**理由**:

- ✅ 避免代码重复
- ✅ 统一 LLM 调用逻辑
- ✅ 便于后续添加重试、缓存等功能

**备选方案**:

- ❌ 在 `AIEnhancedMatcher` 中重新实现: 代码重复,维护困难
- ❌ 直接依赖 `JDParser`: 耦合过强,职责混乱

---

### 决策 6: 错误处理与降级策略

**选择**: LLM 失败时降级到算法评分

```python
def match(self, resume, requirements):
    baseline_scores = super().match(resume, requirements)

    try:
        ai_scores = self._ai_evaluate(...)
        return ai_scores
    except LLMException as e:
        logger.warning(f"AI evaluation failed, using baseline: {e}")
        return baseline_scores  # 降级到算法评分
```

**理由**:

- ✅ 保证系统可用性
- ✅ 算法评分虽然简单,但可靠
- ✅ 用户不会因 LLM 故障而无法使用

**降级场景**:

- LLM API 超时
- LLM 返回格式错误
- API Key 失效

---

## Risks / Trade-offs

### 风险 1: LLM 输出不稳定

**风险**: LLM 可能返回非 JSON 格式或不符合 schema 的数据

**缓解**:

- 使用 response_format="json" 约束输出格式
- 在 prompt 中明确要求 JSON 格式,提供示例
- 添加 JSON 解析和验证逻辑(参考 JDParser 的实现)
- 失败时降级到算法评分

---

### 风险 2: 评分一致性问题

**风险**: 同一候选人多次评估可能得到不同分数

**缓解**:

- 在 prompt 中强调"客观评估"
- 提供算法基准分作为锚点
- 记录每次评估的推理过程,便于审计
- 后续可考虑添加结果缓存(相同简历+JD 返回相同结果)

---

### 风险 3: 成本增加

**风险**: 每个候选人增加 1 次 LLM 调用

**缓解**:

- 单次调用评估所有维度,避免多次调用
- 控制 prompt 长度,减少 token 消耗
- 可配置开关,允许降级到纯算法模式
- 监控成本,设置预警阈值

**预估成本** (MiniMax 价格: ¥0.015/1K tokens):

- 输入: ~2000 tokens × ¥0.015 = ¥0.03/候选人
- 输出: ~800 tokens × ¥0.015 = ¥0.012/候选人
- 总计: **¥0.042/候选人** (~$0.006)

---

### 权衡 1: 可解释性 vs 简洁性

**权衡**: AI 推理说明详细但冗长

**决策**: 优先可解释性,允许冗长输出

**理由**:

- HR 需要理解评分依据
- 详细说明有助于候选人反馈
- 可在前端选择性展示(摘要 vs 详情)

---

### 权衡 2: 灵活性 vs 一致性

**权衡**: AI 可以灵活判断,但可能不一致

**决策**: 接受一定不一致性,换取灵活性

**理由**:

- 人类 HR 评估也存在主观差异
- AI 的灵活判断能发现算法遗漏的优点
- 可通过优化 prompt 提高一致性

---

## Migration Plan

### 阶段 1: 并行运行(灰度)

```python
# app/agent/tools/score_candidate.py
USE_AI_ENHANCED = os.getenv("USE_AI_ENHANCED_MATCHER", "false") == "true"

def run_score_candidate(resume, requirements):
    if USE_AI_ENHANCED:
        matcher = AIEnhancedMatcher()
    else:
        matcher = Matcher()  # 保留现有逻辑

    return matcher.match(resume, requirements)
```

**步骤**:

1. 默认关闭 AI 增强(`USE_AI_ENHANCED=false`)
2. 内部测试打开 AI 增强,对比结果
3. 小范围用户测试
4. 逐步扩大比例

---

### 阶段 2: 全面切换

- 将 `USE_AI_ENHANCED` 默认值改为 `true`
- 保留环境变量开关,允许紧急降级
- 监控 LLM 调用成功率和响应时间

---

### 阶段 3: 清理(可选)

- 如果 AI 增强运行稳定(如 3 个月无问题)
- 可考虑移除旧的 `Matcher`,只保留 `AIEnhancedMatcher`
- 但建议保留,作为兜底方案

---

### 回滚策略

如果发现问题,可立即回滚:

```bash
# 方式 1: 环境变量
export USE_AI_ENHANCED_MATCHER=false

# 方式 2: 代码回滚
git revert <commit>
```

---

## Open Questions

### Q1: 是否需要缓存 AI 评估结果?

**场景**: 同一简历+JD 组合可能多次评估

**待定**:

- 缓存策略(内存 vs Redis)
- 缓存失效时间
- 缓存 key 设计(简历 hash + JD hash)

**决策时机**: 实施后观察实际重复评估频率

---

### Q2: 是否需要 A/B 测试框架?

**场景**: 对比 AI 增强 vs 纯算法的实际效果

**待定**:

- 评估指标(HR 满意度、offer 接受率等)
- A/B 分流逻辑
- 数据收集方案

**决策时机**: 如果需要量化评估效果,可在阶段 1 引入

---

### Q3: 是否支持自定义 prompt?

**场景**: 不同岗位类型可能需要不同评估标准

**待定**:

- Prompt 模板化
- 岗位类型配置(技术岗 vs 管理岗 vs 销售岗)

**决策时机**: 当前 scope 较大,建议后续迭代
