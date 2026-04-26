from src.rag import load_context_docs, retrieve_contexts


def docs():
    return load_context_docs("data/context_docs")


def test_study_focus_retrieval():
    results = retrieve_contexts("quiet study music for homework", docs(), k=2)

    assert results[0]["id"] == "study"
    assert len(results) == 2


def test_workout_retrieval_has_high_energy_targets():
    results = retrieve_contexts("upbeat workout music", docs(), k=1)

    assert results[0]["id"] == "workout"
    assert results[0]["target_energy_min"] >= 0.7


def test_sleep_relax_retrieval_has_low_energy_targets():
    results = retrieve_contexts("calm sleep music to relax", docs(), k=2)

    assert results[0]["target_energy_max"] <= 0.45
    assert {result["id"] for result in results} & {"sleep", "relax"}


def test_retrieval_respects_k_bound():
    assert len(retrieve_contexts("party music", docs(), k=1)) == 1
