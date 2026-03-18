from fastapi import APIRouter, HTTPException, Header
from app.types.models import MatchRequest, MatchReport
from app.pipeline.jd_parser import JDParser
from app.pipeline.matcher import Matcher
from app.pipeline.reporter import Reporter
import os

router = APIRouter()
parser = JDParser()
matcher = Matcher()
reporter = Reporter()

@router.post("/api/v1/match", response_model=MatchReport)
async def match_resume(
    request: MatchRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    api_key = os.getenv("API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not request.job_description or len(request.job_description.strip()) < 5:
        raise HTTPException(status_code=400, detail="Job description too short")
    
    try:
        requirements = parser.parse(request.job_description)
        
        if not requirements.required_skills and requirements.experience_years == 0:
            raise HTTPException(status_code=400, detail="Unable to parse JD requirements")
        
        dimension_scores = matcher.match(request.resume, requirements)
        
        if not dimension_scores:
            raise HTTPException(status_code=500, detail="Unable to calculate scores")
        
        result = reporter.generate(dimension_scores)
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")
