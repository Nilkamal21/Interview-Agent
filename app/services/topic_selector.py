from typing import Dict, Any, List

def select_interview_topics(candidate: Dict[str, Any], curriculum: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Joins candidate missions against curriculum days and selects at least 4 distinct days
    to interview them on, using the following priority rules:
    1. Prioritizes days where the candidate struggled (attempts >= 3) or failed (passed is False).
    2. Includes lighter-touch awareness questions for skipped days.
    3. Includes a couple of "too easy" days (passed on attempt 1) to verify real understanding vs luck.
    
    Returns a list of selected days with curriculum info joined.
    """
    # 1. Map curriculum days by day number for fast lookup
    curriculum_days = {d["day"]: d for d in curriculum.get("days", [])}
    
    # 2. Join candidate missions with curriculum details
    joined_missions = []
    for mission in candidate.get("missions", []):
        day_num = mission.get("day")
        if day_num in curriculum_days:
            curr_day = curriculum_days[day_num]
            joined_missions.append({
                "day": day_num,
                "title": curr_day.get("title"),
                "type": curr_day.get("type"),
                "tools": curr_day.get("tools", []),
                "objectives": curr_day.get("objectives", []),
                "result": mission
            })
            
    # 3. Categorize joined missions
    struggled_failed = []
    skipped = []
    easy = []
    medium = []
    
    for jm in joined_missions:
        result = jm["result"]
        if result.get("skipped") is True:
            skipped.append(jm)
        elif result.get("passed") is False:
            struggled_failed.append(jm)
        elif result.get("passed") is True:
            attempts = result.get("attempts", 1)
            if attempts >= 3:
                struggled_failed.append(jm)
            elif attempts == 2:
                medium.append(jm)
            else:
                easy.append(jm)

    # Sort struggled/failed by passed == False first, then by attempts descending
    struggled_failed.sort(key=lambda x: (x["result"].get("passed") is True, -x["result"].get("attempts", 0)))
    
    selected_topics = []
    
    # Selection algorithm:
    # Target: 4 topics
    # - Take up to 2 from struggled_failed
    # - Take up to 1 from skipped
    # - Take up to 1-2 from easy
    # - Fill from medium or remaining if we don't have 4 topics yet
    
    # Add struggled/failed first (up to 2)
    selected_topics.extend(struggled_failed[:2])
    
    # Add skipped (up to 1)
    selected_topics.extend(skipped[:1])
    
    # Add easy (up to 2)
    selected_topics.extend(easy[:2])
    
    # If we need more (e.g. if struggled/failed or skipped was empty)
    # Add from medium
    if len(selected_topics) < 4:
        for item in medium:
            if item not in selected_topics:
                selected_topics.append(item)
                if len(selected_topics) >= 4:
                    break
                    
    # If still not enough (e.g. candidate has very few missions recorded)
    # Add remaining from struggled_failed
    if len(selected_topics) < 4:
        for item in struggled_failed[2:]:
            if item not in selected_topics:
                selected_topics.append(item)
                if len(selected_topics) >= 4:
                    break
                    
    # Add remaining from skipped
    if len(selected_topics) < 4:
        for item in skipped[1:]:
            if item not in selected_topics:
                selected_topics.append(item)
                if len(selected_topics) >= 4:
                    break

    # Add remaining from easy
    if len(selected_topics) < 4:
        for item in easy[2:]:
            if item not in selected_topics:
                selected_topics.append(item)
                if len(selected_topics) >= 4:
                    break
                    
    # Sort selected topics by day number so the interview progresses chronologically
    selected_topics.sort(key=lambda x: x["day"])
    
    return selected_topics
