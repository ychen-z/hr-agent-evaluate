from fastapi import APIRouter, HTTPException, Header
from app.types.models import MatchRequest
import os

router = APIRouter()

from fastapi.responses import HTMLResponse
from app.agent.hr_agent import HRAgent, AgentLoopError, _html_store
from app.types.models import AgentResult


@router.post("/api/v1/agent/match", response_model=AgentResult)
async def agent_match_resume(
    request: MatchRequest,
    x_api_key: str = Header(None, alias="X-API-Key")
):
    api_key = os.getenv("API_KEY")
    if api_key and x_api_key != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not request.job_description or len(request.job_description.strip()) < 5:
        raise HTTPException(status_code=400, detail="Job description too short")

    try:
        agent = HRAgent()
        result = agent.run(request.resume, request.job_description)
        return result
    except AgentLoopError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable")


@router.get("/api/v1/agent/report/{session_id}", response_class=HTMLResponse)
async def get_agent_report(session_id: str):
    html = _html_store.get(session_id)
    if html is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return HTMLResponse(content=html)
