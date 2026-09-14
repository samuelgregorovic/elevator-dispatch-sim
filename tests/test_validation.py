"""Input validation (A14, A15) and config validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import req
from elevator_sim.config import SimulationConfig
from elevator_sim.io import read_requests
from elevator_sim.validate import InvalidInputError, parse_row, validate_requests


def write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "in.csv"
    p.write_text(body)
    return p


def test_reads_sample_from_brief(tmp_path):
    p = write(
        tmp_path, "time,id,source,dest\n0,passenger1,1,51\n0,passenger2,1,37\n10,passenger3,20,1\n"
    )
    rows = read_requests(p, floors=51)
    assert [r.id for r in rows] == ["passenger1", "passenger2", "passenger3"]


def test_unsorted_input_is_sorted_stably_on_load(tmp_path):
    p = write(tmp_path, "time,id,source,dest\n5,late,1,2\n0,a,1,3\n0,b,2,4\n")
    from elevator_sim.feed import RequestFeed

    feed = RequestFeed(read_requests(p, floors=10))
    assert [r.id for r in feed.release(0)] == ["a", "b"]
    assert feed.release(4) == []
    assert [r.id for r in feed.release(5)] == ["late"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("time,id,source,dest\n0,a,3,3\n", "source and dest are both 3"),
        ("time,id,source,dest\n0,a,0,3\n", "source floor 0 outside 1..10"),
        ("time,id,source,dest\n0,a,1,11\n", "dest floor 11 outside 1..10"),
        ("time,id,source,dest\n-1,a,1,2\n", "negative time"),
        ("time,id,source,dest\n0,a,1,2\n1,a,2,3\n", "duplicate passenger id a"),
        ("time,id,source,dest\n0,a,x,2\n", "must be integers"),
        ("time,id,source\n0,a,1\n", "missing column"),
        ("time,id,source,dest\n0,,1,2\n", "empty id"),
    ],
)
def test_invalid_rows_are_rejected_with_a_named_reason(tmp_path, body, message):
    with pytest.raises(InvalidInputError, match=message):
        read_requests(write(tmp_path, body), floors=10)


def test_parse_row_reports_line_number():
    with pytest.raises(InvalidInputError, match="line 7"):
        parse_row({"time": "1", "id": "a", "source": "b", "dest": "2"}, line=7)


def test_validate_requests_passes_valid_rows_through():
    rows = [req(0, "a", 1, 2), req(0, "b", 2, 1)]
    assert validate_requests(rows, floors=2) == rows


@pytest.mark.parametrize(
    "kwargs",
    [
        {"elevators": 0},
        {"floors": 1},
        {"capacity": 0},
        {"dwell_ticks": -1},
        {"start_floor": 0},
        {"park_floor": 99},
        {"served_floors": {5: frozenset({1, 2})}},
        {"served_floors": {0: frozenset({1})}},
        {"served_floors": {0: frozenset({0, 1})}},
    ],
)
def test_invalid_config_is_rejected(kwargs):
    with pytest.raises(ValueError):
        SimulationConfig(**{"elevators": 2, "floors": 10, **kwargs})
