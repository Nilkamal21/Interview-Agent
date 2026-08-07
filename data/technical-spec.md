# Technical Specification

This document defines the API contract and submission requirements for the AI Interview Agent.

---

# HTTP Endpoint

Your agent must expose a single endpoint:

```
POST /api/interview
```

No authentication is required.

The endpoint must maintain interview state using the provided `sessionId`.

---

# Interview Flow

## 1. Start Interview

The first request initializes a new interview session.

```json
POST /api/interview

{
  "sessionId": "abc-123",
  "candidate": { ...candidate.json }
}
```

### Expected Response

```json
{
  "reply": "Welcome. Let's begin your interview.",
  "done": false
}
```

---

## 2. Conversation Turn

Every subsequent request contains the candidate's latest response.

```json
{
  "sessionId": "abc-123",
  "message": "..."
}
```

### Expected Response

```json
{
  "reply": "...",
  "done": false
}
```

This continues until the interview is complete.

---

## 3. End Interview

When the interview is complete, return:

```json
{
  "reply": "Interview completed.",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": [],
    "gaps": [],
    "next": []
  }
}
```

---

# Feedback Format

The final response must include:

| Field | Type |
|--------|------|
| summary | string |
| strengths | string[] |
| gaps | string[] |
| next | string[] |

Each array should contain concise, actionable points.

---

# Notes

- Use the supplied `sessionId` throughout the interview.
- The interview should remain conversational across multiple requests.
- The candidate object will follow the provided `candidate.json` schema.
- Teams are free to choose any frontend, backend, LLM, framework, or architecture.
