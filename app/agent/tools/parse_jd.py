from app.pipeline.jd_parser import JDParser

def run_parse_jd(tool_input: dict) -> dict:
    """Tool adapter: parse raw JD text into structured JDRequirements dict."""
    try:
        jd_text = tool_input["jd_text"]
        parser = JDParser()
        requirements = parser.parse(jd_text)
        return requirements.model_dump()
    except Exception as e:
        return {"error": str(e)}

TOOL_SCHEMA = {
    "name": "parse_jd",
    "description": "解析职位描述文本，提取结构化需求（技能、经验年限、学历、软技能）",
    "input_schema": {
        "type": "object",
        "properties": {
            "jd_text": {
                "type": "string",
                "description": "原始职位描述文本"
            }
        },
        "required": ["jd_text"]
    }
}
