import json
import re
from langchain_core.messages import HumanMessage
from app.types.models import JDRequirements
from app.utils.llm import get_minmax_model

_PROMPT_TEMPLATE = """从以下职位描述中提取结构化需求，返回JSON格式。

职位描述:
{jd_text}

请提取以下字段并只返回JSON，不要其他内容：
{{
  "required_skills": ["技能1", "技能2"],
  "experience_years": 0,
  "education_level": "本科",
  "soft_skills": ["软技能1"]
}}

education_level 只能是以下之一：大专、本科、硕士、博士"""


class JDParser:
    def __init__(self):
        self.model = get_minmax_model()

    def parse(self, jd_text: str) -> JDRequirements:
        """Parse a job description text into structured JDRequirements.

        Raises ValueError if the model response cannot be parsed into JDRequirements.
        """
        prompt = _PROMPT_TEMPLATE.format(jd_text=jd_text)
        try:
            response = self.model.invoke([HumanMessage(content=prompt)])
            content = response.content
            # Strip markdown fences if present: ```json ... ``` or ``` ... ```
            content = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
            content = re.sub(r"\s*```$", "", content.strip())
            data = json.loads(content)
            return JDRequirements(**data)
        except Exception as e:
            raise ValueError(f"Failed to parse JD: {e}") from e
