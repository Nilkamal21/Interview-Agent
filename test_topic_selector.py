import json
from app.services.topic_selector import select_interview_topics

def load_data():
    with open("data/candidates.json", "r") as f:
        candidates_data = json.load(f)
    with open("data/curriculum.json", "r") as f:
        curriculum_data = json.load(f)
    return candidates_data["candidates"], curriculum_data

def run_test():
    candidates, curriculum = load_data()
    
    # Let's find specific candidates to test
    target_ids = ["CAND-001", "CAND-003", "CAND-010"]
    test_candidates = [c for c in candidates if c["member"]["id"] in target_ids]
    
    for candidate in test_candidates:
        member = candidate["member"]
        print(f"\n=========================================")
        print(f"CANDIDATE: {member['name']} ({member['id']})")
        print(f"Role: {member['jobRole']} | Experience: {member['yearsExperience']} years")
        print(f"Signals: {candidate.get('signals', {})}")
        print(f"-----------------------------------------")
        
        selected = select_interview_topics(candidate, curriculum)
        
        print(f"Selected {len(selected)} days for interview:")
        for idx, item in enumerate(selected, 1):
            res = item["result"]
            status_str = ""
            if res.get("skipped"):
                status_str = "SKIPPED"
            elif res.get("passed") is False:
                status_str = f"FAILED (attempts: {res.get('attempts')})"
            else:
                status_str = f"PASSED (attempts: {res.get('attempts')})"
                
            print(f"  {idx}. Day {item['day']}: {item['title']}")
            print(f"     Status: {status_str}")
            print(f"     Tools: {', '.join(item['tools'])}")
            print(f"     Objectives (first 2): {item['objectives'][:2]}")
        
        # Simple assertions
        assert len(selected) >= 4, "Should select at least 4 days"
        
        # For Emily (CAND-003), everything is passed on attempt 1, so verify we still selected 4 easy days
        if member["id"] == "CAND-003":
            for item in selected:
                assert item["result"].get("attempts") == 1 and item["result"].get("passed") is True, "Emily should only have easy days"
                
        # For Gerald (CAND-010), verify we caught his failures or skips
        if member["id"] == "CAND-010":
            has_fail_or_skip = any(item["result"].get("passed") is False or item["result"].get("skipped") is True for item in selected)
            assert has_fail_or_skip, "Gerald should have failed or skipped days selected"

    print("\nALL TOPIC SELECTION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_test()
