
def detect_anomaly(previous_scores, current_score):
    if not previous_scores:
        return False
    avg = sum(previous_scores)/len(previous_scores)
    return abs(avg - current_score) > 10
