# The Interview Agent 🚀

An adaptive, multi-turn AI technical interview agent built for the hackathon. It conducts highly personalized technical interviews grounded in a candidate's actual learning journey, evaluating conceptual and practical understanding while delivering honest, transcript-grounded feedback.

## 1. Project Overview

### The Problem
After completing a rigorous 31-day AI engineering bootcamp, learners often struggle to articulate the architectural decisions, trade-offs, and implementation details of the systems they built during job interviews. Standard interviewers ask generic questions, and traditional mock interview tools provide high-level, unhelpful feedback.

### Our Solution
**The Interview Agent** bridges this gap. It connects a candidate's actual learning analytics (completed, failed, or skipped curriculum days and attempt logs) with the core engineering curriculum. The agent acts as a skeptical but fair senior technical interviewer—dynamically calibrating question difficulty, tracking response consistency, drilling down on weak areas, and delivering strict, transcript-grounded gap analysis and recommended next steps.

---

## 2. Key Features

*   **Personalized Topic Selection:** Integrates candidates' bootcamp progress data (attempts, passed, skipped) directly with the curriculum database. It dynamically builds a personalized plan prioritizing failed and high-attempt days (indicating struggle), skipped topics (checking baseline awareness), and includes a single spot-check of a first-try pass (to verify real understanding vs luck).
*   **Topic Selection Reasoning:** Returns a human-readable choice justification for each selected curriculum topic (e.g. *"Selected because this topic was skipped — checking baseline awareness"*), visible in both the API response and the sidebar frontend dashboard.
*   **Role and Seniority Calibration:** Dynamically adjusts prompt context and question difficulty:
    *   *Technical Roles (e.g. Engineers):* Receives deep, implementation-level questions targeting architecture patterns, design tradeoffs, libraries, and hyperparameter selections.
    *   *Non-Technical Roles (e.g. Product Owners, Business Analysts):* Receives conceptual and decision-level questions focusing on *why* a particular approach was chosen, what problems it solved, and how stakeholders were impacted.
*   **Human-like Conversational Flow:** Acknowledges candidate answers in a short, natural sentence, uses contextual transitions between curriculum topics, addresses the candidate by first name once every 2–3 questions, and varies follow-up phrasing to keep the interview feeling professional and alive.
*   **Adaptive Follow-Up Logic:** Evaluates answer responsiveness in real-time. If a candidate attempts to dodge a question by repeating generic concepts or pasting off-topic blocks, the agent detects the deflection and drills deeper with specific follow-up questions instead of moving on.
*   **Transcript-Grounded Feedback & Resilience:** 
    *   Strengths and gaps are strictly grounded in what the candidate *actually said* during the conversation. 
    *   Bootcamp analytics are strictly secondary (e.g. *"This gap aligns with their bootcamp record of 4 attempts on Day 12"*), preventing the AI from assuming candidate struggles not evidenced in the chat.
    *   Topics not assessed in the interview are programmatically isolated into a separate *"Not Assessed"* list to maintain strict grading integrity.
*   **Resilience & Rate Limit Fallback:** Catching rate limits (HTTP 429) automatically transitions requests from `"llama-3.3-70b-versatile"` to `"llama-3.1-8b-instant"` mid-session, preventing crashes during demos.

---

## 3. Architecture Overview

The system is organized into a clean, decoupled layer structure:
```
├── app/
│   ├── main.py              # Application setup & Global exception handlers
│   ├── routes/
│   │   └── interview.py     # Stateful /api/interview endpoint & request validation
│   └── services/
│       ├── orchestrator.py  # Session managers, LLM retries, system prompts, evaluation
│       └── topic_selector.py# Deterministic score-weighting selector for curriculum days
├── data/
│   ├── candidates.json      # Bootcamp records (attempts, first-try rate, signals)
│   └── curriculum.json      # Course curriculum (titles, tools, learning objectives)
├── static/
│   └── index.html           # Single Page Application frontend (HTML5/CSS3/Vanilla JS)
├── scripts/
│   ├── test_topic_selection.py  # Verification of topic prioritization logic
│   └── test_mixed_performance.py# Verification of feedback accuracy under mixed answer quality
└── test_api.py              # Full end-to-end integration tests
```

*   **Data Layer:** Serves as the source of truth for the curriculum metadata and candidates' progress markers.
*   **Topic Selector (`topic_selector.py`):** Automatically selects exactly 4 distinct days to structure the personalization plan based on attempt and pass records.
*   **Orchestrator (`orchestrator.py`):** Holds session states in memory isolation. Integrates Groq SDK with custom prompt templates for question, follow-up, and final feedback generation. Enforces the strict completion threshold (minimum 8 questions across at least 4 topics).
*   **Global Exception Middleware (`main.py`):** Intercepts unexpected python errors globally to return sanitised JSON responses to the client, preventing stack traces from leaking to the frontend.
*   **Frontend UI:** Provides a glassmorphism dashboard containing candidate profiles, automated validation controls, a real-time "Personalization Plan" section showing selection justifications, a clean chat bubble timeline, and a collapsible, formatted feedback accordion.

---

## 4. Tech Stack

*   **Backend:** Python 3.10+ / FastAPI
*   **LLM Provider:** Groq Cloud API (using `llama-3.3-70b-versatile` with automatic failover to `llama-3.1-8b-instant`)
*   **Frontend:** Vanilla HTML5, CSS3 Custom Properties (sleek dark mode), and Vanilla JavaScript
*   **Deployment Support:** Fully containerized with a Docker multi-stage build, ready for Render or Railway deployment.

---

## 5. How to Run Locally

### Prerequisites
*   Python 3.10 or higher installed.
*   A Groq API Key (get one free at [console.groq.com](https://console.groq.com)).

### Setup Steps
1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd Interview-Agent
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure Environment Variables:**
    Copy the example template and input your API key:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file:
    ```env
    GROQ_API_KEY=gsk_your_groq_api_key_goes_here
    ```

4.  **Run the Server:**
    ```bash
    python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    ```

5.  **Access the App:**
    Open your browser and navigate to: [http://localhost:8000](http://localhost:8000)

---

## 6. Sample cURL Requests

### Step 1: Start Interview Session (Sends Candidate Profile)
```bash
curl -X POST "http://localhost:8000/api/interview" \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "session-readme-demo",
       "candidate": {
         "member": {
           "id": "CAND-001",
           "name": "Sarah Johnson",
           "jobRole": "Senior Data Engineer",
           "yearsExperience": 9,
           "education": "MS CS"
         },
         "missions": [
           { "day": 7, "title": "Embeddings Explained", "passed": true, "attempts": 1 },
           { "day": 12, "title": "Prompt Engineering Fundamentals", "passed": true, "attempts": 4 },
           { "day": 28, "title": "Docker & Kubernetes Deployment", "passed": true, "attempts": 3 },
           { "day": 29, "title": "Monitoring, Logging & Observability", "skipped": true }
         ]
       }
     }'
```

**Response:**
```json
{
  "reply": "Sarah, can you walk me through the design decisions you made when choosing a specific Sentence Transformer model for generating embeddings, and how you evaluated its performance?",
  "done": false,
  "interviewPlan": [
    {
      "day": 7,
      "title": "Embeddings Explained",
      "reason": "Selected as a spot-check: passed on first attempt, verifying real understanding vs luck"
    },
    {
      "day": 12,
      "title": "Prompt Engineering Fundamentals",
      "reason": "Selected due to high attempt count (4 attempts) indicating struggle"
    },
    {
      "day": 28,
      "title": "Docker & Kubernetes Deployment",
      "reason": "Selected due to high attempt count (3 attempts) indicating struggle"
    },
    {
      "day": 29,
      "title": "Monitoring, Logging & Observability",
      "reason": "Selected because this topic was skipped — checking baseline awareness"
    }
  ]
}
```

### Step 2: Mid-Interview Turn (Sending Answer)
```bash
curl -X POST "http://localhost:8000/api/interview" \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "session-readme-demo",
       "message": "I used Sentence Transformers because I wanted to run them locally on the container to reduce latency and save API costs."
     }'
```

**Response:**
```json
{
  "reply": "Acknowledge: That makes sense to save roundtrip network time. Follow-up: How did you evaluate if local embedding similarity met your quality standards compared to OpenAI models?",
  "done": false
}
```

### Step 3: Final Turn (Completed Interview + Feedback Report)
Sent after 8+ questions and 4 distinct days have been covered:
```bash
curl -X POST "http://localhost:8000/api/interview" \
     -H "Content-Type: application/json" \
     -d '{
       "sessionId": "session-readme-demo",
       "message": "I didn'\''t implement structured logging in detail, I just printed exceptions to console."
     }'
```

**Response:**
```json
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "Sarah demonstrated a strong high-level understanding of system architectures but struggled to provide implementation details across curriculum topics Day 7, Day 12, Day 28, and Day 29. Her responses remained generic when pressed on logging and monitoring configurations.",
    "strengths": [
      "Clear articulation of local embeddings performance latency trade-offs on Day 7."
    ],
    "gaps": [
      "Struggled to articulate Docker multi-stage configurations on Day 28.",
      "Failed to design structured logging configurations using Python built-in logging module on Day 29."
    ],
    "next": [
      "Review multi-stage Docker builds to optimize backend image sizes.",
      "Re-examine python'\''s logging module handlers and formats as detailed in Day 29 materials."
    ],
    "notAssessed": [
      "Day 8: Vector Databases Overview",
      "Day 10: The Retrieval & Matching Engine",
      "Day 16: Chatbot Backend & API Integration",
      "Day 22: Multi-Agent Orchestration",
      "Day 23: Model Context Protocol (MCP)",
      "Day 31: Capstone Project & Final Demo"
    ]
  }
}
```

---

## 7. Testing

We created automated scripts inside the repository to validate all business rules:
*   **`python -m scripts.test_topic_selection`**: Verifies that the selection weighting algorithm correctly prioritizes failed, skipped, and high-attempt topics while bounding easy days to a maximum of 1 spot-check.
*   **`python -m scripts.test_mixed_performance`**: Runs a full 10-turn mock interview. It sends high-quality answers for Days 7/12, and vague/weak answers for Days 28/29. It asserts that:
    1.  *Strengths* ONLY credit Days 7 and 12.
    2.  *Gaps* ONLY flag Days 28 and 29 (and Day 12 if the candidate repeatedly dodged follow-ups).
    3.  The *Executive Summary* accurately records mixed performance.
*   **`python test_api.py`**: Executes an end-to-end integration test validating FastAPI routing, Pydantic schemas, and error boundaries.

---

## 8. Live Demo

The project is deployed and accessible at:
🔗 **[Live Interview Agent Dashboard](https://interview-agent-production.up.railway.app/)** *(Replace with your deployed URL)*
