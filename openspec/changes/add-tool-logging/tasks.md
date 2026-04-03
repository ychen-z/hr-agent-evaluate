## 1. 创建日志基础设施

- [x] 1.1 创建 `app/utils/logger.py` 文件
- [x] 1.2 实现 `StructuredFormatter` 类,格式化为单行 JSON,包含 timestamp, level, logger, message, extra_fields
- [x] 1.3 实现 `DeveloperFormatter` 类,格式化为人类友好的多行输出,包含 emoji 指示器(🔧/✅/❌)
- [x] 1.4 创建 `tool_logger` logger 实例,配置 level 为 INFO
- [x] 1.5 根据 ENV 环境变量选择 formatter(默认 development 使用 DeveloperFormatter)
- [x] 1.6 添加 StreamHandler,输出到 stdout

## 2. 实现工具追踪装饰器

- [x] 2.1 实现 `traced_tool(tool_name=None)` 装饰器工厂函数
- [x] 2.2 装饰器生成 call*id(格式: `{tool_name}*{timestamp_ms}`)
- [x] 2.3 装饰器记录 tool_start 事件,包含 call_id, tool_name, timestamp, input_preview
- [x] 2.4 装饰器记录执行开始时间(time.time())
- [x] 2.5 装饰器使用 try/except/finally 确保异常时也记录 tool_end
- [x] 2.6 装饰器记录 tool_end 事件,包含 call_id, tool_name, duration_ms, status(success/error), output_preview, error
- [x] 2.7 装饰器使用 `@wraps(func)` 保持原函数元数据

## 3. 实现辅助工具函数

- [x] 3.1 实现 `_preview_args(args, kwargs, max_len=100)` 函数,生成参数预览字典
- [x] 3.2 实现 `_preview_output(output, max_len=100)` 函数,生成输出预览字符串
- [x] 3.3 实现 `_truncate(value, max_len)` 函数,截断长字符串并附加 "... (truncated, N total chars)"
- [x] 3.4 确保 \_truncate 对任意类型的 value 进行 str() 转换后截断

## 4. 应用装饰器到工具函数

- [x] 4.1 在 `app/agent/tools/parse_jd.py` 顶部添加 `from app.utils.logger import traced_tool` 导入
- [x] 4.2 在 `parse_jd_tool` 函数上添加 `@traced_tool("parse_jd")` 装饰器(在 `@tool` 之前)
- [x] 4.3 在 `app/agent/tools/score_candidate.py` 添加导入和装饰器到 `run_score_candidate` 函数
- [x] 4.4 在 `app/agent/tools/generate_report_html.py` 添加导入和装饰器到 `run_generate_report_html` 函数

## 5. 测试和验证

- [x] 5.1 本地运行完整流程(调用 API 或测试),观察控制台日志输出
- [x] 5.2 验证每个工具调用产生 tool_start 和 tool_end 两条日志
- [x] 5.3 验证日志包含所有必需字段(call_id, tool_name, duration_ms, status, input_preview, output_preview)
- [x] 5.4 验证输入输出超过 100 字符时正确截断
- [x] 5.5 设置 ENV=production,验证日志格式切换为 JSON
- [x] 5.6 验证异常情况下仍能记录 tool_end(status=error)且异常正常抛出
- [x] 5.7 测量工具执行时间增加,确认<5ms (实测 <1ms)

## 6. 文档和清理(可选)

- [x] 6.1 在 README.md 添加日志配置说明(ENV 环境变量)
- [x] 6.2 添加示例日志输出到文档
- [x] 6.3 如需持久化,添加 FileHandler 配置示例(注释掉)
