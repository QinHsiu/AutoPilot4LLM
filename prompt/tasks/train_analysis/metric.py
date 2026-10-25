def score_one(pred, gold) -> bool:
    if not isinstance(pred, list) or not isinstance(gold, list):
        return False
    return set(pred) == set(gold)
