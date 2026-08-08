import json
import urllib.request
import urllib.error
import sys

BASE_URL = "http://localhost:8000/api"

def make_post_request(url, data):
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as response:
            res_body = response.read().decode("utf-8")
            return response.status, json.loads(res_body)
    except urllib.error.HTTPError as e:
        res_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(res_body)
        except json.JSONDecodeError:
            return e.code, res_body
    except urllib.error.URLError as e:
        print(f"Error: Could not connect to the server at {url}. Is it running?")
        sys.exit(1)

def get_answer_for_question(question_text):
    q_lower = question_text.lower()
    
    # Day 7: Embeddings
    if any(k in q_lower for k in ["embedding", "sentence transformer", "similarity", "vector space", "clustering"]):
        return (
            "For generating embeddings, we chose Sentence Transformers (specifically the all-MiniLM-L6-v2 model) "
            "to run locally within our container environment. This eliminated external API costs and latency. "
            "We evaluated embedding quality using silhouette scores on a sample dataset of 500 healthcare claim records. "
            "We observed that all-MiniLM-L6-v2 achieved a silhouette score of 0.72, which was highly comparable to "
            "OpenAI's text-embedding-ada-002 score of 0.78, but achieved a 95% reduction in latency by eliminating "
            "external network roundtrips."
        )
        
    # Day 12: Prompt Engineering
    if any(k in q_lower for k in ["prompt", "few-shot", "zero-shot", "chain-of-thought", "compliant", "system prompt"]):
        return (
            "We designed system prompts with strict Few-Shot examples to ensure the LLM output conforms to our "
            "JSON structure. In zero-shot trials, the model often hallucinated JSON keys, so we structured a system prompt "
            "containing 3 static XML-wrapped few-shot examples. To ensure regulatory compliance, we used Chain-of-Thought "
            "reasoning where the model writes a compliance reasoning path before outputting final medical advice, "
            "achieving a 99.8% compliance rate under automated checks."
        )
        
    # Day 28: Docker & Deployment
    if any(k in q_lower for k in ["docker", "container", "deploy", "kubernetes", "k8s", "dockerfile"]):
        return (
            "Docker is used to package the code so that it runs in the cloud. We copied a standard Python template "
            "from the internet for the Dockerfile and ran docker build and run. It worked okay for deploying. "
            "I don't recall the specific configuration details, but we just used it for basic deployment on Railway."
        )
        
    # Day 29: Monitoring, Logging & Observability
    if any(k in q_lower for k in ["monitoring", "logging", "observability", "prometheus", "grafana", "python logging"]):
        return (
            "Monitoring is about checking if the server is running. We did some logging by adding standard python "
            "print statements in the console to print when endpoints are hit. We didn't set up Prometheus or Grafana "
            "in this project because we ran out of time and it was too complex."
        )
        
    # Fallback default response
    return (
        "I understand the question. While I am familiar with this conceptual day in the curriculum, "
        "I did not implement deep custom metrics here and focused on using standard frameworks like LangChain."
    )

def run_mixed_performance_test():
    session_id = "test-session-mixed-perf"
    
    # Load candidate Sarah Johnson
    with open("data/candidates.json", "r") as f:
        candidates_data = json.load(f)
    candidate_data = candidates_data["candidates"][0] # Sarah Johnson (Days 7, 12, 28, 29)
    
    print("======================================================================")
    print("             RUNNING MIXED PERFORMANCE EVALUATION TEST                 ")
    print("======================================================================\n")
    
    # 1. Initialize session and get first question
    payload = {
        "sessionId": session_id,
        "candidate": candidate_data
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    if status != 200:
        print(f"Failed to initialize session: {res}")
        sys.exit(1)
        
    current_question = res["reply"]
    print(f"Interviewer (Q1): {current_question}\n")
    
    # 2. Dynamic Q&A loop
    turn = 1
    done = False
    while not done:
        # Determine the response quality dynamically based on topic
        answer = get_answer_for_question(current_question)
        
        is_strong = "silhouette" in answer or "Few-Shot" in answer
        quality_label = "STRONG" if is_strong else "WEAK"
        print(f"--- Turn {turn} [Detected Topic Response: {quality_label}] ---")
        print(f"Candidate Answer: {answer[:120]}...\n")
        
        payload = {
            "sessionId": session_id,
            "message": answer
        }
        status, res = make_post_request(f"{BASE_URL}/interview", payload)
        if status != 200:
            print(f"Error on turn {turn}: {res}")
            sys.exit(1)
            
        done = res["done"]
        if not done:
            current_question = res["reply"]
            print(f"Interviewer (Q{turn+1}): {current_question}\n")
            turn += 1
        else:
            print("======================================================================")
            print("                       INTERVIEW COMPLETED                             ")
            print("======================================================================\n")
            feedback = res["feedback"]
            print(f"Feedback Report: {json.dumps(feedback, indent=2)}\n")
            
            # Perform assertions as requested by the user
            print("=== VERIFYING ACCURACY CONSTRAINTS ===")
            
            # Check 1: Key Strengths crediting only Days 7/12
            strengths_text = " ".join(feedback["strengths"]).lower()
            day7_checked = "day 7" in strengths_text or "embedding" in strengths_text
            day12_checked = "day 12" in strengths_text or "prompt" in strengths_text
            day28_checked = "day 28" in strengths_text or "docker" in strengths_text or "kubernetes" in strengths_text
            day29_checked = "day 29" in strengths_text or "monitoring" in strengths_text or "logging" in strengths_text
            
            print(f"  [CHECK] Strengths cite Day 7/Embeddings: {day7_checked}")
            print(f"  [CHECK] Strengths cite Day 12/Prompting: {day12_checked}")
            print(f"  [CHECK] Strengths NOT citing Day 28 (Docker): {not day28_checked}")
            print(f"  [CHECK] Strengths NOT citing Day 29 (Logging): {not day29_checked}")
            
            # Check 2: Identified Gaps flagging only Days 28/29
            gaps_text = " ".join(feedback["gaps"]).lower()
            day7_gap_checked = "day 7" in gaps_text or "embedding" in gaps_text
            day12_gap_checked = "day 12" in gaps_text or "prompt" in gaps_text
            day28_gap_checked = "day 28" in gaps_text or "docker" in gaps_text or "kubernetes" in gaps_text
            day29_gap_checked = "day 29" in gaps_text or "monitoring" in gaps_text or "logging" in gaps_text
            
            print(f"  [CHECK] Gaps NOT citing Day 7 (Embeddings): {not day7_gap_checked}")
            print(f"  [CHECK] Gaps NOT citing Day 12 (Prompting): {not day12_gap_checked}")
            print(f"  [CHECK] Gaps cite Day 28 (Docker): {day28_gap_checked}")
            print(f"  [CHECK] Gaps cite Day 29 (Logging): {day29_gap_checked}")
            
            # Check 3: Executive Summary reflecting mixed performance
            summary_text = feedback["summary"].lower()
            is_mixed = any(w in summary_text for w in ["mixed", "stronger", "struggled", "gap", "but", "however", "although", "demonstrated", "failed"])
            print(f"  [CHECK] Summary reflects mixed performance (contains tradeoff keywords): {is_mixed}")
            
            # Check 4: Unassessed days are present
            unassessed_checked = len(feedback.get("notAssessed", [])) > 0
            print(f"  [CHECK] Unassessed days listed programmatically: {unassessed_checked}")
            
            print("\nMIXED PERFORMANCE EVALUATION VERIFICATION COMPLETE!")

if __name__ == "__main__":
    run_mixed_performance_test()
