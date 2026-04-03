import logging
import json
import time
import os
from datetime import datetime
from functools import wraps
from typing import Any, Callable


# ============================================================================
# Formatters
# ============================================================================

class StructuredFormatter(logging.Formatter):
    """格式化为单行 JSON,适用于生产环境"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 添加额外的结构化字段
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        return json.dumps(log_data, ensure_ascii=False)


class DeveloperFormatter(logging.Formatter):
    """人类友好的格式化器,适用于开发环境"""
    
    def format(self, record):
        if hasattr(record, "extra_fields"):
            fields = record.extra_fields
            event = fields.get("event")
            
            if event == "tool_start":
                return (
                    f"🔧 [{fields['tool_name']}] START\n"
                    f"   Call ID: {fields['call_id']}\n"
                    f"   Input: {fields['input_preview']}\n"
                )
            elif event == "tool_end":
                status_emoji = "✅" if fields['status'] == 'success' else "❌"
                error_line = f"   Error: {fields.get('error')}\n" if fields.get('error') else ""
                return (
                    f"{status_emoji} [{fields['tool_name']}] END\n"
                    f"   Duration: {fields['duration_ms']}ms\n"
                    f"   Status: {fields['status']}\n"
                    f"   Output: {fields.get('output_preview', 'N/A')}\n"
                    f"{error_line}"
                )
        
        return super().format(record)


# ============================================================================
# Logger Configuration
# ============================================================================

# 创建专门的工具调用 logger
tool_logger = logging.getLogger("hr_agent.tools")
tool_logger.setLevel(logging.INFO)

# 根据环境选择格式化器
ENV = os.getenv("ENV", "development")

if ENV == "development":
    # 开发环境: 人类友好格式
    formatter = DeveloperFormatter()
else:
    # 生产环境: 结构化 JSON
    formatter = StructuredFormatter()

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
tool_logger.addHandler(console_handler)

# 可选: 文件处理器 (生产环境)
# from logging.handlers import RotatingFileHandler
# file_handler = RotatingFileHandler(
#     "logs/tools.log",
#     maxBytes=10*1024*1024,  # 10MB
#     backupCount=5
# )
# file_handler.setFormatter(StructuredFormatter())
# tool_logger.addHandler(file_handler)


# ============================================================================
# Utility Functions
# ============================================================================

def _truncate(value: Any, max_len: int) -> str:
    """截断长数据"""
    str_value = str(value)
    if len(str_value) <= max_len:
        return str_value
    return str_value[:max_len] + f"... (truncated, {len(str_value)} total chars)"


def _preview_args(args: tuple, kwargs: dict, max_len: int = 100) -> dict:
    """生成参数预览,避免记录过长数据"""
    preview = {}
    
    # 位置参数
    if args:
        for i, arg in enumerate(args):
            preview[f"arg_{i}"] = _truncate(arg, max_len)
    
    # 关键字参数
    for key, value in kwargs.items():
        preview[key] = _truncate(value, max_len)
    
    return preview


def _preview_output(output: Any, max_len: int = 100) -> str:
    """生成输出预览"""
    return _truncate(output, max_len)


# ============================================================================
# Decorator
# ============================================================================

def traced_tool(tool_name: str = None):
    """
    装饰器: 自动追踪工具调用
    
    记录:
    - 工具名称
    - 开始/结束时间
    - 执行时长
    - 输入参数预览
    - 输出结果预览
    - 异常信息
    """
    def decorator(func: Callable) -> Callable:
        name = tool_name or func.__name__
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成调用 ID
            call_id = f"{name}_{int(time.time() * 1000)}"
            
            # 参数预览 (避免记录过长数据)
            input_preview = _preview_args(args, kwargs)
            
            # 记录开始
            tool_logger.info(
                f"Tool started: {name}",
                extra={
                    "extra_fields": {
                        "event": "tool_start",
                        "call_id": call_id,
                        "tool_name": name,
                        "input_preview": input_preview,
                    }
                }
            )
            
            start_time = time.time()
            error = None
            result = None
            
            try:
                # 执行工具
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = e
                raise
            finally:
                # 记录结束 (无论成功或失败)
                duration = time.time() - start_time
                
                output_preview = _preview_output(result) if not error else None
                error_info = str(error) if error else None
                
                tool_logger.info(
                    f"Tool finished: {name}",
                    extra={
                        "extra_fields": {
                            "event": "tool_end",
                            "call_id": call_id,
                            "tool_name": name,
                            "duration_ms": round(duration * 1000, 2),
                            "status": "error" if error else "success",
                            "output_preview": output_preview,
                            "error": error_info,
                        }
                    }
                )
        
        return wrapper
    return decorator
