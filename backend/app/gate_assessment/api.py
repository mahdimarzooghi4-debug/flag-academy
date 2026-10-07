from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.gate_assessment.candidate_projection import (
    load_candidate_gate_projection,
)
from app.identity.auth import ActorContext, require_role

router = APIRouter(prefix="/api/v1", tags=["gate-assessment"])


class CandidateGateResponse(BaseModel):
    gate_code: str
    gate_name: str
    status: str
    evidence_gaps: list[str]
    remediation_status: str | None


class CandidateGateProjectionResponse(BaseModel):
    gates: list[CandidateGateResponse]


@router.get(
    "/me/gate-assessments",
    response_model=CandidateGateProjectionResponse,
)
async def get_my_gate_assessments(
    actor: Annotated[ActorContext, Depends(require_role("CANDIDATE"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateGateProjectionResponse:
    projection = await load_candidate_gate_projection(
        db,
        organization_context_id=actor.organization_context_id,
        subject_person_id=actor.person_id,
    )
    return CandidateGateProjectionResponse(
        gates=[
            CandidateGateResponse(
                gate_code=item.gate_code,
                gate_name=item.gate_name,
                status=item.status,
                evidence_gaps=list(item.evidence_gaps),
                remediation_status=item.remediation_status,
            )
            for item in projection.gates
        ]
    )
