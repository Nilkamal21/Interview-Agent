# AI Usage Log — The Interview Agent

This document records the actual prompts used throughout development, in chronological order, as part of the hackathon's authenticity requirements. These prompts were given to an AI coding agent (Antigravity) to build the project incrementally, phase by phase.

---

## Phase -1 — Project Context

```
I'm building a project for a hackathon called "The Interview Agent." Here's 
the full context before we start building anything — just read and 
acknowledge, don't generate code yet.

THE PROBLEM:
There's a 31-day "AI Cohort" bootcamp teaching enterprise AI engineering 
(RAG, vector databases, prompt engineering, agentic AI, MCP, deployment). 
After finishing, learners struggle to articulate what they built and why in 
technical interviews. I need to build an AI agent that conducts a realistic, 
adaptive, multi-turn technical interview based on each candidate's actual 
learning journey through the cohort — not a generic scripted quiz.

WHAT I'M GIVEN (all three files will be placed in a data/ folder in this repo):
1. curriculum.json — the full 31-day syllabus: 8 modules, each day has a 
   title, type (SETUP/BUILD/LEARN/SHIP_IT/CAPSTONE), tools used, and learning 
   objectives.
2. candidates.json — per-candidate profiles: job role, years of experience, 
   education, and a "missions" array showing which curriculum days they 
   completed, how many attempts each took, whether they passed, or whether 
   they skipped it entirely. Plus aggregate signals (commit days, first-try 
   rate, etc).
3. technical-specs.md — the exact API contract I must implement: a single 
   POST /api/interview endpoint that's stateful across multiple calls via a 
   sessionId, starts with a candidate object, continues via message turns, 
   and ends with a done:true response containing structured feedback 
   (summary/strengths/gaps/next).

WHAT THE FINAL PRODUCT MUST DO:
- Join a candidate's mission data against the curriculum to figure out what 
  to interview them on — prioritizing days they struggled with (high 
  attempts, failed) or skipped, while also spot-checking days they breezed 
  through
- Ask at least 8 questions spanning at least 4 different curriculum days
- Generate genuine follow-up questions based on the candidate's previous 
  answer, not pre-scripted branches
- Adapt tone/difficulty to the candidate's seniority (jobRole, yearsExperience)
- Maintain full conversation context across the interview
- End with structured, specific feedback referencing actual days and answers, 
  not generic praise
- Expose exactly the HTTP contract defined in technical-specs.md, since this 
  gets hit by automated grading

CONSTRAINTS:
- No auth, no persistent accounts, no voice, no long-term memory across 
  sessions — session state can be in-memory
- I'm building this incrementally in phases, each phase will be its own git 
  commit, so keep changes scoped to what I ask for in each phase rather than 
  jumping ahead
- Stack: Python/FastAPI backend. LLM provider: Groq API (OpenAI-compatible 
  chat completions endpoint), using a model like llama-3.3-70b-versatile or 
  llama-3.1-8b-instant depending on speed/quality tradeoff. I will provide 
  GROQ_API_KEY as an environment variable — never hardcode it.

Confirm you understand the project, then wait for my Phase 0 instructions.
```

---

## Phase 0 — Setup

```
Scaffold a FastAPI project for a hackathon submission. Structure:
- app/main.py (FastAPI app entrypoint)
- app/routes/ (for future endpoints)
- data/curriculum.json, data/candidates.json, data/technical-specs.md 
  (I will place these files here myself — just create the folder)
- requirements.txt
- Add a GET /health endpoint returning {"status": "ok"}
- Add a Dockerfile suitable for deployment on Render/Railway
- Add a .gitignore for Python

Also add a .env.example file with GROQ_API_KEY=your_key_here, and make sure 
.env is in .gitignore so I never accidentally commit my real key.

Keep it minimal, this is step 1 of a multi-phase build.
```

---

## Phase 1 — Spec-Compliant Endpoint

```
Read data/technical-specs.md in this repo for the exact API contract.

Add a POST /api/interview endpoint matching that spec exactly:
- Request has sessionId, and either "candidate" (first call, starts a session) 
  or "message" (later calls, continues an existing session)
- Maintain session state in an in-memory dict keyed by sessionId
- Response shape: {"reply": str, "done": bool}, and on completion also include 
  "feedback": {summary, strengths, gaps, next}
- For now, stub the reply logic with a placeholder response — I'll wire in real 
  logic in later phases
- Return a clear error if sessionId is missing, or if message is sent for a 
  session that doesn't exist yet

Also add a simple test script (curl commands or a Python script) I can run to 
verify start → turn → completion against the running server.
```

---

## Phase 2 — Data Layer (Curriculum × Candidate Join)

```
Read data/curriculum.json and data/candidates.json in this repo.

Write a function select_interview_topics(candidate: dict, curriculum: dict) -> list[dict]
that:
- Joins candidate["missions"] against curriculum["days"] on the "day" field
- Prioritizes days where the candidate had high attempts (struggled) or failed 
  (passed: false)
- Includes lighter-touch awareness questions for skipped days
- Also includes a couple of "too easy" days (passed on attempt 1) to verify 
  real understanding vs luck
- Returns at least 4 distinct days, each with the day's title, objectives, 
  tools, and the candidate's mission result for that day

Put this in app/services/topic_selector.py.

Write a quick test script that runs this against 2-3 different candidates from 
data/candidates.json (pick contrasting ones — a struggling candidate and a 
strong one) and prints the selected days for each, so I can sanity check the 
output differs meaningfully.
```

---

## Phase 3 — LLM Orchestrator (Groq)

```
Update: we're using Groq's free API tier for all LLM calls in this project, 
not OpenAI or Anthropic directly.

Use the Groq Python SDK (pip install groq) with this pattern:

from groq import Groq
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[...],
    temperature=0.7
)

Requirements:
- Add "groq" to requirements.txt
- Read GROQ_API_KEY from environment variable only — never hardcode it
- Add GROQ_API_KEY=your_key_here to .env.example, and confirm .env is in 
  .gitignore
- Use model "llama-3.3-70b-versatile" for all question generation, follow-up 
  reasoning, and feedback generation calls going forward
- If you already scaffolded any LLM client code before this message, update 
  it to use Groq instead

Confirm this is wired in correctly before we continue to the next phase.
```

```
Build the core interview orchestrator in app/services/orchestrator.py.

Use the Groq API via their OpenAI-compatible client for generation.

Requirements:
- On session start, call select_interview_topics() to get the candidate's 
  interview plan, store it in session state along with an empty Q&A history 
  and question counter
- System prompt: define an interviewer persona — a skeptical but fair senior 
  technical interviewer. Calibrate question difficulty/tone based on the 
  candidate's jobRole and yearsExperience (e.g. push harder on a Distinguished 
  Engineer, be more foundational with an intern)
- On each turn (candidate's message received):
  1. Evaluate the previous answer for completeness/correctness
  2. Decide: ask a follow-up on the same day, or move to the next day in the plan
  3. Generate the next question grounded in that day's objectives/tools from 
     curriculum.json
- Track total questions asked and distinct days covered in session state
- Do NOT allow completion (done: true) until at least 8 questions have been 
  asked AND at least 4 distinct days have been covered
- Wire this orchestrator into the /api/interview endpoint from Phase 1, 
  replacing the stubbed logic

Show me the full system prompt you used so I can review and tune it.
```

---

## Phase 4 — Feedback Generation

```
Read the feedback schema in data/technical-specs.md.

When the orchestrator decides the interview is complete (8+ questions, 4+ days 
covered), add a final LLM call that generates structured feedback from the 
full conversation transcript:
- summary: 2-3 sentences, referencing specific curriculum days discussed
- strengths: concrete points tied to specific answers/days, not generic praise
- gaps: concrete weak areas tied to specific days/answers, especially where 
  the candidate's mission data (skipped/high-attempts/failed) matched what 
  they showed in the interview
- next: actionable recommendations (e.g. "revisit Day 8 vector database 
  indexing strategies")

Wire this into the /api/interview endpoint so the final response includes 
this feedback object per the spec.
```

---

## Phase 5 — Frontend

```
Build a minimal chat frontend (plain HTML/JS) that:
- Generates a sessionId and lets me pick a candidate from data/candidates.json 
  to start an interview
- Sends requests to POST /api/interview and renders the conversation as a chat
- Clearly shows when done: true, and renders the feedback object nicely 
  (summary/strengths/gaps/next as separate sections)
- Keep styling simple and clean, this needs to be presentable to hackathon judges

Serve it from the same backend, whichever is simpler to deploy together.
```

---

## Phase 6 — Bug Fixes & Human-Like Flow

### Fix: Topic selection weighting, opening dead-turn, duplicate completion message

```
I need to fix several issues found during testing. Please address all of these:

1. TOPIC SELECTION WEIGHTING BUG
Review select_interview_topics() in app/services/topic_selector.py. When I 
tested with Alex Turner's profile (data/candidates.json), it selected days 
that weren't actually his weakest areas. 

Fix the scoring logic so it correctly weights:
- Highest priority: failed missions (passed: false)
- Second priority: high attempts (3+) even if eventually passed
- Third priority: skipped missions (light-touch awareness questions only)
- Lowest priority: passed on first attempt (only include 1 of these max, as 
  a "verify real understanding" spot check)

2. NO OPENING "YES" TURN — SKIP STRAIGHT TO QUESTION 1
Currently the first exchange is a generic "Welcome, let's begin" message 
that the candidate has to respond to before the real first question starts. 
Remove this dead turn entirely. On session start, the very first reply 
should already BE the first real technical question.

3. VERIFY QUESTION COUNT AND DAY COUNT LOGIC
Double check the completion-gate logic: it must not allow done: true until 
AT LEAST 8 real questions have been asked AND at least 4 distinct curriculum 
days have been covered. Add a debug log line printing the running question 
count and distinct day count after every turn.

4. UI DUPLICATE COMPLETION MESSAGE
Remove the duplicate completion message shown on the frontend — keep only 
one clear completion message before the Evaluation Report renders.

5. ADD A VERIFICATION TEST SCRIPT
Write a script (scripts/test_topic_selection.py) that runs 
select_interview_topics() against at least 4 different candidates from 
data/candidates.json and prints selected days + their attempts/passed/skipped 
status, so I can manually verify the weighting logic.
```

### Fix: Feedback hallucination

```
Found a bug testing against David Miller's transcript: the feedback 
generator is hallucinating struggles that didn't happen in the actual 
interview conversation.

The final feedback claims the candidate "struggled" or "required additional 
questions to clarify" on topics where the transcript shows a single clean, 
thorough answer with no follow-up needed. It appears the feedback prompt is 
leaning on the candidate's bootcamp attempts data (from candidates.json) to 
assert interview struggles, rather than basing gaps/strengths strictly on 
what happened in the actual conversation.

Fix the feedback generation prompt so that:
- Strengths and gaps must be grounded ONLY in what the candidate actually 
  said during THIS interview (the transcript), not assumptions imported 
  from their bootcamp attempts/passed/skipped data
- The bootcamp record (attempts, skipped, passed) can be used as 
  CONTEXT/CORROBORATION — e.g. "this aligns with their bootcamp record 
  showing 5 attempts on this day" — but only as a secondary note added 
  AFTER an actual observed gap in the transcript, never as the sole basis 
  for claiming a struggle
- If a curriculum day was skipped by the selection logic and never actually 
  asked about in the interview, don't list it under "Identified Gaps" — put 
  it in a separate clearly labeled section like "Not Assessed in This 
  Interview"
- Re-read the full transcript carefully when generating feedback: if the 
  candidate gave a strong, complete, technically correct answer, it must be 
  reflected as a strength, not silently reframed as a struggle

Show me the updated feedback generation prompt, and re-run against David 
Miller's transcript so I can verify the new feedback actually matches what 
was said in the conversation, not just his bootcamp attempts data.
```

### Fix: Question calibration to candidate role

```
Currently the interviewer asks the same deep implementation-level questions 
regardless of the candidate's jobRole. This isn't right for every candidate 
— e.g. a Business Analyst with an MBA shouldn't get asked for RRF smoothing 
constants or OpenTelemetry correlation ID propagation details.

Update the system prompt so question DEPTH and FRAMING adapt to jobRole:
- Engineering roles → ask implementation-level questions: specific 
  code/architecture decisions, libraries, hyperparameters, tradeoffs at the 
  systems level
- Non-engineering roles (Business Analyst, Marketing Manager, HR Manager, 
  UX Researcher, etc.) → ask conceptual/decision-level questions: WHY a 
  particular approach was chosen, what problem it solved, what the tradeoffs 
  meant for the end user/business outcome — not HOW it was coded
- Adjust based on yearsExperience too: a 20-year Principal Architect should 
  get systems-design and tradeoff questions even if non-technical role 
  labels suggest otherwise; a fresh intern should get more foundational 
  "explain this concept" questions even in a technical role

Include 2-3 example question pairs in the system prompt showing the SAME 
curriculum day asked differently for an engineer vs a non-engineer.

Show me the updated system prompt, then re-run against a non-engineering 
candidate so I can verify the new questions are more concept/tradeoff-focused 
rather than implementation-heavy.
```

### Fix: Human-like conversational flow

```
I want the interview to feel more human and conversational, not like a list 
of disconnected questions fired one after another. Update the system prompt 
in the orchestrator to make the interviewer:

1. ACKNOWLEDGE THE PREVIOUS ANSWER BEFORE MOVING ON
Before asking the next question, briefly react to what the candidate just 
said — like a real interviewer would. Keep this to one short sentence, not 
a full paragraph.

2. USE NATURAL TRANSITIONS WHEN CHANGING TOPICS/DAYS
When moving from one curriculum day to a different one, bridge it naturally 
rather than jumping straight into the new question. Vary the transition 
phrasing each time so it doesn't sound templated.

3. USE THE CANDIDATE'S NAME OCCASIONALLY, NOT EVERY TURN
Have the interviewer address the candidate by first name maybe once every 
2-3 questions, not on every turn.

4. VARY FOLLOW-UP PHRASING
Give the model a few different natural phrasings to draw from depending on 
context, rather than always starting follow-ups the same way.

5. KEEP IT TIGHT
Total interviewer message per turn should still read naturally in 2-4 
sentences max, not a wall of text.

Update the system prompt to include explicit instructions and 2-3 example 
turns demonstrating this acknowledge → transition → ask pattern. Show me 
the updated system prompt.
```

### Test: Mixed performance verification

```
I want to verify one more edge case in the feedback generation: can it 
correctly distinguish STRONG performance on some topics from WEAK 
performance on others within the same interview, rather than making a 
blanket judgment about the whole interview?

Write a test script (scripts/test_mixed_performance.py) that runs a full 
interview session against a candidate profile but simulates MIXED answer 
quality instead of a single repeated answer:
- For questions on 2 of the selected days: send a genuinely strong, 
  detailed, technically correct answer
- For questions on the other 2 selected days: send a weak, vague, or 
  off-topic answer

After the interview completes, print the full feedback report and check:
1. Does "Key Strengths" correctly credit ONLY the topics where strong 
   answers were given?
2. Does "Identified Gaps" correctly flag ONLY the topics where weak answers 
   were given?
3. Does the executive summary accurately reflect mixed performance?
4. Does each gap/strength cite the SPECIFIC day and reasoning tied to what 
   was actually said?

Run this test and show me the full transcript and feedback report output.
```

### Fix: Next-steps scope limited to assessed topics

```
One more small refinement to the feedback prompt: the "next" (recommended 
next steps) section should stay focused on topics that were ACTUALLY 
covered in the interview and showed a gap — not generate specific advice 
about days listed under "Not Assessed." It's fine to have one generic 
closing note like "continue building on strengths and revisit any skipped 
curriculum days," but don't invent specific technical recommendations for 
days that were never discussed in this conversation.
```

---

## Phase 7 — Advanced Features

### Feature: Visible personalization reasoning

```
I want to make the topic-selection reasoning visible, so it's clear the 
interview is genuinely personalized rather than generic. Right now 
select_interview_topics() picks the days silently — I want that reasoning 
surfaced.

Changes needed:

1. UPDATE select_interview_topics()
Have the function return not just the selected days, but also a short 
reason string for EACH selected day explaining why it was chosen, based on 
the actual data. Examples:
- "Selected due to failed status (passed: false) after 3 attempts"
- "Selected due to high attempt count (5 attempts) indicating struggle"
- "Selected because this topic was skipped — checking baseline awareness"
- "Selected as a spot-check: passed on first attempt, verifying real 
  understanding vs luck"

2. SURFACE THIS AT SESSION START
When a session starts, generate a short internal "interview plan" summary. 
Add a new field to the session state and to the API response on session 
start: "interviewPlan": [ {day, title, reason}, ... ] — additive only, 
doesn't break the existing spec contract.

3. DISPLAY IN THE FRONTEND
Add a compact "Interview Focus" / "Personalization Plan" section in the UI 
listing selected days and reasons, visible before/during the interview.

4. DO NOT CHANGE ANYTHING ELSE
This is additive only — don't modify question generation, follow-up logic, 
or feedback generation.

Show me the updated topic_selector.py output for 2-3 test candidates so I 
can confirm the reasons are accurate and specific to their actual data.
```

### Feature: Rate-limit fallback

```
I need the app to gracefully handle Groq API rate limits during a live 
interview session. Add automatic fallback logic:

1. The orchestrator defaults to "llama-3.3-70b-versatile" on the first 
   attempt of every LLM call.
2. If the API returns a 429 Rate Limit Exceeded error, intercept it:
   - Log a warning to the server console
   - Dynamically switch the active model to "llama-3.1-8b-instant"
   - Reset the backoff timer and immediately retry with the fallback model
3. This should ensure the candidate's interview session does not fail or 
   show errors even if the primary model tier hits rate limits mid-
   conversation.

Verify this works by running a full test interview with the fallback model 
forced, checking that:
1. Valid JSON schema compliance is maintained
2. Follow-up and role calibration rules still work reasonably well
3. Feedback grounding still avoids hallucination

Show me the test results.
```

---

## Phase 8 — Deployment & Reliability

```
I need to prevent this app from sleeping due to inactivity on the free 
hosting tier. Add a self-ping keep-alive mechanism:

1. Confirm GET /health exists and returns a fast, trivial response.

2. ADD A BACKGROUND SELF-PING TASK
Using FastAPI's startup event, add a loop that pings the app's own /health 
endpoint every 10 minutes for as long as the app is running. Read the 
app's public URL from an environment variable SELF_URL.

Implementation notes:
- Use httpx for the async ping call
- Wrap the ping in a try/except so a failed ping never crashes the app
- Log each ping attempt at debug level
- Only run this loop if SELF_URL is set, so it doesn't ping itself during 
  local development

3. Add SELF_URL to .env.example with a comment explaining it should be set 
   to the deployed URL once known.

4. Document this in the README under deployment instructions.

Show me the updated main.py startup logic.
```

---

## Phase 9 — Documentation

```
Write a README.md for this hackathon project covering: project overview, 
key features (personalized topic selection, role/seniority-calibrated 
questioning, human-like conversational flow, genuine adaptive follow-ups, 
transcript-grounded feedback, rate-limit fallback resilience), architecture 
overview (data layer, topic selector, orchestrator, feedback generator, API 
layer, frontend), tech stack, how to run locally, sample curl requests 
showing a full interview flow, link to the live deployed demo, and a note 
on the test scripts used to validate the project.

Also create a PROMPTS.md documenting the AI-assisted development process.
```
