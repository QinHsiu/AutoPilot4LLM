def score_one(pred, gold) -> bool:
    return isinstance(pred, str) and isinstance(gold, str) and pred == gold
