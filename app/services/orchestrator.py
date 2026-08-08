import os
import json
import re
import time
from typing import Dict, Any, List
from groq import Groq, APIError, APIConnectionError, APITimeoutError
from dotenv import load_dotenv
from app.services.topic_selector import select_interview_topics

# Load env variables from .env if present
load_dotenv()

# In-memory session store
# Key: sessionId
# Value: Dict representing session state
sessions: Dict[str, Dict[str, Any]] = {}

def get_groq_client() -> Groq:
    """
    Initializes and returns the Groq client.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing. Please configure it in your environment or .env file.")
    return Groq(api_key=api_key)

def load_curriculum() -> Dict[str, Any]:
    """
    Loads curriculum.json from the data folder.
    """
    path = os.path.join("data", "curriculum.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def clean_and_parse_json(text: str) -> Dict[str, Any]:
    """
    Cleans markdown formatting and parses JSON content from LLM response.
    """
    text = text.strip()
    # Remove markdown code block symbols if they exist
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback to finding first { and last }
        match_braces = re.search(r"(\{.*\})", text, re.DOTALL)
        if match_braces:
            try:
                return json.loads(match_braces.group(1).strip())
            except json.JSONDecodeError:
                pass
        raise ValueError(f"Failed to parse JSON response from LLM: {text}")

def get_system_prompt(candidate: Dict[str, Any]) -> str:
    """
    Defines the interviewer persona and calibrates difficulty and tone based on candidate profile.
    It also guides conversational mechanics such as short acknowledgments, name frequency, and topic transitions.
    Additionally, it calibrates question depth and framing based on technical/non-technical roles.
    """
    member = candidate.get("member", {})
    name = member.get("name", "Candidate")
    first_name = name.split()[0] if name else "Candidate"
    role = member.get("jobRole", "Software Engineer")
    exp = member.get("yearsExperience", 2)
    edu = member.get("education", "N/A")
    
    # Identify if candidate is in an engineering/technical role or non-engineering role
    eng_keywords = ["engineer", "developer", "architect", "programmer", "coder", "devops", "scripter", "specialist"]
    # Check explicitly for roles like Business Analyst or Marketing Manager which are non-eng
    is_engineer = any(kw in role.lower() for kw in eng_keywords) and "analyst" not in role.lower() and "manager" not in role.lower()
    
    # Seniority adjustments
    if exp >= 10:
        seniority_guideline = (
            "The candidate is highly experienced (Senior/Principal/Distinguished level). "
            "Focus heavily on system design, trade-offs, architecture, scalability, cost optimization, "
            "production challenges, and security. Tone should be demanding, highly professional, and direct."
        )
    elif exp >= 4:
        seniority_guideline = (
            "The candidate is mid-to-senior level. "
            "Ask about implementation tradeoffs, design decisions, practical bottlenecks, "
            "and how they debugged or handled failures."
        )
    else:
        seniority_guideline = (
            "The candidate is junior or an intern. "
            "Focus on basic definitions, explain-this-concept style checks, and how the core tools work. "
            "Be encouraging and verify they actually understand the foundation."
        )
        
    # Role-based depth calibration
    if is_engineer:
        role_guideline = (
            "Because the candidate is in an ENGINEERING/TECHNICAL role, ask implementation-level questions. "
            "Drill into specific code details, architectural decisions, libraries, APIs, hyperparameters, "
            "and technical tradeoffs at the system/code level."
        )
    else:
        role_guideline = (
            "Because the candidate is in a NON-ENGINEERING role (e.g. Analyst, Manager, Specialist, Researcher, HR), "
            "do NOT ask for low-level code, specific syntax, API hyperparameters, or code internals. "
            "Instead, ask conceptual, product, and business/decision-level questions. "
            "Focus on WHY they chose a particular approach, what business or user problem it solved, "
            "and how they evaluated success or trade-offs for the end-user/business outcome."
        )
        
    prompt = f"""You are a skeptical but fair senior technical interviewer conducting an adaptive technical interview.
Your goal is to evaluate if the candidate truly built their bootcamp projects and understands the engineering decisions behind them.

Candidate Profile:
- Name: {name}
- Job Role: {role} ({"Technical/Engineering" if is_engineer else "Non-Engineering"})
- Experience: {exp} years
- Education: {edu}

Seniority & Tone Calibration:
{seniority_guideline}

Role-based Depth Calibration:
{role_guideline}

Interviewing Style & Rules:
1. **Skeptical but Fair**: Act like a real interviewer. Be polite but analytical. If their answer is vague or lacks depth, dig deeper.
2. **No Spoon-Feeding**: Do not give away the answers. Do not write code for them.
3. **No Buzzwords**: Look for actual comprehension rather than rote-learned terms.

Conversational Dynamics & Pacing (CRITICAL FOR REALISM):
- **Acknowledge the Previous Answer**: Before asking a new question, briefly react to what the candidate just said with exactly one short sentence (e.g. "That's a solid breakdown of the hybrid approach.", "Interesting, I hadn't thought about it that way.", "Makes sense, though I want to push on that detail."). Avoid generic repetitive praise like "Great job!" or "Excellent answer!" on every turn.
- **Natural Transitions**: When switching to a new curriculum day/topic, bridge it naturally instead of jumping straight in. Use phrases like:
  - "Alright, let's shift gears a bit — I want to talk about how you approached prompt engineering."
  - "Good, that covers retrieval pretty well. Now, let's look at..."
  - "Moving forward in your roadmap, let's talk about the deployment side..."
- **Use the Candidate's Name ({first_name}) Occasionally**: Address the candidate by their first name ({first_name}) occasionally—roughly once every 2-3 questions. Never use it on consecutive turns or repetitively, which sounds robotic.
- **Vary Follow-up Phrasings**: Vary how you ask follow-up questions to drill into their claims (e.g., "What made you choose that specifically over...", "Walk me through the actual implementation of...", "Let's dig into the details here—...", "I want to push on this a bit—...").
- **Keep it Tight (2-4 sentences max)**: Do not write walls of text. Combine your acknowledgment, transition (if any), and question into a natural, spoken-feeling response of 2 to 4 sentences total.

Calibration Reference (SAME Curriculum Day Asked Differently):

Example 1: Day 8 (Vector Databases Overview)
- **Technical/Engineering Option**: "How did you configure index parameters in ChromaDB, and what tradeoffs did you observe between cosine similarity and L2 distance metrics for retrieval latency?"
- **Non-Engineering Option**: "Why did you decide to use a vector database for the chatbot instead of a standard relational database, and how did this impact the user experience when searching for healthcare plans?"

Example 2: Day 12 (Prompt Engineering Fundamentals)
- **Technical/Engineering Option**: "How did you structure your system prompts for few-shot learning, and did you implement any token optimization techniques like prompt caching?"
- **Non-Engineering Option**: "How did you design the chatbot's system prompt to ensure the answers were compliant with healthcare regulations and sounded professional to customers?"

Example 3: Day 28 (Docker & Deployment)
- **Technical/Engineering Option**: "How did you configure multi-stage builds in your Dockerfile to optimize image size, and how did you configure Kubernetes liveness and readiness probes?"
- **Non-Engineering Option**: "Why is containerizing the application with Docker useful for deploying the chatbot, and how does it help ensure the service remains reliable for users?"

Example Conversational Turns (Acknowledge → Transition → Ask Pattern):

Example 1 (Same-Topic Follow-up):
Candidate: "I used ChromaDB locally because it's lightweight and we didn't have budget for Pinecone."
Interviewer: "Choosing a local setup makes perfect sense for a hackathon budget. What made you choose ChromaDB specifically over other local vector stores like FAISS, and did you run into any concurrency issues during testing?"

Example 2 (Topic Switch with Name):
Candidate: "I evaluated it using Ragas framework and got a faithfulness score of 0.85, which showed the context was accurate."
Interviewer: "A faithfulness score of 0.85 is a respectable baseline for checking retrieval grounding. Now, {first_name}, let's shift gears and look at the deployment phase. How did you containerize your backend using Docker, and did you run into any permission issues when creating the non-root user?"

Example 3 (Tough Follow-up on Senior Candidate):
Candidate: "We built a multi-agent system where one agent wrote claims and the other did validation."
Interviewer: "Specializing the validator role is a standard pattern to prevent single-agent hallucinations. I want to push on this a bit—how did you manage state handoff and loop prevention if the validator kept rejecting the claims agent's output?"
"""
    return prompt

def call_llm_with_retry(messages: List[Dict[str, Any]], response_format: Dict[str, Any] = None, max_retries: int = 3, timeout: float = 15.0) -> str:
    """
    Executes a Groq LLM completion call with timeout and exponential backoff retry handling.
    """
    client = get_groq_client()
    backoff = 1.0
    
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                response_format=response_format,
                timeout=timeout
            )
            return response.choices[0].message.content
        except (APIConnectionError, APITimeoutError) as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"Failed to communicate with the AI model after {max_retries} attempts: {str(e)}")
            time.sleep(backoff)
            backoff *= 2.0
        except APIError as e:
            if e.status_code == 429:
                if attempt == max_retries - 1:
                    raise RuntimeError("Rate limit exceeded for the AI model. Please wait a moment and try again.")
                time.sleep(backoff + 2.0)
                backoff *= 2.0
            else:
                raise RuntimeError(f"AI model API error (status {e.status_code}): {e.message}")
        except Exception as e:
            raise RuntimeError(f"An unexpected error occurred while communicating with the AI model: {str(e)}")
            
    raise RuntimeError("AI model communication failed.")

def generate_first_question(session: Dict[str, Any]) -> str:
    """
    Generates the initial starting question for the first selected topic.
    """
    topic = session["selected_topics"][0]
    
    prompt = f"""We are starting the interview. The first topic is:
Day {topic['day']}: {topic['title']}
Tools used: {', '.join(topic['tools'])}
Learning objectives: {', '.join(topic['objectives'])}
Candidate's bootcamp result for this day: {topic['result']}

Please ask a single starting question to test their understanding of this day's work.
- If they failed or skipped, ask about the core concepts or challenges.
- If they passed on attempt 1, ask a challenging question about design decisions, trade-offs, or implementation.
- Do not mention attempts, scores, or "bootcamp results". Make it natural.

You must return a JSON response with the following format:
{{
  "question": "Your starting question here."
}}"""

    messages = [
        {"role": "system", "content": session["system_prompt"]},
        {"role": "user", "content": prompt}
    ]
    
    content = call_llm_with_retry(messages, response_format={"type": "json_object"})
    res_data = clean_and_parse_json(content)
    return res_data["question"]

def generate_feedback(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the entire chat history and generates structured feedback.
    Gaps and strengths are grounded strictly in the transcript, using bootcamp history only as secondary corroboration.
    """
    client = get_groq_client()
    candidate = session["candidate"]
    evaluations = session["evaluations"]
    
    # Format a summary of the turn evaluations
    evals_summary = []
    discussed_days = sorted(list(set(ev["day"] for ev in evaluations)))
    discussed_days_str = ", ".join(f"Day {d}" for d in discussed_days)
    
    for ev in evaluations:
        evals_summary.append(f"""Topic Day {ev['day']}:
- Question: {ev['question']}
- Candidate Answer: {ev['answer']}
- Evaluation: {ev['evaluation']}
""")
        
    # Format candidate's bootcamp results for correlation check in gaps
    bootcamp_struggles = []
    for m in candidate.get("missions", []):
        day_num = m.get("day")
        if m.get("skipped"):
            bootcamp_struggles.append(f"Day {day_num} was SKIPPED")
        elif m.get("passed") is False:
            bootcamp_struggles.append(f"Day {day_num} was FAILED with {m.get('attempts', 0)} attempts")
        elif m.get("attempts", 1) >= 3:
            bootcamp_struggles.append(f"Day {day_num} was passed but struggled (took {m.get('attempts')} attempts)")
            
    bootcamp_summary = ", ".join(bootcamp_struggles) if bootcamp_struggles else "No major struggles or skips recorded in bootcamp."

    prompt = f"""You are the senior technical interviewer. The interview is now complete.
Please review the candidate's profile, their bootcamp record, and the evaluations of their answers to generate the final structured feedback.

Candidate Profile:
- Name: {candidate['member']['name']}
- Job Role: {candidate['member']['jobRole']}
- Experience: {candidate['member']['yearsExperience']} years

Candidate's Bootcamp Struggles/Skips:
- {bootcamp_summary}

Interview Evaluations (by Day):
{chr(10).join(evals_summary)}

Please generate feedback matching these specifications:
1. **summary**: Exactly 2-3 sentences. It MUST explicitly reference the specific curriculum days discussed: {discussed_days_str}. It should summarize their performance and communication style.
2. **strengths**: A list of 2-3 concrete points. Each point MUST be grounded ONLY in the candidate's actual answers in the interview. Do NOT assume strengths.
3. **gaps**: A list of 2-3 concrete weak areas. Each gap MUST be strictly grounded in what the candidate actually said (or failed to say) in this interview. Do NOT claim the candidate struggled on a topic based solely on their bootcamp record. If they answered correctly, they do not have a gap. You may use their bootcamp struggles (such as skipped or high attempts days) ONLY as secondary corroboration AFTER an actual gap is demonstrated in their answer (e.g. 'This gap aligns with their bootcamp record of 5 attempts on Day 12').
4. **next**: A list of 2-3 actionable, highly specific recommendations to help them improve. These recommendations MUST be focused ONLY on the topics/days that were ACTUALLY discussed in this interview ({discussed_days_str}) and demonstrated a gap. Do NOT invent specific technical recommendations or suggest next steps for days that were not discussed in this conversation (i.e. those in the 'Not Assessed' category). It is acceptable to include a generic closing recommendation like 'continue building on strengths and review skipped curriculum days', but any detailed technical guidance must be grounded in discussed topics only.

You must return a JSON response with the following format:
{{
  "summary": "...",
  "strengths": ["...", "..."],
  "gaps": ["...", "..."],
  "next": ["...", "..."]
}}"""

    messages = [
        {"role": "system", "content": session["system_prompt"]},
        {"role": "user", "content": prompt}
    ]
    
    content = call_llm_with_retry(messages, response_format={"type": "json_object"})
    feedback = clean_and_parse_json(content)
    
    # Calculate notAssessed days programmatically in Python for 100% accuracy
    try:
        curriculum = load_curriculum()
        curriculum_map = {d["day"]: d for d in curriculum.get("days", [])}
        
        candidate_days = set(m.get("day") for m in candidate.get("missions", []))
        discussed_days_set = set(ev["day"] for ev in evaluations)
        unassessed_days = sorted(list(candidate_days - discussed_days_set))
        
        unassessed_list = []
        for d in unassessed_days:
            if d in curriculum_map:
                unassessed_list.append(f"Day {d}: {curriculum_map[d]['title']}")
        feedback["notAssessed"] = unassessed_list
    except Exception:
        feedback["notAssessed"] = []
        
    return feedback

def init_session(session_id: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initializes a new interview session.
    """
    curriculum = load_curriculum()
    selected_topics = select_interview_topics(candidate, curriculum)
    
    interview_plan = [
        {
            "day": t["day"],
            "title": t["title"],
            "reason": t.get("reason", "")
        }
        for t in selected_topics
    ]
    
    session = {
        "candidate": candidate,
        "selected_topics": selected_topics,
        "interview_plan": interview_plan,
        "current_topic_index": 0,
        "question_count": 0,
        "questions_by_day": {},  # Maps day_num -> count
        "history": [],  # Message history for uvicorn/LLM context
        "evaluations": [],  # Detailed turn-by-turn evaluations
        "done": False,
        "system_prompt": get_system_prompt(candidate)
    }
    
    sessions[session_id] = session
    
    # Ask the very first question on session start immediately
    question = generate_first_question(session)
    session["history"].append({"role": "assistant", "content": question})
    session["question_count"] = 1
    
    first_topic = selected_topics[0]
    session["questions_by_day"][first_topic["day"]] = 1
    
    # Print a debug log
    print(f"[DEBUG] Session {session_id} initialized. Question 1 asked on Day {first_topic['day']}. Total questions: 1, Distinct days: 1")
    
    return {
        "reply": question,
        "done": False,
        "interviewPlan": interview_plan
    }

def process_turn(session_id: str, message: str) -> Dict[str, Any]:
    """
    Processes a conversation turn. Evaluates previous answer, decides flow path, and generates next question or final feedback.
    """
    if session_id not in sessions:
        raise ValueError(f"Session with ID '{session_id}' does not exist or has not been initialized.")
        
    session = sessions[session_id]
    
    if session["done"]:
        return {
            "reply": "Interview completed.",
            "done": True,
            "feedback": session.get("feedback")
        }
        
    # Append the candidate's response to history
    session["history"].append({"role": "user", "content": message})
    
    question_count = session["question_count"]
    
    # Calculate distinct days covered so far (any day with a question count > 0)
    distinct_days_covered = len([day for day, count in session["questions_by_day"].items() if count > 0])
    
    # Print a debug log showing count information as requested
    print(f"[DEBUG] Session {session_id} - Turn processed. Total questions asked so far: {question_count}, Distinct days covered: {distinct_days_covered}")
    
    # We only complete the interview if we've asked at least 8 questions AND covered at least 4 distinct days
    if question_count >= 8 and distinct_days_covered >= 4:
        # Complete the interview: evaluate final answer and compile feedback
        current_topic_index = session["current_topic_index"]
        current_topic = session["selected_topics"][current_topic_index]
        
        client = get_groq_client()
        
        eval_prompt = f"""Evaluate the candidate's final response for correctness and completeness relative to the topic:
Day {current_topic['day']}: {current_topic['title']}
Tools: {', '.join(current_topic['tools'])}
Objectives: {', '.join(current_topic['objectives'])}

You must return a JSON response with the following format:
{{
  "evaluation": "Your brief evaluation of the candidate's final response."
}}"""

        eval_messages = [
            {"role": "system", "content": session["system_prompt"]}
        ]
        eval_messages.extend(session["history"])
        eval_messages.append({"role": "user", "content": eval_prompt})
        
        eval_content = call_llm_with_retry(eval_messages, response_format={"type": "json_object"})
        eval_data = clean_and_parse_json(eval_content)
        
        prev_question = session["history"][-2]["content"] if len(session["history"]) >= 2 else ""
        session["evaluations"].append({
            "day": current_topic["day"],
            "question": prev_question,
            "answer": message,
            "evaluation": eval_data.get("evaluation", "")
        })
        
        # Generate the structured feedback report
        feedback = generate_feedback(session)
        session["feedback"] = feedback
        session["done"] = True
        
        return {
            "reply": "Interview completed.",
            "done": True,
            "feedback": feedback
        }
        
    else:
        # Generate the next question
        current_topic_index = session["current_topic_index"]
        selected_topics = session["selected_topics"]
        current_topic = selected_topics[current_topic_index]
        
        can_move_on = (current_topic_index < len(selected_topics) - 1)
        questions_asked_on_day = session["questions_by_day"].get(current_topic["day"], 0)
        
        # Enforce state machine rules:
        # - Force move on if we've asked 3 questions on the current topic.
        # - Force follow-up if we are at the last topic and need more questions to reach 8.
        force_move_on = can_move_on and (questions_asked_on_day >= 3)
        force_followup = (current_topic_index == len(selected_topics) - 1) and (question_count < 8)
        
        decision_guideline = ""
        if force_move_on:
            decision_guideline = "You MUST set 'decision' to 'MOVE_ON' because we have asked enough questions on this topic."
        elif force_followup:
            decision_guideline = "You MUST set 'decision' to 'FOLLOW_UP' because we are at the end of the topics and need to ask more questions."
        else:
            decision_guideline = "You can decide to set 'decision' to either 'FOLLOW_UP' (to ask a deeper question on this topic) or 'MOVE_ON' (to move to the next topic)."
            
        next_topic = selected_topics[current_topic_index + 1] if can_move_on else None
        next_topic_details = ""
        if next_topic:
            next_topic_details = f"""If moving on, the next topic is:
Day {next_topic['day']}: {next_topic['title']}
Tools: {', '.join(next_topic['tools'])}
Objectives: {', '.join(next_topic['objectives'])}
Result: {next_topic['result']}"""

        client = get_groq_client()
        
        prompt = f"""The candidate has responded to the last question.
Current topic: Day {current_topic['day']}: {current_topic['title']}
Tools: {', '.join(current_topic['tools'])}
Objectives: {', '.join(current_topic['objectives'])}
Result: {current_topic['result']}

Questions asked on this day so far: {questions_asked_on_day}
Total questions asked in the interview: {question_count}

{decision_guideline}

{next_topic_details}

Please perform the following tasks:
1. Evaluate the candidate's last answer for correctness and completeness relative to the current topic's tools/objectives.
2. Output a decision: "FOLLOW_UP" if you are continuing on the same topic, or "MOVE_ON" if you are moving to the next topic.
3. Generate the next question:
   - If "FOLLOW_UP": ask a specific follow-up question digging deeper into their response.
   - If "MOVE_ON": transition to the next topic and ask an initial question about it.

You must return a JSON response with the following format:
{{
  "evaluation": "Your brief evaluation of the candidate's last response.",
  "decision": "FOLLOW_UP" or "MOVE_ON",
  "question": "The text of the next question to ask the candidate."
}}"""

        messages = [
            {"role": "system", "content": session["system_prompt"]}
        ]
        messages.extend(session["history"])
        messages.append({"role": "user", "content": prompt})
        
        content = call_llm_with_retry(messages, response_format={"type": "json_object"})
        res_data = clean_and_parse_json(content)
        
        evaluation = res_data.get("evaluation", "")
        decision = res_data.get("decision", "FOLLOW_UP")
        next_question = res_data.get("question", "Could you explain more?")
        
        # Save evaluation details
        prev_question = session["history"][-2]["content"] if len(session["history"]) >= 2 else ""
        session["evaluations"].append({
            "day": current_topic["day"],
            "question": prev_question,
            "answer": message,
            "evaluation": evaluation
        })
        
        # Update topic indices and counters
        if decision == "MOVE_ON" and can_move_on:
            session["current_topic_index"] += 1
            new_topic = selected_topics[session["current_topic_index"]]
            session["questions_by_day"][new_topic["day"]] = 1
        else:
            session["questions_by_day"][current_topic["day"]] = questions_asked_on_day + 1
            
        session["question_count"] += 1
        session["history"].append({"role": "assistant", "content": next_question})
        
        return {
            "reply": next_question,
            "done": False
        }

