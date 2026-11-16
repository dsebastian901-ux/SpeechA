"""Regression: do not count old r51 approvals as newly evaluated r53 calls."""
from app.services.checkpoint_revision_summary import summarize_result_revisions


def _item(status, rev=None):
    return {"status": status, "analytics_metadata": {"engine_revision": rev}}


def test_saved_r51_decisions_remain_r51_after_resuming_r53_batch():
    items = [
        _item("completado", "3.6.19-r51"),
        _item("completado", "3.6.19-r51"),
        _item("completado", "3.6.19-r53-gpt6-test2"),
        _item("error", "3.6.19-r51"),
        {"status": "pendiente"},
    ]
    result = summarize_result_revisions(items, "3.6.19-r53-gpt6-test2")
    assert result["processed"] == 3
    assert result["previous_engine_results"] == 2
    assert result["revisions"]["3.6.19-r51"] == 2
    assert result["requires_explicit_reanalysis"]


def test_only_current_engine_results_do_not_request_reanalysis():
    result = summarize_result_revisions(
        [_item("completado", "3.6.19-r53-gpt6-test2"), {"status": "pendiente"}],
        "3.6.19-r53-gpt6-test2")
    assert not result["requires_explicit_reanalysis"]
    assert not result["previous_engine_results"]


def test_unknown_original_engine_also_warns_without_inventing_version():
    result = summarize_result_revisions([_item("completado")], "3.6.19-r53")
    assert result["unknown_engine_results"] == 1
    assert result["requires_explicit_reanalysis"]
