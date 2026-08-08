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
class InterviewRequest(BaseModel):
    sessionId: str = Field(..., description="Unique identifier for the interview session")
    candidate: Optional[Dict[str, Any]] = Field(None, description="Candidate details, provided only on the first turn")
    message: Optional[str] = Field(None, description="Candidate response, provided on subsequent turns")

class FeedbackDetail(BaseModel):
    summary: str
    strengths: List[str]
    gaps: List[str]
    next: List[str]

class InterviewResponse(BaseModel):
    reply: str
    done: bool
    feedback: Optional[FeedbackDetail] = None

@router.post("/interview", response_model=InterviewResponse)
async def handle_interview(request: InterviewRequest):
    session_id = request.sessionId.strip()
    
    # 1. Validate sessionId is not empty
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
            response_payload = init_session(session_id, request.candidate)
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
