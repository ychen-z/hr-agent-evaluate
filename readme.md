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

### 3. 生成评估报告

输出专业的 HTML 可视化报告，包含：

- 综合评分（0-100）
- 各维度分数条形图
- 推荐/不推荐结论
- 评估理由说明

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
├── .env                 # 环境变量配置（需自行创建）
├── .env.example         # 环境变量示例
└── requirements.txt     # Python 依赖
```

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

```
DASHSCOPE_API_KEY=your_dashscope_api_key_here
BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
API_KEY=your_api_key_here
```

### 3. 启动项目

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

### 4. 访问应用

- 前端页面：<http://localhost:8001>
- API 文档：<http://localhost:8001/docs>
- 健康检查：<http://localhost:8001/health>

## 🔌 API 接口

| 方法 | 路径                                | 说明                 |
| ---- | ----------------------------------- | -------------------- |
| POST | `/api/v1/match`                     | 简历匹配（简单模式） |
| POST | `/api/v1/agent/match`               | Agent 智能匹配       |
| GET  | `/api/v1/agent/report/{session_id}` | 获取 HTML 报告       |

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

### Q: Mock 模式是什么？

**A:** 当未配置 `DASHSCOPE_API_KEY` 或 `BASE_URL` 环境变量时，系统会自动切换到 Mock 模式，使用简单的规则匹配算法进行演示，无需调用 LLM API。

## 📄 许可证

MIT License
