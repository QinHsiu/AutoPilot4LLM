def score_one(pred, gold) -> bool:
    if not isinstance(pred, dict) or not isinstance(gold, dict):
        return False
    if set(pred) != set(gold):
        return False
    for key, expected in gold.items():
        actual = pred[key]
        if not isinstance(actual, str) or not isinstance(expected, str):
            return False
        if actual.strip() != expected.strip():
            return False
    return True
