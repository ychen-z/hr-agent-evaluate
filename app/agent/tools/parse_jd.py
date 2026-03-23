import json
from langchain_core.tools import tool
from app.pipeline.jd_parser import JDParser

# Lazy singleton — initialized on first call to avoid requiring DASHSCOPE_API_KEY
# at import time. One ChatOpenAI HTTP client is shared across all invocations.
_parser: JDParser | None = None


def _get_parser() -> JDParser:
    global _parser
    if _parser is None:
        _parser = JDParser()
    return _parser


@tool("parse_jd")
def parse_jd_tool(jd_text: str) -> str:
    """解析职位描述文本，提取结构化需求（技能、经验年限、学历、软技能），返回JSON字符串。"""
    requirements = _get_parser().parse(jd_text)
    return json.dumps(requirements.model_dump(), ensure_ascii=False)
