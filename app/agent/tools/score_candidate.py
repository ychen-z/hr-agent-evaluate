import os
import logging
from pydantic import ValidationError
from app.types.models import Resume, JDRequirements
from app.pipeline.matcher import Matcher, AIEnhancedMatcher
from app.pipeline.reporter import Reporter
from app.utils.logger import traced_tool

logger = logging.getLogger("hr_agent.tools")

@traced_tool("score_candidate")
def run_score_candidate(resume: dict, requirements: dict) -> dict:
    """Score a candidate resume against parsed JD requirements.

    Returns a MatchReport dict with overall_score, dimensions, recommendation, reasons.
    Raises ValueError on invalid input.
    """
    try:
        resume_obj = Resume(**resume)
        req_obj = JDRequirements(**requirements)
    except (ValidationError, KeyError, TypeError) as e:
        raise ValueError(f"Invalid input: {e}") from e

    # 根据环境变量选择 Matcher
    use_ai_enhanced = os.getenv("USE_AI_ENHANCED_MATCHER", "false").lower() == "true"
    
    if use_ai_enhanced:
        logger.info("[score_candidate] Using AI-enhanced matcher")
        matcher = AIEnhancedMatcher()
    else:
        logger.info("[score_candidate] Using traditional algorithm matcher")
        matcher = Matcher()
    
    reporter = Reporter()
    dimension_scores = matcher.match(resume_obj, req_obj)
    report = reporter.generate(dimension_scores)
    if hasattr(report, "model_dump"):
        return report.model_dump()
    return report
