"""Audit readers preserve original indices and distinguish one pass from two observations."""
import pytest

from final.src.audits.detection_kinds import evaluation_observations, observation_kind
from final.src.runtime.artifacts import save


def test_partial_confirmation_maps_subset_index_to_original_input(tmp_path):
    save(tmp_path / "evaluation/4_0.json", {"tests": [{"status": "pass"}, {"status": "fail"}, {"status": "timeout"}]})
    save(tmp_path / "evaluation/4_retry_1.json", {"tests": [{"status": "fail"}, {"status": "pass"}]})
    result = evaluation_observations(tmp_path, "4", {"retested": [1, 2]})
    assert result == [[{"status": "pass"}], [{"status": "fail"}, {"status": "fail"}],
                      [{"status": "timeout"}, {"status": "pass"}]]


def test_all_pass_confirmation_needs_no_second_file(tmp_path):
    save(tmp_path / "evaluation/4_0.json", {"tests": [{"status": "pass"}]})
    assert evaluation_observations(tmp_path, "4", {"retested": []}) == [[{"status": "pass"}]]


def test_historical_full_repeats_remain_readable(tmp_path):
    save(tmp_path / "evaluation/4_0.json", {"tests": [{"status": "pass"}, {"status": "fail"}]})
    save(tmp_path / "evaluation/4_1.json", {"tests": [{"status": "fail"}, {"status": "fail"}]})
    result = evaluation_observations(tmp_path, "4", {"failing": [1], "unstable": [0]})
    assert result[0] == [{"status": "pass"}, {"status": "fail"}]
    assert result[1] == [{"status": "fail"}, {"status": "fail"}]


def test_missing_failure_confirmation_is_an_error_not_a_stable_failure(tmp_path):
    save(tmp_path / "evaluation/4_0.json", {"tests": [{"status": "fail"}]})
    with pytest.raises(ValueError, match="Missing first-failure confirmation"):
        evaluation_observations(tmp_path, "4", {"retested": []})


def test_single_unconfirmed_failure_is_not_a_stable_value_mismatch():
    with pytest.raises(ValueError, match="Not a confirmed failure"):
        observation_kind([{"status": "fail"}])
