# HR Agent 智能简历匹配系统

一个基于 AI 的人力资源工具，用于自动化候选人简历筛选和评估。

## 🎯 项目功能

### 1. 职位描述解析

自动从 JD（Job Description）中提取结构化需求：

- 技术技能要求
- 工作经验年限
- 学历要求
- 软技能要求

### 2. 候选人评估

对候选人简历进行多维度评分：

- 📊 技术技能匹配度
- 💼 工作经验匹配度
- 🎓 教育背景匹配度
- 🤝 软技能匹配度

**✨ AI 增强评分** (可选):

- 🤖 使用 AI 进行深度评估,识别语义相似技能
- 🧠 评估经验质量而非仅看年限
- 💡 从项目经历推断软技能
- 📝 提供详细的推理说明和亮点/关注点

### 3. 生成评估报告

输出专业的 HTML 可视化报告，包含：

- 综合评分（0-100）
- 各维度分数条形图
- 推荐/不推荐结论
- 评估理由说明

**🎨 增强版报告** (可选):

- 📋 多层次区块布局 (概览 → 亮点 → 关注点 → 详细评分 → 对比 → 建议)
- 💡 AI亮点卡片 (浅蓝渐变,自动图标匹配)
- ⚠️ 关注点卡片 (浅黄警告色)
- 🤖 AI推理过程展示 (每个维度的调整说明)
- 📈 算法vs AI对比表格 (文字柱状图)
- 🎯 面试建议生成 (基于评估结果的规则引擎)
- 📱 响应式设计 (移动端友好)
- 🖨️ 打印优化 (适合存档)

## 🏗️ 技术架构

```
HR Agent 系统
├── FastAPI 后端服务
├── LangGraph Agent（AI 工具调用循环）
│   ├── parse_jd 工具 - 解析职位描述
│   ├── score_candidate 工具 - 评分候选人
│   └── generate_report_html 工具 - 生成报告
├── 前端展示页面（HTML/Tailwind CSS）
└── LLM 支持（通义千问/MiniMax）
```

## 📁 项目结构

```
hr-agent/
├── app/
│   ├── agent/           # HR Agent 核心逻辑
│   │   ├── hr_agent.py  # Agent 主循环
│   │   └── tools/       # 工具适配器
│   ├── api/             # FastAPI 路由接口
│   ├── pipeline/        # JD 解析、匹配、报告生成流水线
│   ├── static/          # 前端页面
│   ├── types/           # 数据模型定义
│   ├── utils/           # 工具函数（LLM 配置等）
│   └── main.py          # 应用入口
├── tests/               # 测试文件
├── docs/                # 文档
│   └── components/      # 组件文档（详细技术文档）
├── .env                 # 环境变量配置（需自行创建）
├── .env.example         # 环境变量示例
└── requirements.txt     # Python 依赖
```

### 📖 详细文档

- **[组件文档](./docs/components/)** - 各核心组件的详细技术文档
  - [JDParser - 职位描述解析器](./docs/components/jd-parser.md)

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# 必填: LLM API Key
DASHSCOPE_API_KEY=your_dashscope_api_key_here
BASE_URL=https://api.minimaxi.com/v1

# 可选: 启用 AI 增强评分 (默认: false)
# 启用后使用 AI 深度评估候选人,成本约 ¥0.042/候选人
USE_AI_ENHANCED_MATCHER=true

# 可选: 启用增强版报告 (默认: false)
# 启用后生成多层次、视觉优化的评估报告
USE_ENHANCED_REPORT=true
```

**环境变量说明**:

| 变量                      | 说明             | 默认值  | 必填 |
| ------------------------- | ---------------- | ------- | ---- |
| `DASHSCOPE_API_KEY`       | LLM API 密钥     | -       | 是   |
| `BASE_URL`                | LLM API 地址     | -       | 是   |
| `USE_AI_ENHANCED_MATCHER` | 启用 AI 增强评分 | `false` | 否   |
| `USE_ENHANCED_REPORT`     | 启用增强版报告   | `false` | 否   |

**AI 增强评分特性**:

- ✅ 识别语义相似的技能 (React vs Vue)
- ✅ 评估经验质量 (项目复杂度、技术深度)
- ✅ 从工作经历推断软技能 (带团队→领导力)
- ✅ 提供详细推理说明、亮点和关注点
- ✅ 失败时自动降级到算法评分 (保证可用性)
- 📊 成本: 每个候选人约 ¥0.042 (~$0.006)

### 3. 启动项目

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 4. 访问应用

- 前端页面：<http://localhost:8001>
- API 文档：<http://localhost:8001/docs>
- 健康检查：<http://localhost:8001/health>

## 🔌 API 接口

| 方法 | 路径                                | 说明           |
| ---- | ----------------------------------- | -------------- |
| POST | `/api/v1/agent/match`               | Agent 智能匹配 |
| GET  | `/api/v1/agent/report/{session_id}` | 获取 HTML 报告 |

### 请求示例

```bash
curl -X POST http://localhost:8001/api/v1/agent/match \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{
    "resume": {
      "name": "张三",
      "email": "zhangsan@example.com",
      "phone": "13800138000",
      "education": [{"degree": "本科", "major": "计算机", "school": "北京大学", "year": 2018}],
      "experience": [{"company": "字节跳动", "position": "Python工程师", "duration": "3年", "description": "后端开发"}],
      "skills": ["Python", "FastAPI", "PostgreSQL"],
      "soft_skills": ["沟通能力", "团队协作"]
    },
    "job_description": "招聘Python工程师，3年经验，熟悉FastAPI"
  }'
```

## 📊 工具调用日志

系统内置了轻量级的工具调用日志追踪功能,用于观测 AI Agent 的工具调用情况。

### 日志配置

通过 `ENV` 环境变量控制日志输出格式:

**开发环境**(默认):

```bash
# 不设置 ENV 或设置为 development
uvicorn app.main:app --reload
```

输出人类友好的格式:

```
🔧 [parse_jd] START
   Call ID: parse_jd_1775197468673
   Input: {'jd_text': 'Python工程师，3年经验，熟悉FastAPI'}

✅ [parse_jd] END
   Duration: 1245.32ms
   Status: success
   Output: {"hard_skills":["Python","FastAPI"],...}
```

**生产环境**:

```bash
ENV=production uvicorn app.main:app
```

输出结构化 JSON 格式:

```json
{"timestamp":"2026-04-03T06:23:55.093878Z","level":"INFO","logger":"hr_agent.tools","message":"Tool started: parse_jd","event":"tool_start","call_id":"parse_jd_1775197468673","tool_name":"parse_jd","input_preview":{"jd_text":"Python工程师..."}}
{"timestamp":"2026-04-03T06:23:56.339210Z","level":"INFO","logger":"hr_agent.tools","message":"Tool finished: parse_jd","event":"tool_end","call_id":"parse_jd_1775197468673","tool_name":"parse_jd","duration_ms":1245.32,"status":"success","output_preview":"{\"hard_skills\":[..."}
```

### 日志字段说明

| 字段             | 说明                                |
| ---------------- | ----------------------------------- |
| `event`          | 事件类型: `tool_start` / `tool_end` |
| `call_id`        | 调用唯一标识                        |
| `tool_name`      | 工具名称                            |
| `duration_ms`    | 执行耗时(毫秒)                      |
| `status`         | 执行状态: `success` / `error`       |
| `input_preview`  | 输入参数预览(截断到100字符)         |
| `output_preview` | 输出结果预览(截断到100字符)         |
| `error`          | 异常信息(如有)                      |

### 隐私保护

- 输入输出自动截断到 100 字符,防止完整记录敏感信息
- 生产环境建议配置适当的日志访问权限

## 🧪 运行测试

```bash
pytest -v
```

## ❓ 常见问题

### Q: 为什么获取不到 `os.getenv("DASHSCOPE_API_KEY")` 的值？

**A:** FastAPI 不会自动加载 `.env` 文件。需要使用 `python-dotenv`：

```python
from dotenv import load_dotenv

# 在应用启动时加载 .env 文件
load_dotenv()
```

本项目已在 `app/main.py` 中配置了自动加载。

## 📄 许可证

MIT License
