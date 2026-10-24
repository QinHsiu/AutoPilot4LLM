from prompt.tasks.badcase.metric import score_one as badcase_score
from prompt.tasks.clean.metric import score_one as clean_score
from prompt.tasks.distill.metric import score_one as distill_score
from prompt.tasks.govern.metric import score_one as govern_score
from prompt.tasks.train_analysis.metric import score_one as train_score


def test_distill_requires_exact_stripped_strings():
    gold = {"name": "张三", "sex": "男", "symptom": "发热两天"}
    assert distill_score({"name": " 张三 ", "sex": "男", "symptom": "发热两天"}, gold)
    assert not distill_score({"name": "张三", "sex": "男"}, gold)
    assert not distill_score({"name": "张三", "sex": "男", "symptom": "发热两天", "extra": ""}, gold)


def test_clean_and_govern_are_exact_strings():
    assert clean_score("keep", "keep")
    assert not clean_score("keep ", "keep")
    assert govern_score("redact", "redact")
    assert not govern_score("pass", "fail")


def test_train_analysis_compares_sets():
    assert train_score(["LEAK", "EMPTY", "EMPTY"], ["EMPTY", "LEAK"])
    assert not train_score(["DUP"], ["EMPTY"])


def test_badcase_is_exact_label():
    assert badcase_score("FORMAT", "FORMAT")
    assert not badcase_score("OFF_TOPIC", "FORMAT")
