from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes.interview import router as interview_router

app = FastAPI(
    title="The Interview Agent",
    description="An adaptive, multi-turn AI technical interview agent based on student learning journeys.",
    version="0.1.0",
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

