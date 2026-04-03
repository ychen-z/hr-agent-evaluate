# JDParser 组件文档

## 概述

`JDParser` 是 HR Agent 系统的核心组件之一,负责将非结构化的职位描述(Job Description)文本转换为结构化数据。它是整个简历匹配流程的第一步,为后续的匹配和评分提供标准化的需求数据。

## 核心功能

### 功能定位

**职位描述解析器** - 自动从 JD 文本中提取关键信息

```
输入 (非结构化):                    输出 (结构化):
┌──────────────────────────┐      ┌─────────────────────────┐
│ "招聘高级Python工程师     │      │ JDRequirements:        │
│  要求:                   │      │  - required_skills:    │
│  - 3年以上开发经验        │ ──▶  │    ["Python","FastAPI"]│
│  - 熟悉Python、FastAPI    │      │  - experience_years: 3 │
│  - 本科学历              │      │  - education_level:    │
│  - 良好的沟通能力"        │      │    "本科"              │
└──────────────────────────┘      │  - soft_skills:        │
   (自然语言文本)                    │    ["沟通能力"]        │
                                   └─────────────────────────┘
                                        (JSON 对象)
```

## 在系统中的位置

```
用户提交 JD 文本
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                    HR Agent                             │
│  ┌───────────────────────────────────────────────────┐ │
│  │  Agent 循环 (LangGraph)                           │ │
│  │                                                   │ │
│  │  Step 1: 调用 parse_jd 工具                      │ │
│  │  ┌──────────────────────────────┐                │ │
│  │  │  parse_jd_tool()             │                │ │
│  │  │    ↓                         │                │ │
│  │  │  JDParser.parse(jd_text) ◄───┼─ 这里!         │ │
│  │  │    │                         │                │ │
│  │  │    ├─ 1. 构建 prompt         │                │ │
│  │  │    ├─ 2. 调用 LLM            │                │ │
│  │  │    ├─ 3. 解析 JSON           │                │ │
│  │  │    └─ 4. 返回 JDRequirements │                │ │
│  │  └──────────────────────────────┘                │ │
│  │           ▼                                       │ │
│  │  返回: JDRequirements {                          │ │
│  │    required_skills: ["Python", "FastAPI"],       │ │
│  │    experience_years: 3,                          │ │
│  │    education_level: "本科",                      │ │
│  │    soft_skills: ["沟通能力"]                     │ │
│  │  }                                               │ │
│  │           ▼                                       │ │
│  │  Step 2: 调用 score_candidate 工具               │ │
│  │         (使用 JDRequirements 进行匹配)            │ │
│  │           ▼                                       │ │
│  │  Step 3: 生成报告                                │ │
│  └───────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 数据模型

### 输入

```python
jd_text: str  # 任意格式的职位描述文本
```

**示例**:

```python
jd_text = """
招聘高级Python工程师
要求:
- 3年以上Python开发经验
- 熟悉FastAPI、Django等Web框架
- 本科及以上学历,计算机相关专业
- 具备良好的沟通能力和团队协作精神
"""
```

### 输出

```python
class JDRequirements(BaseModel):
    required_skills: list[str]      # 技术技能要求列表
    experience_years: int           # 工作年限要求(整数)
    education_level: str            # 学历要求 ("大专"/"本科"/"硕士"/"博士")
    soft_skills: list[str]          # 软技能要求列表
```

**示例**:

```python
JDRequirements(
    required_skills=["Python", "FastAPI", "Django"],
    experience_years=3,
    education_level="本科",
    soft_skills=["沟通能力", "团队协作"]
)
```

## 工作原理

### 1. Prompt 工程

JDParser 使用精心设计的 prompt 引导 LLM 提取结构化信息:

````python
_PROMPT_TEMPLATE = """你是一个职位需求提取助手。从职位描述中提取结构化信息,以JSON格式返回。

职位描述:
{jd_text}

请严格按照以下JSON格式返回(不要有任何其他文字):
```json
{{
  "required_skills": ["提取的技能1", "技能2"],
  "experience_years": 提取的年限数字,
  "education_level": "本科",
  "soft_skills": ["软技能1", "软技能2"]
}}
````

规则:

- required_skills: 技术技能列表
- experience_years: 工作年限(整数),未提及则为0
- education_level: 只能是 "大专"/"本科"/"硕士"/"博士" 之一,未提及则为"本科"
- soft_skills: 软技能列表(沟通能力、团队协作等)

只返回JSON,不要有其他解释文字。"""

````

**设计要点**:
- ✅ 明确角色定位("职位需求提取助手")
- ✅ 提供清晰的 JSON 示例
- ✅ 定义默认值规则(未提及时的处理)
- ✅ 强调"只返回 JSON"(减少解释文字)

### 2. LLM 调用

使用 **MiniMax-M2.5** 模型进行语义理解和信息提取:

```python
response = self.model.invoke([HumanMessage(content=prompt)])
content = response.content  # LLM 返回的文本
````

### 3. 智能 JSON 提取

多策略提取 JSON,处理各种 LLM 响应格式:

````python
# 策略 1: 提取 markdown 代码块
# 匹配: ```json { ... } ```
json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL | re.IGNORECASE)
if json_match:
    content = json_match.group(1)

# 策略 2: 去除代码围栏
# 处理: ``` { ... } ```
content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
content = re.sub(r"\s*```$", "", content.strip())

# 策略 3: 从文本中查找 JSON 对象
# 处理: 一些解释文字 { ... } 更多文字
if not content.startswith("{"):
    json_obj_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_obj_match:
        content = json_obj_match.group(0)
````

**为什么需要多策略?**

LLM 返回的格式可能不一致:

- 有时带 markdown 代码块: ` ```json {...} ``` `
- 有时只有代码围栏: ` ``` {...} ``` `
- 有时带解释文字: `根据要求提取如下: {...} 以上是结果`
- 有时是纯 JSON: `{...}`

### 4. 验证和转换

```python
# JSON 解析
data = json.loads(content)

# Pydantic 模型验证
return JDRequirements(**data)
```

Pydantic 会自动验证:

- 字段类型是否正确
- 必需字段是否存在
- 字段值是否符合约束

## 使用示例

### 基本使用

```python
from app.pipeline.jd_parser import JDParser

# 创建解析器实例
parser = JDParser()

# 解析 JD 文本
jd_text = """
招聘Python工程师
要求:
- 3年Python开发经验
- 熟悉FastAPI
- 本科学历
"""

requirements = parser.parse(jd_text)

print(requirements.required_skills)    # ["Python", "FastAPI"]
print(requirements.experience_years)   # 3
print(requirements.education_level)    # "本科"
print(requirements.soft_skills)        # []
```

### 在 Agent 工具中使用

```python
# app/agent/tools/parse_jd.py
from app.pipeline.jd_parser import JDParser

_parser: JDParser | None = None

def _get_parser() -> JDParser:
    global _parser
    if _parser is None:
        _parser = JDParser()
    return _parser

@tool("parse_jd")
def parse_jd_tool(jd_text: str) -> str:
    """解析职位描述文本，提取结构化需求"""
    requirements = _get_parser().parse(jd_text)
    return json.dumps(requirements.model_dump(), ensure_ascii=False)
```

## 错误处理

### 常见错误类型

#### 1. 空响应错误

```python
ValueError: LLM returned empty response
```

**原因**: LLM API 返回空内容
**可能场景**:

- API 配额耗尽
- 网络问题
- 内容审查拦截

#### 2. JSON 解析错误

```python
ValueError: Failed to parse JSON from LLM response: Expecting value: line 1 column 1 (char 0)
Content: <实际内容>
```

**原因**: LLM 返回的不是有效 JSON
**可能场景**:

- LLM 返回纯文本解释
- JSON 格式错误
- 提取策略失败

#### 3. 字段验证错误

```python
pydantic.ValidationError: 1 validation error for JDRequirements
experience_years
  Input should be a valid integer
```

**原因**: LLM 返回的字段类型不符合预期
**可能场景**:

- `experience_years` 是字符串 "3年" 而不是整数 3
- `required_skills` 是字符串而不是列表

### 调试方法

#### 启用 DEBUG 日志

```python
import logging
logging.basicConfig(level=logging.INFO)

# 运行 parser,会输出:
# [DEBUG] LLM raw response (len=256): ...
# [DEBUG] Extracted from markdown: ...
# [DEBUG] Final content: ...
```

#### 查看 LLM 原始响应

```python
parser = JDParser()
try:
    requirements = parser.parse(jd_text)
except ValueError as e:
    print(f"解析失败: {e}")
    # 错误消息中会包含 LLM 返回内容的前 500 字符
```

## 性能考虑

### 典型执行时间

```
成功场景:
- LLM 调用: 1-3 秒
- JSON 提取和验证: <10 毫秒
- 总耗时: ~1-3 秒

失败场景:
- LLM 超时: 10+ 秒
- 重试: 取决于重试策略
```

### 优化建议

#### 1. 单例模式

```python
# ✅ 推荐: 复用同一个 parser 实例
_parser = JDParser()  # 只创建一次

def parse(jd_text: str):
    return _parser.parse(jd_text)
```

#### 2. 缓存结果

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def parse_jd_cached(jd_text: str) -> JDRequirements:
    """相同 JD 文本不重复调用 LLM"""
    return parser.parse(jd_text)
```

#### 3. 异步调用

```python
async def parse_async(jd_text: str) -> JDRequirements:
    """异步版本,适合批量处理"""
    response = await self.model.ainvoke([HumanMessage(content=prompt)])
    # ... 后续处理
```

## 依赖关系

```
JDParser
├── langchain_core.messages.HumanMessage  # LangChain 消息格式
├── app.utils.llm.get_minmax_model       # LLM 模型获取
├── app.types.models.JDRequirements      # 输出数据模型
└── Python 标准库
    ├── json                             # JSON 解析
    └── re                               # 正则表达式
```

## 测试

### 单元测试示例

````python
# tests/test_jd_parser.py
from unittest.mock import MagicMock, patch
from app.pipeline.jd_parser import JDParser

def test_parse_valid_jd():
    """测试正常的 JD 解析"""
    with patch("app.pipeline.jd_parser.get_minmax_model") as mock_model:
        # Mock LLM 响应
        mock_response = MagicMock()
        mock_response.content = '''
        ```json
        {
          "required_skills": ["Python", "FastAPI"],
          "experience_years": 3,
          "education_level": "本科",
          "soft_skills": ["沟通能力"]
        }
        ```
        '''
        mock_model.return_value.invoke.return_value = mock_response

        # 执行测试
        parser = JDParser()
        result = parser.parse("招聘Python工程师，3年经验")

        # 验证结果
        assert result.required_skills == ["Python", "FastAPI"]
        assert result.experience_years == 3
        assert result.education_level == "本科"

def test_parse_with_text_around_json():
    """测试带解释文字的响应"""
    with patch("app.pipeline.jd_parser.get_minmax_model") as mock_model:
        mock_response = MagicMock()
        mock_response.content = '根据要求提取如下: {"required_skills": ["Java"], "experience_years": 5, "education_level": "硕士", "soft_skills": []} 以上是结果'
        mock_model.return_value.invoke.return_value = mock_response

        parser = JDParser()
        result = parser.parse("招聘Java工程师")

        assert result.required_skills == ["Java"]
        assert result.experience_years == 5

def test_parse_empty_response():
    """测试空响应处理"""
    with patch("app.pipeline.jd_parser.get_minmax_model") as mock_model:
        mock_response = MagicMock()
        mock_response.content = ""
        mock_model.return_value.invoke.return_value = mock_response

        parser = JDParser()

        with pytest.raises(ValueError, match="LLM returned empty response"):
            parser.parse("测试文本")
````

## 常见问题 (FAQ)

### Q1: JDParser 支持哪些语言?

**A**: 目前 prompt 是中文设计的,主要支持中文 JD。如需支持英文或其他语言,需要修改 `_PROMPT_TEMPLATE`。

### Q2: 如何提高解析准确率?

**A**:

1. 改进 prompt 模板,提供更清晰的示例
2. 在 prompt 中添加领域专有名词列表
3. 使用更强大的 LLM 模型
4. 对特定行业定制 prompt

### Q3: 解析失败率大概多少?

**A**:

- 正常格式的 JD: <5% 失败率
- 格式混乱的 JD: 10-20% 失败率
- 主要失败原因: LLM 返回格式不符合预期

### Q4: 能否不使用 LLM,直接用规则提取?

**A**: 可以,但效果会差很多:

- ✅ 规则方法: 速度快,成本低
- ❌ 规则方法: 准确率低,维护困难
- ✅ LLM 方法: 准确率高,适应性强
- ❌ LLM 方法: 速度慢,有调用成本

### Q5: 如何处理复杂的 JD(如多个岗位合并)?

**A**:

1. 在 prompt 中明确说明"只提取第一个岗位"
2. 或者预处理 JD,拆分成多个独立岗位
3. 或者扩展 `JDRequirements` 模型支持多岗位

## 未来改进方向

### 1. 支持更多字段

```python
class JDRequirements(BaseModel):
    required_skills: list[str]
    experience_years: int
    education_level: str
    soft_skills: list[str]
    # 新增字段
    salary_range: Optional[tuple[int, int]] = None  # 薪资范围
    location: Optional[str] = None                   # 工作地点
    company_size: Optional[str] = None               # 公司规模
    industry: Optional[str] = None                   # 行业领域
```

### 2. 结构化输出 (Structured Output)

使用 LLM 的 structured output 功能,强制返回符合 schema 的 JSON:

```python
from langchain_core.output_parsers import JsonOutputParser

parser = JsonOutputParser(pydantic_object=JDRequirements)
chain = prompt | model | parser
result = chain.invoke({"jd_text": jd_text})
```

### 3. 增加置信度评分

```python
class JDRequirements(BaseModel):
    required_skills: list[str]
    experience_years: int
    education_level: str
    soft_skills: list[str]
    confidence: float  # 0-1, 表示提取的置信度
```

### 4. 支持增量提取

用户可以手动修正提取结果:

```python
requirements = parser.parse(jd_text)
# 用户修正
requirements.required_skills.append("Docker")
# 保存修正结果用于训练
```

## 参考资料

- [LangChain 文档](https://python.langchain.com/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [MiniMax API 文档](https://www.minimaxi.com/document/guides)
- [Prompt Engineering 最佳实践](https://platform.openai.com/docs/guides/prompt-engineering)

## 维护历史

| 日期       | 版本  | 变更说明                              |
| ---------- | ----- | ------------------------------------- |
| 2026-04-03 | 1.1.0 | 增加多策略 JSON 提取,改进 prompt 模板 |
| 2026-03-23 | 1.0.0 | 初始版本,基于 MiniMax 模型            |
