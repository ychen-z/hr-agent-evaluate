from app.types.models import AgentResult, MatchReport


def test_agent_result_model():
    report = MatchReport(
        overall_score=85,
        dimensions={},
        recommendation="推荐",
        reasons=["技术栈匹配度高"]
    )
    result = AgentResult(
        session_id="abc-123",
        report=report,
        html="<html></html>",
        reasoning="候选人综合评估良好"
    )
    assert result.session_id == "abc-123"
    assert result.report.overall_score == 85
    assert result.html == "<html></html>"
    assert result.reasoning == "候选人综合评估良好"


from app.agent.hr_agent import AgentLoopError


def test_agent_loop_error_is_exception():
    err = AgentLoopError("too many iterations")
    assert isinstance(err, Exception)
    assert str(err) == "too many iterations"
