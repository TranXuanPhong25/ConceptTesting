"""Endpoint/config CLI checks without model/tokenizer/reference execution."""
import sys

import pytest

from final.src.audits import run_prompt_style as runner
from final.src.models.model import QwenModel, TransportError


@pytest.fixture
def private_config(monkeypatch, tmp_path):
    for name in ("FINAL_BASE_URL", "FINAL_MODEL", "FINAL_API_KEY", "FINAL_ENDPOINT_ENV_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("FINAL_ENDPOINT_ENV_FILE", "")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr(runner, "LEGACY_ENDPOINT_FILE", tmp_path / "missing-legacy.env")

    def forbidden(*args, **kwargs):
        raise AssertionError("Configuration check must not call network/model")

    monkeypatch.setattr(QwenModel, "request", forbidden)
    return tmp_path


def write_config(path, suffix="persistent"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('export FINAL_BASE_URL=http://fixture.invalid/' + suffix + '\nexport FINAL_MODEL=qwen3.5-27b-awq\n')
    return path


def test_persistent_config_works_without_tmp_file(private_config):
    path = write_config(private_config / "config/concepttester/final-qwen.env")
    assert runner.configure_endpoint() == path
    assert QwenModel().base_url == "http://fixture.invalid/persistent"


def test_explicit_file_overrides_default_and_process_url(private_config, monkeypatch):
    write_config(private_config / "config/concepttester/final-qwen.env")
    monkeypatch.setenv("FINAL_BASE_URL", "http://fixture.invalid/process")
    explicit = write_config(private_config / "explicit.env", "explicit")
    assert runner.configure_endpoint(explicit) == explicit
    assert QwenModel().base_url == "http://fixture.invalid/explicit"


def test_explicit_env_file_is_supported(private_config, monkeypatch):
    explicit = write_config(private_config / "by-env.env", "explicit-env")
    monkeypatch.setenv("FINAL_ENDPOINT_ENV_FILE", str(explicit))
    assert runner.configure_endpoint() == explicit


def test_process_url_is_not_overwritten_by_stale_defaults(private_config, monkeypatch):
    write_config(private_config / "config/concepttester/final-qwen.env")
    write_config(runner.LEGACY_ENDPOINT_FILE, "stale")
    monkeypatch.setenv("FINAL_BASE_URL", "http://fixture.invalid/process")
    runner.configure_endpoint()
    assert QwenModel().base_url == "http://fixture.invalid/process"


def test_legacy_file_still_works(private_config):
    write_config(runner.LEGACY_ENDPOINT_FILE, "legacy")
    assert runner.configure_endpoint() == runner.LEGACY_ENDPOINT_FILE
    assert QwenModel().base_url == "http://fixture.invalid/legacy"


def test_missing_explicit_file_does_not_silently_fall_back(private_config):
    write_config(private_config / "config/concepttester/final-qwen.env")
    with pytest.raises(ValueError, match="Endpoint env file does not exist"):
        runner.configure_endpoint(private_config / "absent.env")


def test_wrong_model_is_a_configuration_error(private_config):
    path = write_config(private_config / "bad-model.env")
    path.write_text(path.read_text().replace("qwen3.5-27b-awq", "other-model"))
    with pytest.raises(TransportError) as failure:
        runner.configure_endpoint(path)
    assert failure.value.error_type == "ModelChanged"


def test_missing_config_fails_before_creating_any_run(private_config, monkeypatch, capsys):
    output = private_config / "must-not-exist"
    monkeypatch.setattr(sys, "argv", ["run_prompt_style", "--cohort", str(private_config / "cohort.json"), "--artifacts", str(output)])
    with pytest.raises(SystemExit) as failure:
        runner.main()
    assert failure.value.code == 2
    assert "Missing Qwen endpoint" in capsys.readouterr().err
    assert not output.exists()
