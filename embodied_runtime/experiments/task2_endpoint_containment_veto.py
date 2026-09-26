"""Fresh point approach with one observed-point nominal-endpoint exclusion."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path

import numpy as np

from ..decision_interface import CanonicalDecisionInput, geometric_effects
from . import task2_box_point_boundary as baseline
from . import task2_observed_surface_sweep as geometry
from .records import file_hash
from .sensor_gripper_proximity import NUMERIC_TOLERANCE, proxy_distance

PROTOCOL = baseline.ROOT/'docs/research/task2_endpoint_containment_veto_protocol.md'
BASELINE_SHA = 'f834673a379523f8c90619d2fd00dd69174f4dd7499cb91a8340742de225e771'
GEOMETRY_SOURCES = {name: digest for name, digest in geometry.SOURCES.items()
                    if name != 'task2-box-point-boundary-run-01/episodes.jsonl'}


def prepare_geometry(frame, point):
    for name, expected in GEOMETRY_SOURCES.items():
        if file_hash(baseline.RAW/name) != expected:
            raise ValueError('Sealed geometry source mismatch: '+name)
    for name, expected in geometry.HELPERS.items():
        if file_hash(Path(__file__).with_name(name)) != expected:
            raise ValueError('Unchanged geometry helper mismatch: '+name)
    calibration = baseline.read(baseline.RAW/'robot-geometry-observability-03/robot-calibration.json')
    if point['box_xyxy'] != [208, 156, 228, 223]:
        raise ValueError('Frozen full BOX changed')
    full = geometry.support(*(frame[k] for k in ('depth_m', 'intrinsics', 'camera_to_world')), point['box_xyxy'])
    if len(full) != 1340:
        raise ValueError('Original full BOX point count differs')
    return {'calibration': geometry.subtree(calibration), 'full_support': full,
            'source_sha256': GEOMETRY_SOURCES, 'helper_sha256': geometry.HELPERS,
            'compatibility': geometry.compatibility(calibration),
            'containment_halfspace_numeric_tolerance': NUMERIC_TOLERANCE,
            'physical_margin_m': 0., 'sweep_computed': False,
            'support_refreshed': False, 'mask_cleanup': False,
            'exploratory_partial_observation_guard': True, 'safety_certification': False}


def preflight(args):
    frozen, point, frame = baseline.preflight(args)
    if file_hash(baseline.RAW/'task2-box-point-boundary-run-01/episodes.jsonl') != BASELINE_SHA:
        raise ValueError('Sealed comparison baseline changed')
    frozen.update(protocol_sha256=file_hash(PROTOCOL),
                  endpoint_guard=prepare_geometry(frame, point),
                  baseline_journal_sha256=BASELINE_SHA,
                  predicted_first_policy_divergence_step=22,
                  baseline_protocol_sha256=file_hash(baseline.PROTOCOL))
    return frozen, point, frame


def endpoint_exclusions(full_support, geometries):
    """OR containment over five separate solids; never fill inter-proxy gaps."""
    if list(geometries) != geometry.GEOMS:
        raise ValueError('All five separate own gripper proxies required')
    points = np.asarray([row['position_world_m'] for row in full_support], float)
    if points.ndim != 2 or points.shape[1:] != (3,) or not len(points) or not np.isfinite(points).all():
        raise ValueError('Nonempty finite observed support required')
    result = {}
    for token, delta in geometry.MOVES.items():
        proxies, union = {}, np.zeros(len(points), bool)
        for name, vertices in geometries.items():
            _, _, inside = proxy_distance(points, np.asarray(vertices)+np.asarray(delta))
            union |= inside
            indices = np.flatnonzero(inside).tolist()
            proxies[name] = {'contained_point_count': len(indices), 'full_support_indices': indices}
        excluded = token != 'STOP' and bool(union.any())
        result[token] = {'nominal_delta_m': delta, 'excluded': excluded,
                         'reason': ('terminal_option_no_primitive' if token == 'STOP' else
                                    'observed_point_inside_nominal_endpoint' if excluded else 'no_observed_endpoint_containment'),
                         'contained_point_count': int(union.sum()), 'proxies': proxies}
    return result


def select_remaining(view, exclusions):
    if list(exclusions) != [candidate.token for candidate in view.candidates]:
        raise ValueError('All seven canonical candidates must remain in exclusion evidence')
    remaining = tuple(candidate for candidate in view.candidates if not exclusions[candidate.token]['excluded'])
    eligible = CanonicalDecisionInput(view.state, remaining, geometric_effects(view.state, remaining), view.history)
    token = eligible.rule_token() if remaining else 'STOP'
    reason = 'endpoint_veto_zero_remaining_pool' if not remaining else 'rule_no_strict_nominal_improvement'
    return token, eligible, reason


class EndpointSelector:
    """Only fixed observed support/static own geometry/live returned own data."""
    def __init__(self, packet):
        self.calibration, self.full = packet['calibration'], packet['full_support']
        self.first_divergence = None

    def __call__(self, view, returned_own):
        own = geometry.own_packet(returned_own)
        proxies, mount = geometry.place(self.calibration, own)
        exclusions = endpoint_exclusions(self.full, proxies)
        delta = np.asarray(view.state.fields['relations.tcp_target_delta_m'].value)
        for candidate, details in exclusions.items():
            details['nominal_tcp_to_P_m'] = float(np.linalg.norm(delta-np.asarray(geometry.MOVES[candidate])))
        token, eligible, reason = select_remaining(view, exclusions)
        unguarded = view.rule_token()
        if token != unguarded and self.first_divergence is None:
            self.first_divergence = {'step': view.revision, 'unguarded_token': unguarded, 'guarded_token': token}
        return token, {'guard': 'full_BOX_observed_point_nominal_endpoint_containment',
                       'own_packet': own, 'own_sample_time_s': None, 'mount': mount,
                       'current_proxy_vertices_world_m': {k: v.tolist() for k, v in proxies.items()},
                       'all_seven_candidates': exclusions, 'eligible_canonical': asdict(eligible),
                       'unguarded_rule_token_at_same_state': unguarded,
                       'first_policy_divergence': self.first_divergence,
                       'STOP_semantics': 'termination_before_execute'}, reason


def collect(args):
    def selector_factory(frozen):
        if not args.review or not Path(args.review).is_file():
            raise ValueError('Independent prospective review receipt required')
        review = Path(args.review).read_text()
        if frozen['code']['commit'] not in review or 'PASS' not in review:
            raise ValueError('Prospective PASS must name exact clean freeze')
        return EndpointSelector(frozen['endpoint_guard'])
    baseline.collect(args, preflight_fn=preflight, protocol=PROTOCOL,
                     selector_factory=selector_factory,
                     condition='cached_BOX_P_full_BOX_nominal_endpoint_containment_veto')


def replay(args):
    baseline.replay(args, preflight_fn=preflight,
                    provenance_keys=('endpoint_guard', 'baseline_journal_sha256',
                                     'baseline_protocol_sha256', 'predicted_first_policy_divergence_step'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--review')
    parser.add_argument('--mode', choices=('collect', 'replay'), default='collect')
    parser.add_argument('--source')
    parser.add_argument('--preflight', action='store_true')
    parser.add_argument('--libero-root', default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir', default='/home/junhongli/runs/libero-config')
    parser.set_defaults(seed=1, init_state_id=0)
    args = parser.parse_args()
    if args.preflight:
        frozen, _, _ = preflight(args)
        with Path(args.output).open('x') as stream:
            json.dump(frozen, stream, indent=2, allow_nan=False)
            stream.write('\n')
        print(json.dumps({'preflight': 'passed', 'world_constructed': False}))
    else:
        (collect if args.mode == 'collect' else replay)(args)
