import json
import os
from app.services.topic_selector import select_interview_topics

def load_data():
    with open("data/candidates.json", "r") as f:
        candidates_data = json.load(f)
    with open("data/curriculum.json", "r") as f:
        curriculum_data = json.load(f)
    return candidates_data["candidates"], curriculum_data

def run_selection_test():
    candidates, curriculum = load_data()
    
    # Target candidates for verification
    target_ids = ["CAND-010", "CAND-003", "CAND-011", "CAND-002"]
    test_candidates = [c for c in candidates if c["member"]["id"] in target_ids]
    
    print("======================================================================")
    print("                TOPIC SELECTION WEIGHTING VERIFICATION                ")
    print("======================================================================\n")
    
    for candidate in test_candidates:
        member = candidate["member"]
        name = member["name"]
        id = member["id"]
        role = member["jobRole"]
        
        print(f"CANDIDATE: {name} ({id}) - {role}")
        print(f"Bootcamp Signals: {candidate.get('signals', {})}")
        
        selected_topics = select_interview_topics(candidate, curriculum)
        
        print(f"Selected {len(selected_topics)} Days for Interview:")
        for idx, item in enumerate(selected_topics, 1):
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
            print(f"     Reason: {item.get('reason')}")
        print("-" * 70)
        
        # Specific Assertions
        assert len(selected_topics) >= 4, "Must select at least 4 distinct days"
        
        # Alex Turner Verification (CAND-002)
        # Weak days are 7 (3), 10 (4), 12 (5), 13 (4), 22 (3).
        # Days 16 and 18 are passed on attempt 1.
        # Verify that 16 and 18 are NOT both selected (max 1 easy day).
        if id == "CAND-002":
            easy_count = sum(1 for item in selected_topics if item["result"].get("attempts") == 1 and item["result"].get("passed") is True)
            print(f"[VERIFY] Alex Turner: Easy days selected = {easy_count} (Expected: <= 1)")
            assert easy_count <= 1, "Alex Turner has too many easy days selected!"
            
            # Check that his selected days are indeed his struggles
            struggle_days = [7, 10, 12, 13, 22]
            selected_days = [item["day"] for item in selected_topics]
            selected_struggles = [d for d in selected_days if d in struggle_days]
            print(f"[VERIFY] Alex Turner: Struggle days selected = {selected_struggles} (Expected at least 3)")
            assert len(selected_struggles) >= 3, "Alex Turner must have at least 3 struggle days selected!"
            
        # Gerald Combs Verification (CAND-010)
        # Should prioritize his failed days (Day 8, Day 10, Day 22)
        if id == "CAND-010":
            selected_days = [item["day"] for item in selected_topics]
            print(f"[VERIFY] Gerald Combs: Selected days = {selected_days} (Should contain failures: 8, 10, 22)")
            has_failures = any(d in [8, 10, 22] for d in selected_days)
            assert has_failures, "Gerald Combs must have failed days selected!"
            
        # Emily Chen Verification (CAND-003)
        # All passes on first attempt, so it should select 4 easy days
        if id == "CAND-003":
            selected_days = [item["day"] for item in selected_topics]
            easy_count = sum(1 for item in selected_topics if item["result"].get("attempts") == 1 and item["result"].get("passed") is True)
            print(f"[VERIFY] Emily Chen: Selected days = {selected_days}, Easy days = {easy_count} (Expected: 4)")
            assert easy_count == 4, "Emily Chen should have exactly 4 easy days selected!"

    print("ALL TOPIC SELECTION PRIORITY TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_selection_test()
