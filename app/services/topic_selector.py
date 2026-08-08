from typing import Dict, Any, List

def select_interview_topics(candidate: Dict[str, Any], curriculum: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Selects exactly 4 distinct curriculum days to interview the candidate on.
    Prioritizes:
      1. Failed missions (passed: false)
      2. High attempts (3+) even if eventually passed
      3. Skipped missions (light-touch awareness questions)
      4. Moderate struggle (attempts: 2)
      5. Passed on first attempt (easy days - limit to 1 max as a spot check if struggles exist)
    """
    curriculum_map = {d["day"]: d for d in curriculum.get("days", [])}
    
    # Classify joined days
    failed = []
    high_attempts = []
    skipped = []
    medium = []
    easy = []
    
    for mission in candidate.get("missions", []):
        day_num = mission.get("day")
        if day_num in curriculum_map:
            curr_day = curriculum_map[day_num]
            joined = {
                "day": day_num,
                "title": curr_day.get("title"),
                "type": curr_day.get("type"),
                "tools": curr_day.get("tools", []),
                "objectives": curr_day.get("objectives", []),
                "result": mission
            }
            
            if mission.get("skipped") is True:
                skipped.append(joined)
            elif mission.get("passed") is False:
                failed.append(joined)
            else:
                attempts = mission.get("attempts", 1)
                if attempts >= 3:
                    high_attempts.append(joined)
                elif attempts == 2:
                    medium.append(joined)
                else:
                    easy.append(joined)
                    
    # Sort struggled/failed by attempts descending to prioritize harder ones first
    failed.sort(key=lambda x: x["result"].get("attempts", 0), reverse=True)
    high_attempts.sort(key=lambda x: x["result"].get("attempts", 0), reverse=True)
    
    # Selection pools in priority order
    selected_struggles = []
    selected_struggles.extend(failed)
    selected_struggles.extend(high_attempts)
    selected_struggles.extend(skipped)
    selected_struggles.extend(medium)
    
    selected = []
    
    # 1. If we have at least 3 struggle/skipped days and at least 1 easy day:
    #    Take exactly 3 struggles/skips + exactly 1 easy day as a verify-understanding spot check.
    if len(selected_struggles) >= 3 and len(easy) >= 1:
        selected.extend(selected_struggles[:3])
        selected.append(easy[0])
    # 2. If we have no easy days but have at least 4 struggle/skipped days:
    #    Take exactly 4 struggles/skips.
    elif len(selected_struggles) >= 4:
        selected.extend(selected_struggles[:4])
    # 3. Otherwise: merge all struggles and fill the remaining slots with easy days.
    else:
        selected.extend(selected_struggles)
        for item in easy:
            if len(selected) < 4:
                selected.append(item)
            else:
                break
                
    # Sort selected topics chronologically by day number
    selected.sort(key=lambda x: x["day"])
    return selected
