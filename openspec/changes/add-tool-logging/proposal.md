## Why

当前 HR Agent 系统缺乏可观测性,无法追踪工具调用的顺序、耗时和状态。这导致:

- 调试困难:无法定位性能瓶颈或异常原因
- 无法验证 ReAct Agent 是否按预期顺序调用工具
- 缺乏生产环境监控能力

需要引入轻量级的工具调用埋点日志系统,提供实时观测能力,同时保持最小性能开销和零额外依赖。

## What Changes

- 新增结构化日志基础设施(基于 Python 标准库 logging)
- 为三个工具函数添加自动追踪装饰器(`parse_jd`, `score_candidate`, `generate_report_html`)
- 记录每个工具调用的开始/结束时间、执行时长、输入输出预览、异常信息
- 支持开发环境(人类友好)和生产环境(结构化 JSON)两种输出格式
- 可选:添加 session 级别的追踪

## Capabilities

### New Capabilities

- `tool-logging`: 工具调用的结构化日志记录和追踪能力,包括装饰器、格式化器、logger 配置

### Modified Capabilities

<!-- 无现有 capability 的需求变更 -->

## Impact

**新增文件**:

- `app/utils/logger.py`: 日志基础设施、装饰器、格式化器

**修改文件**:

- `app/agent/tools/parse_jd.py`: 添加 `@traced_tool` 装饰器
- `app/agent/tools/score_candidate.py`: 添加 `@traced_tool` 装饰器
- `app/agent/tools/generate_report_html.py`: 添加 `@traced_tool` 装饰器
- (可选) `app/agent/hr_agent.py`: 添加 session 级别日志

**依赖**:

- 零新增依赖,仅使用 Python 标准库

**兼容性**:

- 无 breaking change,纯新增功能
- 日志输出不影响现有 API 响应
