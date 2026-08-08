import os
import json
import re
from typing import Dict, Any, List
from groq import Groq
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
    """
    member = candidate.get("member", {})
    name = member.get("name", "Candidate")
    role = member.get("jobRole", "Software Engineer")
    exp = member.get("yearsExperience", 2)
    edu = member.get("education", "N/A")
    
    # Calibrate tone and depth based on years of experience
    if exp >= 10:
        seniority_guideline = (
            "The candidate is highly experienced (Senior/Principal/Distinguished level). "
            "You should push them hard on trade-offs, architecture, edge cases, scalability, "
            "production challenges, and security. Do not accept high-level buzzwords; demand deep technical justifications. "
            "Tone should be demanding, highly professional, and direct."
        )
    elif exp >= 4:
        seniority_guideline = (
            "The candidate is mid-to-senior level. "
            "Ask about implementation details, design decisions, practical trade-offs, "
            "and how they handled failures or debugging. Keep the questions professional and moderately challenging."
        )
    else:
        seniority_guideline = (
            "The candidate is junior or an intern. "
            "Focus on foundational understanding of the concepts, clear explanation of how the tools work, "
            "and basic implementation. Be encouraging but ensure they actually understand what they built and didn't "
            "just copy-paste code."
        )
        
    prompt = f"""You are a skeptical but fair senior technical interviewer conducting an adaptive technical interview.
Your goal is to evaluate if the candidate truly built their bootcamp projects and understands the engineering decisions behind them.

Candidate Profile:
- Name: {name}
- Job Role: {role}
- Experience: {exp} years
- Education: {edu}

Seniority & Tone Calibration:
{seniority_guideline}

Interviewing Style & Rules:
1. **Skeptical but Fair**: Act like a real interviewer. Be polite but analytical. If their answer is vague or lacks depth, dig deeper.
2. **Context-Aware**: Follow up on their specific claims. If they mention using a tool, ask how or why they set it up that way.
3. **Calibrated Difficulty**: Adapt your vocabulary and depth to their years of experience and job role.
4. **No Spoon-Feeding**: Do not give away the answers. Do not write code for them.
5. **No Buzzwords**: Look for actual comprehension rather than rote-learned terms.
"""
    return prompt

def generate_first_question(session: Dict[str, Any]) -> str:
    """
    Generates the initial starting question for the first selected topic.
    """
    topic = session["selected_topics"][0]
    client = get_groq_client()
    
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

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": session["system_prompt"]},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    
    res_data = clean_and_parse_json(response.choices[0].message.content)
    return res_data["question"]

def generate_feedback(session: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the entire chat history and generates structured feedback.
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
2. **strengths**: A list of 2-3 concrete points. Each point MUST be tied to a specific answer and curriculum day. Avoid generic praise like "good communicator" or "strong skills."
3. **gaps**: A list of 2-3 concrete weak areas. Each point MUST be tied to a specific curriculum day and answer. Specifically highlight any correlation where the candidate's bootcamp mission record (e.g. skipped, high attempts, or failed days) matched their actual struggles or lack of knowledge shown in the interview.
4. **next**: A list of 2-3 actionable, highly specific recommendations to help them improve (e.g., "revisit Day 8 vector database indexing strategies" or "practice building ReAct tool loops on Day 21").

You must return a JSON response with the following format:
{{
  "summary": "...",
  "strengths": ["...", "..."],
  "gaps": ["...", "..."],
  "next": ["...", "..."]
}}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": session["system_prompt"]},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        response_format={"type": "json_object"}
    )
    
    return clean_and_parse_json(response.choices[0].message.content)

def init_session(session_id: str, candidate: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initializes a new interview session.
    """
    curriculum = load_curriculum()
    selected_topics = select_interview_topics(candidate, curriculum)
    
    session = {
        "candidate": candidate,
        "selected_topics": selected_topics,
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
        "done": False
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
        
        eval_response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=eval_messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        eval_data = clean_and_parse_json(eval_response.choices[0].message.content)
        
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
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        res_data = clean_and_parse_json(response.choices[0].message.content)
        
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

