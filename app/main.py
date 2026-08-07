from fastapi import FastAPI

app = FastAPI(
    title="The Interview Agent",
    description="An adaptive, multi-turn AI technical interview agent based on student learning journeys.",
    version="0.1.0",
)

@app.get("/health")
async def health_check():
    """
    Health check endpoint for deployment environments (Render, Railway, etc.).
    """
    return {"status": "ok"}
