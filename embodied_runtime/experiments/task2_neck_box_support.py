"""One fixed researcher-specified neck BOX, using unchanged baseline machinery."""
from __future__ import annotations

from contextlib import contextmanager

from . import task2_box_support as baseline

QUERY = 'the neck of the wine bottle'
QUESTION = f'Locate a single instance that matches the following description: {QUERY}.'
PROTOCOL = baseline.ROOT / 'docs/research/task2_neck_box_support_protocol.md'
CORE_SHA = '9986c4f79578dd4e2691726f21df7ba0706ac8b9876a255ca078eed2f9bb43a6'


@contextmanager
def fixed_condition():
    """Bind only semantic text and protocol; restore even after a failed run."""
    if baseline.file_hash(baseline.__file__) != CORE_SHA:
        raise ValueError('sealed baseline machinery changed')
    original = baseline.QUERY, baseline.QUESTION, baseline.PROTOCOL
    baseline.QUERY, baseline.QUESTION, baseline.PROTOCOL = QUERY, QUESTION, PROTOCOL
    try:
        yield
    finally:
        baseline.QUERY, baseline.QUESTION, baseline.PROTOCOL = original


if __name__ == '__main__':
    with fixed_condition():
        baseline.main()
