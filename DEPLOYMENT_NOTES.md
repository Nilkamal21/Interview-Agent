# Deployment & Troubleshooting Notes

## 1. Render Cold Starts (Inactivity Sleep)
* **Live Demo URL**: [https://interview-agent-rsah.onrender.com/](https://interview-agent-rsah.onrender.com/)
* **Status**: Hosted on Render's **Free Tier**.
* **Behavior**: If the application has not received any traffic for 15 minutes, Render puts the server instance to "sleep". 
* **Note**: When you first click the demo link, the browser may take **up to 1 minute** to load as Render spins up the container. Please wait patiently; once awake, it will load the full interactive dashboard. (A background self-ping keep-alive task is configured to minimize sleep occurrences when active).

## 2. Question Generation Delays (Model Fallback)
* **Primary Model**: `llama-3.3-70b-versatile` (handles role calibration, advanced follow-ups, and grading).
* **Fallback Model**: `llama-3.1-8b-instant` (handles fallback turns).
* **Behavior**: If a question takes longer to load or generating a turn takes time, the primary Groq model tier has likely reached its rate limit (HTTP 429). 
* **Resilience**: The backend is configured with automatic error resilience. When a rate limit is detected, it logs a warning and **instantly switches to the fallback model** mid-session. The interview will proceed without crashing or returning raw stack traces.
