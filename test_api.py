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

def run_tests():
    session_id = "test-session-direct-q1"
    
    # Load candidate
    with open("data/candidates.json", "r") as f:
        candidates_data = json.load(f)
    candidate_data = candidates_data["candidates"][0] # Sarah Johnson
    
    print("=== TEST 1: Initialize Interview Session (Expects Question 1) ===")
    payload = {
        "sessionId": session_id,
        "candidate": candidate_data
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    if status != 200:
        print(f"Error Response: {res}")
        sys.exit(1)
    
    print(f"Interviewer (Q1): {res['reply']}")
    print(f"Done: {res['done']}\n")
    
    assert status == 200, "Initialization failed"
    assert res["done"] is False, "Interview should not be done on init"
    assert len(res["reply"]) > 10, "Should return a real starting question"
    
    # We will answer 8 questions in total
    dummy_answer = (
        "I implemented that by setting up a LangChain agent using the ReAct framework. "
        "I exposed a vector search tool connected to ChromaDB and a structured database lookup tool. "
        "The model decides to query the vector database for unstructured claims and handles structured "
        "plan details via SQL lookup, returning the formatted result to the user."
    )
    
    # Loop dynamically until the interview is complete
    turn = 1
    done = False
    while not done:
        print(f"=== TEST 2: Conversation Turn {turn} (Sending Answer {turn}) ===")
        payload = {
            "sessionId": session_id,
            "message": f"Regarding your question, here is my response: {dummy_answer}"
        }
        status, res = make_post_request(f"{BASE_URL}/interview", payload)
        print(f"Status: {status}")
        if status != 200:
            print(f"Error Response: {res}")
            sys.exit(1)
            
        done = res["done"]
        if not done:
            print(f"Interviewer (Q{turn+1}): {res['reply']}")
            print(f"Done: {res['done']}\n")
            turn += 1
        else:
            print(f"Response: {json.dumps(res, indent=2)}\n")
            assert turn >= 8, f"Interview completed too early after only {turn} turns"
            assert "feedback" in res, "Feedback payload missing"
            feedback = res["feedback"]
            assert "summary" in feedback, "Feedback summary missing"
            assert "strengths" in feedback and len(feedback["strengths"]) > 0, "Feedback strengths missing or empty"
            assert "gaps" in feedback and len(feedback["gaps"]) > 0, "Feedback gaps missing or empty"
            assert "next" in feedback and len(feedback["next"]) > 0, "Feedback next steps missing or empty"
            
    # Verify Error Handling remains intact
    print("=== TEST 3: Error - Non-existent Session ID ===")
    payload = {
        "sessionId": "non-existent-session-id",
        "message": "Hello?"
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {res}\n")
    assert status == 400, "Should return HTTP 400"
    
    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
