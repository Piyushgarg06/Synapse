"""JSON schema validator verifying that captured CLI JSON outputs conform to schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
GENERATED_DIR = SCRIPT_DIR.parent / "docs" / "_generated"


def validate_status_json(data: dict):
    assert isinstance(data, dict), "Status must be dict"
    assert "initialized" in data, "Missing initialized"
    assert "files_indexed" in data, "Missing files_indexed"
    assert "symbols_indexed" in data, "Missing symbols_indexed"
    assert "edges" in data, "Missing edges"
    assert "files_with_errors" in data, "Missing files_with_errors"
    assert "dirty_working_tree" in data, "Missing dirty_working_tree"


def validate_search_json(data: list):
    assert isinstance(data, list), "Search JSON must be list"
    if data:
        item = data[0]
        assert "name" in item
        assert "qualified_name" in item
        assert "kind" in item
        assert "file_path" in item
        assert "start_line" in item


def validate_inspect_json(data: dict):
    assert isinstance(data, dict), "Inspect JSON must be dict"
    assert "found" in data
    if data.get("ambiguous"):
        assert "candidates" in data
    else:
        assert "symbol" in data
        assert "callers" in data
        assert "callees" in data
        assert "base_classes" in data
        assert "subclasses" in data


def validate_context_json(data: dict):
    assert isinstance(data, dict), "Context JSON must be dict"
    assert "query" in data
    assert "results_count" in data
    assert "items" in data
    assert "disclaimer" in data


def validate_index_json(data: dict):
    assert isinstance(data, dict), "Index JSON must be dict"
    assert "mode" in data or "files_processed" in data or "checkpoint" in data


def validate_export_json(data: dict):
    assert isinstance(data, dict), "Export JSON must be dict"
    assert "schema_version" in data
    assert "files" in data
    assert "symbols" in data
    assert "edges" in data
    assert "references" in data


def main() -> int:
    manifest_path = GENERATED_DIR / "manifest.json"
    if not manifest_path.exists():
        print("Error: manifest.json not found in _generated.")
        return 1

    with open(manifest_path, "r", encoding="utf-8") as f:
        captures = json.load(f)

    # Validate status
    status_raw = captures["07_status_json"]["stdout"]
    validate_status_json(json.loads(status_raw))

    # Validate search
    search_raw = captures["10_search_json"]["stdout"]
    validate_search_json(json.loads(search_raw))

    # Validate inspect
    inspect_raw = captures["13_inspect_json"]["stdout"]
    validate_inspect_json(json.loads(inspect_raw))

    # Validate context
    context_raw = captures["16_context_json"]["stdout"]
    validate_context_json(json.loads(context_raw))

    # Validate index
    index_raw = captures["21_index_incremental_json"]["stdout"]
    validate_index_json(json.loads(index_raw))

    # Validate export
    sample_export_path = GENERATED_DIR / "sample_export.json"
    if sample_export_path.exists():
        with open(sample_export_path, "r", encoding="utf-8") as f:
            validate_export_json(json.load(f))

    print("PASS: All captured JSON outputs conform to expected schemas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
