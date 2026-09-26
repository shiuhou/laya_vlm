"""One fixed researcher-specified neck BOX, using unchanged baseline machinery."""
from __future__ import annotations

import argparse
from contextlib import contextmanager

from . import task2_box_support as baseline

QUERY = 'the neck of the wine bottle'
QUESTION = f'Locate a single instance that matches the following description: {QUERY}.'
PROTOCOL = baseline.ROOT / 'docs/research/task2_neck_box_support_protocol.md'
CORE_SHA = '8a8d7d828b4b2f65593975cb0378e5b4e7828c1e27ae432d6ca3bfdae3f179f1'


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['generate', 'evaluate', 'audit', 'processor-preflight'])
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    with fixed_condition():
        if args.mode == 'generate':
            baseline.generate(args.output, expected_gpu='1')
        elif args.mode == 'processor-preflight':
            baseline.processor_preflight(args.output)
        elif args.mode == 'evaluate':
            baseline.evaluate(args.output)
        else:
            sensor = baseline.sealed_sensor(args.output)
            print({'status': 'pass', 'selected_count': len(sensor['support_G']),
                   'model_calls': 1, 'physics_calls': 0, 'render_calls': 0})


if __name__ == '__main__':
    main()
