from pydantic import ValidationError
from app.types.models import Resume, JDRequirements
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter


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

    matcher = Matcher()
    reporter = Reporter()
    dimension_scores = matcher.match(resume_obj, req_obj)
    report = reporter.generate(dimension_scores)
    if hasattr(report, "model_dump"):
        return report.model_dump()
    return report
