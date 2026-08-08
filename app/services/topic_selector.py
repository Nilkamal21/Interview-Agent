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
    
    # Classify joined days with reasoning context
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
            
            attempts = mission.get("attempts", 1)
            if mission.get("skipped") is True:
                reason = "Selected because this topic was skipped — checking baseline awareness"
                skipped.append((joined, reason))
            elif mission.get("passed") is False:
                reason = f"Selected due to failed status (passed: false) after {attempts} attempts"
                failed.append((joined, reason))
            else:
                if attempts >= 3:
                    reason = f"Selected due to high attempt count ({attempts} attempts) indicating struggle"
                    high_attempts.append((joined, reason))
                elif attempts == 2:
                    reason = f"Selected due to moderate attempt count ({attempts} attempts)"
                    medium.append((joined, reason))
                else:
                    reason = "Selected as a spot-check: passed on first attempt, verifying real understanding vs luck"
                    easy.append((joined, reason))
                    
    # Sort struggled/failed by attempts descending to prioritize harder ones first
    failed.sort(key=lambda x: x[0]["result"].get("attempts", 0), reverse=True)
    high_attempts.sort(key=lambda x: x[0]["result"].get("attempts", 0), reverse=True)
    
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
        for item, reason in selected_struggles[:3]:
            item["reason"] = reason
            selected.append(item)
        item, reason = easy[0]
        item["reason"] = "Selected as a spot-check: passed on first attempt, verifying real understanding vs luck"
        selected.append(item)
    # 2. If we have no easy days but have at least 4 struggle/skipped days:
    #    Take exactly 4 struggles/skips.
    elif len(selected_struggles) >= 4:
        for item, reason in selected_struggles[:4]:
            item["reason"] = reason
            selected.append(item)
    # 3. Otherwise: merge all struggles and fill the remaining slots with easy days.
    else:
        for item, reason in selected_struggles:
            item["reason"] = reason
            selected.append(item)
        for item, reason in easy:
            if len(selected) < 4:
                # If we had struggles, this easy day is a spot-check. Otherwise, it is a baseline check.
                if len(selected_struggles) > 0:
                    item["reason"] = "Selected as a spot-check: passed on first attempt, verifying real understanding vs luck"
                else:
                    item["reason"] = "Selected for technical baseline: passed on first attempt"
                selected.append(item)
            else:
                break
                
    # Sort selected topics chronologically by day number
    selected.sort(key=lambda x: x["day"])
    return selected
