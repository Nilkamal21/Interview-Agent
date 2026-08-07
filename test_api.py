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
    session_id = "test-session-999"
    candidate_data = {
        "name": "Jane Doe",
        "jobRole": "AI Engineer",
        "yearsExperience": 3,
        "education": "BS Computer Science",
        "missions": []
    }
    
    print("=== TEST 1: Initialize Interview Session ===")
    payload = {
        "sessionId": session_id,
        "candidate": candidate_data
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(res, indent=2)}\n")
    assert status == 200, "Initialization failed"
    assert res["reply"] == "Welcome. Let's begin your interview.", "Wrong welcome reply"
    assert res["done"] is False, "Interview should not be done yet"
    
    print("=== TEST 2: Send Message Turn 1 ===")
    payload = {
        "sessionId": session_id,
        "message": "I'm ready to discuss my RAG application."
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(res, indent=2)}\n")
    assert status == 200, "Turn 1 failed"
    assert "RAG" in res["reply"], "Reply should ask about RAG"
    assert res["done"] is False, "Interview should not be done yet"
    
    print("=== TEST 3: Send Message Turn 2 ===")
    payload = {
        "sessionId": session_id,
        "message": "I used semantic chunking with a size of 500 characters and overlap of 50."
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(res, indent=2)}\n")
    assert status == 200, "Turn 2 failed"
    assert "retrieval quality" in res["reply"], "Reply should ask about retrieval quality"
    assert res["done"] is False, "Interview should not be done yet"
    
    print("=== TEST 4: Send Message Turn 3 (Triggers Completion) ===")
    payload = {
        "sessionId": session_id,
        "message": "I evaluated it using Ragas framework and got a faithfulness score of 0.85."
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {json.dumps(res, indent=2)}\n")
    assert status == 200, "Turn 3 failed"
    assert res["done"] is True, "Interview should be done"
    assert res["feedback"] is not None, "Feedback should be present"
    assert "summary" in res["feedback"], "Feedback summary missing"
    assert len(res["feedback"]["strengths"]) > 0, "Feedback strengths empty"
    
    print("=== TEST 5: Error - Non-existent Session ID ===")
    payload = {
        "sessionId": "non-existent-session-id",
        "message": "Hello?"
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {res}\n")
    assert status == 400, "Should return HTTP 400"
    
    print("=== TEST 6: Error - Empty Session ID ===")
    payload = {
        "sessionId": "",
        "message": "Hello?"
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {res}\n")
    assert status == 400, "Should return HTTP 400"
    
    print("=== TEST 7: Error - Missing candidate and message ===")
    payload = {
        "sessionId": session_id
    }
    status, res = make_post_request(f"{BASE_URL}/interview", payload)
    print(f"Status: {status}")
    print(f"Response: {res}\n")
    assert status == 400, "Should return HTTP 400"

    print("ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
