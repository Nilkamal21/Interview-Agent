from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.routes.interview import router as interview_router
import traceback

app = FastAPI(
    title="The Interview Agent",
    description="An adaptive, multi-turn AI technical interview agent based on student learning journeys.",
    version="0.1.0",
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions globally to return a clean JSON error response
    rather than a raw stack trace, while logging it to the console.
    """
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"An unexpected server error occurred: {str(exc)}"}
    )

# Include routes
app.include_router(interview_router)

@app.get("/health")
async def health_check():
    """
    Health check endpoint for deployment environments (Render, Railway, etc.).
    """
    return {"status": "ok"}

# Serve static files at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")

