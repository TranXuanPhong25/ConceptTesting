from __future__ import annotations

import csv
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


def parse_pit_report(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if path.is_dir():
        candidates = sorted(path.glob("**/mutations.xml"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            candidates = sorted(path.glob("**/mutations.csv"), key=lambda p: p.stat().st_mtime)
        if not candidates:
            raise FileNotFoundError(f"no PIT mutations report below {path}")
        path = candidates[-1]
    if path.suffix == ".csv":
        return _parse_csv(path)
    root = ET.parse(path).getroot()
    rows = []
    for index, mutation in enumerate(root.findall(".//mutation"), 1):
        def value(name: str) -> str:
            node = mutation.find(name)
            return (node.text or "").strip() if node is not None else ""
        rows.append({
            "id": value("index") or str(index), "status": mutation.attrib.get("status", value("status")).upper(),
            "operator": value("mutator").rsplit(".", 1)[-1], "line": int(value("lineNumber") or 0),
            "mutated_statement": value("description"), "source_file": value("sourceFile"),
            "method": value("mutatedMethod"), "killing_test": value("killingTest"),
        })
    return rows


def _parse_csv(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(newline="", encoding="utf-8") as handle:
        for index, fields in enumerate(csv.reader(handle), 1):
            if len(fields) < 7:
                continue
            rows.append({"id": str(index), "source_file": fields[1], "operator": fields[2].rsplit(".", 1)[-1],
                         "method": fields[3], "line": int(fields[4] or 0), "status": fields[5].upper(),
                         "mutated_statement": fields[6], "killing_test": fields[7] if len(fields) > 7 else ""})
    return rows


def run_pit(checkout: Path, java_home: Path, target_class: str, timeout: float = 1800) -> Path:
    env = dict(os.environ, JAVA_HOME=str(java_home), PATH=f"{java_home / 'bin'}:{os.environ.get('PATH', '')}")
    command = ["mvn", "-q", "org.pitest:pitest-maven:mutationCoverage", f"-DtargetClasses={target_class}",
               "-DoutputFormats=XML", "-DtimestampedReports=false"]
    result = subprocess.run(command, cwd=checkout, env=env, text=True, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"PIT failed ({result.returncode}): {result.stderr[-3000:]}")
    return checkout / "target" / "pit-reports" / "mutations.xml"

