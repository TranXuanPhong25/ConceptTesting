import json

from scripts.benchmark_adapters import main


def test_cli_reports_fixture_counts(tmp_path, capsys):
    mbpp = tmp_path / "mbpp.jsonl"
    mbpp.write_text(json.dumps({
        "task_id": 1,
        "text": "x",
        "code": "def f():\n    return 1\n",
        "test_list": [],
    }) + "\n")

    assert main(["--mbpp", str(mbpp)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["mbpp"]["count"] == 1
