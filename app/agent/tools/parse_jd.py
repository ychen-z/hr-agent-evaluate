import json
from langchain_core.tools import tool
from app.pipeline.jd_parser import JDParser


@tool("parse_jd")
def parse_jd_tool(jd_text: str) -> str:
    """解析职位描述文本，提取结构化需求（技能、经验年限、学历、软技能），返回JSON字符串。"""
    parser = JDParser()
    requirements = parser.parse(jd_text)
    return json.dumps(requirements.model_dump(), ensure_ascii=False)
