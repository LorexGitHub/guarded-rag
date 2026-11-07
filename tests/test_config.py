from guarded_rag import config


def test_retrieval_constants_match_adr_0004():
    assert config.K == 5
    assert config.MIN_SCORE == 0.70
