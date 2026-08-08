from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from app.routes.interview import router as interview_router
import traceback
import asyncio
import httpx
import os

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

@app.get("/")
async def serve_frontend():
    """
    Serves the static index.html file for the root path.
    """
    return FileResponse("static/index.html")

# Mount static folder
app.mount("/static", StaticFiles(directory="static"), name="static")

async def keep_alive_loop(self_url: str):
    """
    Background task to ping the application's health check endpoint every 10 minutes,
    preventing free-tier instances (like Render or Railway) from going to sleep.
    """
    health_url = f"{self_url.rstrip('/')}/health"
    print(f"[INFO] Initializing background self-ping keep-alive for URL: {health_url}")
    
    async with httpx.AsyncClient() as client:
        while True:
            # Sleep for 10 minutes (600 seconds)
            await asyncio.sleep(600)
            try:
                response = await client.get(health_url, timeout=10.0)
                print(f"[DEBUG] Self-ping status code: {response.status_code}")
            except Exception as e:
                print(f"[WARNING] Self-ping task failed: {str(e)}")

@app.on_event("startup")
async def startup_event():
    """
    Startup event to initialize background keep-alive ping tasks if SELF_URL is configured.
    """
    self_url = os.getenv("SELF_URL")
    if self_url:
        asyncio.create_task(keep_alive_loop(self_url))

