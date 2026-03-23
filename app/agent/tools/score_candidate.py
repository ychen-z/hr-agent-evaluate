from pydantic import ValidationError
from app.types.models import Resume, JDRequirements
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter

def run_score_candidate(tool_input: dict) -> dict:
    """Tool adapter: score a candidate resume against parsed JD requirements."""
    try:
        resume = Resume(**tool_input["resume"])
        requirements = JDRequirements(**tool_input["requirements"])
    except (ValidationError, KeyError) as e:
        return {"error": str(e)}

    try:
        matcher = Matcher()
        reporter = Reporter()
        dimension_scores = matcher.match(resume, requirements)
        report = reporter.generate(dimension_scores)
        # reporter.generate() returns a plain dict; guard in case that ever changes
        if hasattr(report, "model_dump"):
            return report.model_dump()
        return report
    except Exception as e:
        return {"error": str(e)}

TOOL_SCHEMA = {
    "name": "score_candidate",
    "description": "\u6839\u636e\u89e3\u6790\u540e\u7684\u804c\u4f4d\u9700\u6c42\u5bf9\u5019\u9009\u4eba\u7b80\u5386\u8fdb\u884c\u8bc4\u5206\uff0c\u8fd4\u56de\u5404\u7ef4\u5ea6\u5206\u6570\u548c\u7efc\u5408\u63a8\u8350\u7ed3\u8bba",
    "input_schema": {
        "type": "object",
        "properties": {
            "resume": {
                "type": "object",
                "description": "\u5019\u9009\u4eba\u7b80\u5386\uff08Resume \u7ed3\u6784\u4f53\uff09"
            },
            "requirements": {
                "type": "object",
                "description": "\u7531 parse_jd \u8fd4\u56de\u7684\u804c\u4f4d\u9700\u6c42\u7ed3\u6784\u4f53"
            }
        },
        "required": ["resume", "requirements"]
    }
}
