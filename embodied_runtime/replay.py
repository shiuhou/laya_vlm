"""JSONL replay utilities; replay never invokes a model."""
from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path


def write_events(path: str | Path, events: Iterable[dict]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def read_events(path: str | Path) -> Iterator[dict]:
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)
