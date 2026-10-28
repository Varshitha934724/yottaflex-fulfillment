from pathlib import Path
import csv


def test_allocation_results_file_exists():
    path = Path("src/data/allocation_results.csv")
    assert path.exists(), "Allocation results file is missing"


def test_allocation_statuses_are_valid():
    path = Path("src/data/allocation_results.csv")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    assert len(rows) > 0
    valid_statuses = {"ALLOCATED", "UNFULFILLABLE"}

    for row in rows:
        assert row["status"] in valid_statuses


def test_every_allocation_has_a_line_id():
    path = Path("src/data/allocation_results.csv")

    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        assert row["order_line_id"].strip() != ""