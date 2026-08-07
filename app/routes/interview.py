from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

router = APIRouter(prefix="/api", tags=["Interview"])

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

# In-memory database to store session states
# Key: sessionId
# Value: Dict containing candidate info, message history, and metadata
sessions: Dict[str, Dict[str, Any]] = {}

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
        # Initialize or reset the session
        sessions[session_id] = {
            "candidate": request.candidate,
            "turn_count": 0,
            "history": []
        }
        return InterviewResponse(
            reply="Welcome. Let's begin your interview.",
            done=False
        )
    
    # 4. Handle Conversation Turn (when message is provided)
    # Ensure session exists
    if session_id not in sessions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session with ID '{session_id}' does not exist or has not been initialized with candidate data."
        )
    
    # Retrieve session state
    session = sessions[session_id]
    session["turn_count"] += 1
    current_turn = session["turn_count"]
    
    # Append message to history
    session["history"].append({"role": "candidate", "content": request.message})
    
    # Simulate a 3-turn interview limit to demonstrate transition to completion
    if current_turn >= 3:
        # End interview with structured feedback
        feedback = FeedbackDetail(
            summary="Candidate demonstrated foundational skills in application development. They can build basic APIs but need to deepen their understanding of enterprise agentic architectures.",
            strengths=[
                "Strong ability to scaffold FastAPI projects and define structured JSON contracts.",
                "Good familiarity with Docker configurations for containerized deployment."
            ],
            gaps=[
                "Lacks experience with building multi-agent coordinate architectures.",
                "Needs improvement on utilizing Model Context Protocol (MCP) for tool integrations."
            ],
            next=[
                "Build a project using LangGraph to understand stateful multi-agent workflows.",
                "Read the MCP documentation and implement custom tool servers."
            ]
        )
        
        response = InterviewResponse(
            reply="Interview completed.",
            done=True,
            feedback=feedback
        )
        
        # Optionally, clear the session or keep it for grades/inspection
        # We will keep it for inspection, but can clear it if memory is a constraint.
        return response
    
    # Otherwise, return a mock question and continue
    mock_questions = [
        "That's interesting. Can you tell me more about a RAG application you built and how you chunked your documents?",
        "How do you evaluate the retrieval quality of your vector database?",
    ]
    
    # Choose question based on current turn (turns are 1-indexed here)
    # Turn 1 -> mock_questions[0], Turn 2 -> mock_questions[1]
    reply_text = mock_questions[current_turn - 1] if (current_turn - 1) < len(mock_questions) else f"Mock follow-up question for turn {current_turn}."
    
    session["history"].append({"role": "interviewer", "content": reply_text})
    
    return InterviewResponse(
        reply=reply_text,
        done=False
    )
