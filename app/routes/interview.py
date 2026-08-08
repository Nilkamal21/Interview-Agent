from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
import json
from app.services.orchestrator import init_session, process_turn

router = APIRouter(prefix="/api", tags=["Interview"])

@router.get("/candidates")
async def get_candidates():
    """
    Returns the full candidates list to populate the frontend selection dashboard.
    """
    try:
        path = os.path.join("data", "candidates.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load candidates dataset: {str(e)}"
        )

# Pydantic models for API validation
class CandidateMember(BaseModel):
    id: str = Field(..., description="Candidate unique ID")
    name: str = Field(..., description="Candidate name")
    jobRole: str = Field(..., description="Candidate job role")
    yearsExperience: int = Field(..., description="Years of experience")
    education: str = Field(..., description="Candidate education details")

class CandidateMission(BaseModel):
    day: int = Field(..., description="Day number of the curriculum")
    title: str = Field(..., description="Curriculum day title")
    passed: Optional[bool] = Field(None, description="Whether they passed the mission")
    attempts: Optional[int] = Field(None, description="Number of attempts on the mission")
    skipped: Optional[bool] = Field(None, description="Whether they skipped the mission")

class CandidateDetail(BaseModel):
    member: CandidateMember
    missions: List[CandidateMission]
    signals: Optional[Dict[str, Any]] = None

class InterviewRequest(BaseModel):
    sessionId: str = Field(
        ..., 
        min_length=1, 
        pattern=r"^[a-zA-Z0-9\-_]+$", 
        description="Unique identifier for the interview session (alphanumeric, hyphens, underscores)"
    )
    candidate: Optional[CandidateDetail] = Field(None, description="Candidate details, provided only on the first turn")
    message: Optional[str] = Field(None, description="Candidate response, provided on subsequent turns")

class FeedbackDetail(BaseModel):
    summary: str
    strengths: List[str]
    gaps: List[str]
    next: List[str]
    notAssessed: Optional[List[str]] = None

class InterviewPlanItem(BaseModel):
    day: int = Field(..., description="Curriculum day number")
    title: str = Field(..., description="Curriculum day title")
    reason: str = Field(..., description="Interviewer reason for selecting this day")

class InterviewResponse(BaseModel):
    reply: str
    done: bool
    feedback: Optional[FeedbackDetail] = None
    interviewPlan: Optional[List[InterviewPlanItem]] = None

@router.post("/interview", response_model=InterviewResponse)
async def handle_interview(request: InterviewRequest):
    session_id = request.sessionId.strip()
    
    # 1. Validate sessionId is not empty (redundant but safe fallback)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sessionId cannot be empty."
        )
    
    # 2. Validate that either candidate or message is provided, but not neither
    if request.candidate is None and request.message is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'candidate' (to start session) or 'message' (to continue session) must be provided."
        )
    
    # 3. Handle Start Interview (when candidate is provided)
    if request.candidate is not None:
        try:
            # Convert Pydantic model to a dict before passing it to service layer
            response_payload = init_session(session_id, request.candidate.dict())
            return InterviewResponse(**response_payload)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize session: {str(e)}"
            )
    
    # 4. Handle Conversation Turn (when message is provided)
    try:
        response_payload = process_turn(session_id, request.message)
        return InterviewResponse(**response_payload)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during the interview turn: {str(e)}"
        )
